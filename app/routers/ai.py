# -*- coding: utf-8 -*-

import hashlib
import json
import os
import random
import re
import secrets
import stat
import time
from typing import cast
from datetime import datetime
from filelock import FileLock, Timeout
from lxml import etree as ET
import anyio
import ollama
from dotenv import load_dotenv
from app.utils import find_test, find_question, get_test_metadata, get_testy_autor, normalizuj_vzor, xquery_to_string, xslt_to_string
from app.mytypes import StringQuery, IntForm, StringForm
from anyio.streams.memory import MemoryObjectSendStream
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.exceptions import HTTPException

load_dotenv()

router = APIRouter()

CACHE_ADRESAR = '/tmp/pisomky-napovedy'
CACHE_MAX_NAPOVEDI = 5
CAKANIE_INTERVAL = 10
# Options that make Ollama restart its runner when they differ between calls, so the warm-up in
# main.py and the hint calls must share them. qwen3.5 is a hybrid (recurrent) model: its prompt
# cache works only through context checkpoints, and llama.cpp creates one at (prompt length -
# num_batch). With the default num_batch 512 that is at ~215 of the ~665 tokens of the shared
# system prompt, so ~500 tokens were evaluated again for every hint (~11 s); with 64 the
# checkpoint lands just below the end of the shared prefix (~2 s). Measured 2026-10-26.
OLLAMA_RUNNER_OPTIONS = {'num_ctx': 4096, 'num_batch': 64}
ZAMOK_CAKANIE = 30
ZAMOK_KROK = 0.2


def _najdi_napovedu(otazka_id: str, spravna_odpoved: str | None = None, logger=None) -> dict | None:
   otazka_el, _ = find_question(otazka_id)
   if otazka_el is None:
      return None
   try:
      spravna_key = None
      if spravna_odpoved:
         for odp in otazka_el.findall('odpoved[@spravna="1"]'):
            if odp.text and odp.text.strip() == spravna_odpoved:
               spravna_key = odp.get('napoveda_key')
               break
      napovedy_els = otazka_el.findall('napoveda')
      if spravna_key:
         keys_ = [k.strip() for k in spravna_key.split(',')]
         napovedy_els = [n for n in napovedy_els if not n.get('pre') or n.get('pre') in keys_]
      else:
         napovedy_els = [n for n in napovedy_els if not n.get('pre')]
      napovedy = [n.text.strip() for n in napovedy_els if n.text and n.text.strip()] or None
      vzory = [normalizuj_vzor(v.text) for v in otazka_el.findall('vzor') if v.text and v.text.strip()]
      klucove = [s.text.strip() for s in otazka_el.findall('klucove_slova/slovo') if s.text]
      return {'napovedy': napovedy, 'vzory': vzory, 'klucove': klucove}
   except Exception as e:
      if logger:
         logger.error(f'chyba napoveda novy format: {e}')
      return None


def _spocitaj_napovedy_testu(subor: str, test_id: str) -> int:
   if not os.path.exists(subor):
      return 0
   try:
      tree = ET.parse(subor)
      return len(tree.xpath('.//zapis[@test_id=$id]', id=test_id))  # type: ignore[arg-type]
   except Exception:
      return 0


def _nacitaj_predchadzajuce(subor: str, otazka_id: str, limit: int = 3) -> list[dict]:
   """Returns the last `limit` hints of the question that students rated (val 1 or 0)."""
   if not os.path.exists(subor):
      return []
   try:
      tree = ET.parse(subor)
      zaznamy = cast(list, tree.xpath('.//zapis[@otazka_id=$id and (@val="1" or @val="0")]', id=otazka_id))
      return [
         {'hint': hint_el.text.strip(), 'val': z.get('val', '')}
         for z in zaznamy
         if (hint_el := z.find('hint')) is not None and hint_el.text and hint_el.text.strip()
      ][-limit:]
   except Exception:
      return []


def _aktualizuj_zapis(subor: str, zapis_id: str, hint: str) -> None:
   if not os.path.exists(subor):
      return
   lock = FileLock(subor + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(subor, xmlParser)
      root = tree.getroot()
      zapis = next((z for z in root.findall('.//zapis') if z.get('id') == zapis_id), None)
      if zapis is None:
         return
      hint_el = zapis.find('hint')
      if hint_el is None:
         hint_el = ET.SubElement(zapis, 'hint')
      hint_el.text = hint
      ET.indent(tree, space='   ')
      tree.write(subor, encoding='UTF-8', xml_declaration=True)


def _uloz_zapis(subor: str, zapis_id: str, otazka_id: str, test_id: str, predmet: str = '', trieda: str = '', skupina: str = '', kapitola: str = '', fileid: str = '') -> None:
   os.makedirs(os.path.dirname(subor), exist_ok=True)
   lock = FileLock(subor + '.lock')
   with lock:
      if os.path.exists(subor):
         xmlParser = ET.XMLParser(remove_blank_text=True)
         tree = ET.parse(subor, xmlParser)
         root = tree.getroot()
      else:
         autor = get_testy_autor(predmet, trieda, skupina, kapitola, fileid)
         root = ET.Element('feedback', attrib={'predmet': predmet, 'trieda': trieda, 'skupina': skupina, 'kapitola': kapitola, 'fileid': fileid, 'autor': autor})
         tree = ET.ElementTree(root)
      zapis = ET.SubElement(root, 'zapis')
      zapis.set('id', zapis_id)
      zapis.set('datum', datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
      zapis.set('otazka_id', otazka_id)
      zapis.set('test_id', test_id)
      zapis.set('val', '')
      ET.indent(tree, space='   ')
      tree.write(subor, encoding='UTF-8', xml_declaration=True)


def _parsuj_hint(raw: str) -> str:
   hint = raw
   for line in raw.split('\n'):
      line = line.strip()
      if line.upper().startswith('HINT:'):
         hint = line[5:].strip()
   return hint


def _cache_kluc(system_instrukcie: str, user_instrukcie: str) -> str:
   """Hash of the prompt without the rating history, so that a changed question text,
   answer or prompt template automatically misses the cache."""
   return hashlib.sha256(f'{system_instrukcie}\0{user_instrukcie}'.encode('utf-8')).hexdigest()[:16]


def _sukromny_adresar() -> bool:
   """True when CACHE_ADRESAR exists (it is created when missing) and is private to this user."""
   try:
      os.makedirs(CACHE_ADRESAR, mode=0o700, exist_ok=True)
      st = os.lstat(CACHE_ADRESAR)
   except OSError:
      return False
   return stat.S_ISDIR(st.st_mode) and st.st_uid == os.geteuid() and not st.st_mode & 0o077


def _cache_subor(predmet: str, trieda: str, skupina: str, kapitola: str, fileid: str) -> str | None:
   """Path of the hint cache of one test (one file per fileid). It lives in /tmp, which is a
   tmpfs here: RAM only, shared by all workers, wiped on reboot. Returns None, which turns
   the cache off, when the directory cannot be created or is not private to this user."""
   if not _sukromny_adresar():
      return None
   nazov = re.sub(r'[^A-Za-z0-9_.-]', '_', f'{predmet}_{trieda}{skupina}_{kapitola}_{fileid}')
   return os.path.join(CACHE_ADRESAR, nazov + '.json')


def _cache_nacitaj(subor: str) -> dict:
   """Cache layout: {otazka_id: {kluc: {'napovedy': [{'hint', 'skore'}]}}}. `skore` is
   the sum of the student ratings (+1 helped, -1 did not help), 0 until rated."""
   try:
      with open(subor, encoding='utf-8') as f:
         data = json.load(f)
   except (OSError, ValueError):
      return {}
   return data if isinstance(data, dict) else {}


def _cache_zapis(subor: str, data: dict) -> None:
   tmp = subor + '.tmp'
   with open(tmp, 'w', encoding='utf-8') as f:
      json.dump(data, f, ensure_ascii=False)
   os.replace(tmp, subor)


def _cache_ziskaj(subor: str | None, otazka_id: str, kluc: str) -> dict | None:
   """Returns a random hint of the pool (helped and not yet rated ones alike), or None when
   the pool is empty and the caller has to generate a new one."""
   if not subor:
      return None
   zaznam = _cache_nacitaj(subor).get(otazka_id, {}).get(kluc)
   if not zaznam or not zaznam['napovedy']:
      return None
   return random.choice(zaznam['napovedy'])


def _cache_uloz(subor: str | None, otazka_id: str, kluc: str, hint: str) -> None:
   """Adds a hint to the pool; when the pool is full, the hint with the lowest score is
   dropped first (the oldest one of them)."""
   if not subor:
      return
   with FileLock(subor + '.lock'):
      data = _cache_nacitaj(subor)
      zaznam = data.setdefault(otazka_id, {}).setdefault(kluc, {'napovedy': []})
      napovedy = zaznam['napovedy']
      if any(n['hint'] == hint for n in napovedy):
         return
      if len(napovedy) >= CACHE_MAX_NAPOVEDI:
         napovedy.remove(min(napovedy, key=lambda n: n['skore']))
      napovedy.append({'hint': hint, 'skore': 0})
      _cache_zapis(subor, data)


def _zamok_napovede(test_id: str) -> FileLock | None:
   """Lock that allows one running hint request per test across all workers (flock, so the
   kernel releases it when a worker dies). None, which turns the lock off, when the private
   directory is not available."""
   if not _sukromny_adresar():
      return None
   return FileLock(os.path.join(CACHE_ADRESAR, f'bezi_{hashlib.sha256(test_id.encode("utf-8")).hexdigest()[:16]}.lock'))


async def _zamok_ziskaj(zamok: FileLock, cakanie: float = ZAMOK_CAKANIE, krok: float = ZAMOK_KROK) -> bool:
   """Waits up to `cakanie` seconds for the lock. The wait gives the previous request of the
   same student time to cancel itself after the student asked for another hint."""
   with anyio.move_on_after(cakanie):
      while True:
         try:
            zamok.acquire(timeout=0)
            return True
         except Timeout:
            await anyio.sleep(krok)
   return False


def _cache_ohodnot(subor: str | None, otazka_id: str, hint: str, zmena: int) -> None:
   """Adds a rating change (+1 helped, -1 did not help, or the difference when a student
   changes the rating) to the score of the rated hint. A hint whose score drops below zero
   is removed from the pool; the next request generates a new one when the pool is empty."""
   if not subor or not hint or not zmena or not os.path.exists(subor):
      return
   with FileLock(subor + '.lock'):
      data = _cache_nacitaj(subor)
      zmeneny = False
      for varianty in data.get(otazka_id, {}).values():
         for n in varianty['napovedy']:
            if n['hint'] == hint:
               n['skore'] += zmena
               zmeneny = True
         varianty['napovedy'] = [n for n in varianty['napovedy'] if n['skore'] >= 0]
      if zmeneny:
         _cache_zapis(subor, data)


def _skore_hodnotenia(val: str | None) -> int:
   return {'1': 1, '0': -1}.get(val or '', 0)


def _posli(send: MemoryObjectSendStream, udalost: tuple[str, dict]) -> None:
   try:
      send.send_nowait(udalost)
   except (anyio.BrokenResourceError, anyio.ClosedResourceError):
      pass


async def _hlas_cakanie(send: MemoryObjectSendStream, prvy_chunk: anyio.Event, interval: float = CAKANIE_INTERVAL) -> None:
   """Sends a `caka` event every `interval` seconds until the model produces its first
   output. The data keeps the proxy from timing out the idle connection while the request
   waits for the (CPU-bound) model, and tells the client how long it has been waiting."""
   sekundy = 0.0
   while True:
      with anyio.move_on_after(interval):
         await prvy_chunk.wait()
         return
      sekundy += interval
      _posli(send, ('caka', {'sekundy': int(sekundy)}))


async def _generuj_napovedu(messages: list[dict], subor: str, zapis_id: str, send: MemoryObjectSendStream, logger,
                            prvy_chunk: anyio.Event, cache_subor: str | None, otazka_id: str, cache_kluc: str,
                            zrusenie: anyio.CancelScope | None = None, zamok: FileLock | None = None) -> None:
   """Runs the model call independently of the client connection, so that the hint is
   always saved even if the client disconnects after the first chunk. Events for the
   client are passed through the stream; closing it marks the end. Only before the first
   output the call can be cancelled through `zrusenie` (the client left, so nobody waits
   for it and it must not block the queue of the model). The hint stays counted for the
   student. The `zamok` of the test is released when the call ends."""

   def posli(udalost: tuple[str, dict]) -> None:
      _posli(send, udalost)

   zrusenie = zrusenie or anyio.CancelScope()
   full_text = ''
   vysledok = 'ok'
   start = time.monotonic()
   cakanie: float | None = None
   try:
      with zrusenie:
         client = ollama.AsyncClient()
         async for chunk in await client.chat(
            model=os.getenv('OLLAMA_MODEL', 'qwen3.5:9b'),
            messages=messages,
            stream=True,
            think=False,
            options={'temperature': 0.3, **OLLAMA_RUNNER_OPTIONS, 'keep_alive': '45m'}
         ):
            text = chunk['message']['content']
            if not text:
               continue
            if cakanie is None:
               cakanie = time.monotonic() - start
            prvy_chunk.set()
            full_text += text
            posli(('chunk', {'text': text}))

         hint = _parsuj_hint(full_text)
         _aktualizuj_zapis(subor, zapis_id, hint)
         posli(('done', {'hint': hint}))
         if hint:
            try:
               _cache_uloz(cache_subor, otazka_id, cache_kluc, hint)
            except OSError as e:
               logger.error(f'chyba zapisu cache napovedy: {e}')
      if zrusenie.cancelled_caught:
         vysledok = 'zrusena'
   except Exception as e:
      vysledok = 'chyba'
      logger.error(f'chyba napoveda stream: {e}')
      posli(('napoveda_error', {'error': 'Služba nápovedy je momentálne zaneprázdnená.'}))
   finally:
      prvy_chunk.set()
      send.close()
      if zamok:
         zamok.release()
      celkom = time.monotonic() - start
      logger.info(f'napoveda zapis={zapis_id} otazka={otazka_id} vysledok={vysledok} '
                  f'cakanie={"-" if cakanie is None else f"{cakanie:.1f}s"} celkom={celkom:.1f}s')


@router.get('/ai/napoveda')
async def napoveda(request: Request, otazka_id: StringQuery, test_id: StringQuery):
   proc = request.app.state.proc
   xsltpath = proc.new_xpath_processor()
   test_node = find_test(proc, test_id, admin=True, cache=request.app.state.kluc_cache)
   if not test_node:
      return JSONResponse({'error': 'Test nenájdený'}, status_code=404)

   xsltpath.set_context(xdm_item=test_node)
   otazka = next((o for o in (xsltpath.evaluate('otazka') or []) if o.get_attribute_value('id') == otazka_id), None)
   if not otazka:
      return JSONResponse({'error': 'Otázka nenájdená'}, status_code=404)

   xsltpath.set_context(xdm_item=otazka)
   znenie_text = xsltpath.evaluate_single('string(znenie)')
   spravna_el = xsltpath.evaluate_single('odpoved[@spravna="1"]')
   spravna_odpoved = spravna_el.string_value.strip() if spravna_el else None
   moznosti_value = xsltpath.evaluate('odpoved')
   moznosti = [m.string_value.strip() for m in moznosti_value] if moznosti_value else []

   if not znenie_text:
      return JSONResponse({'error': 'Prázdne znenie otázky'}, status_code=400)

   zamok = _zamok_napovede(test_id)
   if zamok:
      zaciatok_zamku = time.monotonic()
      ziskany = await _zamok_ziskaj(zamok)
      cakanie_zamok = time.monotonic() - zaciatok_zamku
      if cakanie_zamok >= 1:
         request.app.state.logger.info(f'napoveda test={test_id} cakanie na zamok={cakanie_zamok:.1f}s {"ok" if ziskany else "obsadena"}')
      if not ziskany:
         async def obsadene_stream():
            yield 'event: napoveda_obsadena\ndata: {}\n\n'
         return StreamingResponse(obsadene_stream(), media_type='text/event-stream',
                                  headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
      if await request.is_disconnected():
         zamok.release()
         return JSONResponse({'error': 'Klient odišiel'}, status_code=499)

   predany = zamok is None
   try:
      predmet, trieda, skupina, kapitola, fileid = get_test_metadata(proc, test_node)

      xsltpath.set_context(xdm_item=test_node)
      pocet_otazok = int(xsltpath.evaluate_single('count(otazka)') or 0)

      napovedy_data = _najdi_napovedu(otazka_id, spravna_odpoved, request.app.state.logger) if predmet else None
      napovedy = napovedy_data.get('napovedy') if isinstance(napovedy_data, dict) else napovedy_data
      vzory = napovedy_data.get('vzory') if isinstance(napovedy_data, dict) else []
      klucove = napovedy_data.get('klucove') if isinstance(napovedy_data, dict) else []

      subor = f'./res/xml/feedback/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}_{fileid}.xml'
      pouzite = _spocitaj_napovedy_testu(subor, test_id)

      if pocet_otazok > 0 and pouzite >= pocet_otazok:
         async def limit_stream():
            yield 'event: napoveda_limit\ndata: {}\n\n'
         return StreamingResponse(limit_stream(), media_type='text/event-stream',
                                  headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

      predchadzajuce = _nacitaj_predchadzajuce(subor, otazka_id)
      helped = [p['hint'] for p in predchadzajuce if p['val'] == '1']
      not_helped = [p['hint'] for p in predchadzajuce if p['val'] == '0']

      templates = request.app.state.templates
      system_instrukcie = templates.get_template('aihelp_system.md.j2').render()
      user_instrukcie = templates.get_template('aihelp_user.md.j2').render(
         znenie_text=znenie_text,
         moznosti=moznosti,
         napovedy=napovedy or [],
         vzory=vzory or [],
         klucove=klucove or [],
         helped=helped,
         not_helped=not_helped,
         spravna_odpoved=spravna_odpoved,
      )

      messages = [
         {'role': 'system', 'content': system_instrukcie},
         {'role': 'user', 'content': user_instrukcie}
      ]

      user_bez_spatnej_vazby = templates.get_template('aihelp_user.md.j2').render(
         znenie_text=znenie_text,
         moznosti=moznosti,
         napovedy=napovedy or [],
         vzory=vzory or [],
         klucove=klucove or [],
         helped=[],
         not_helped=[],
         spravna_odpoved=spravna_odpoved,
      )
      cache_kluc = _cache_kluc(system_instrukcie, user_bez_spatnej_vazby)

      zapis_id = secrets.token_hex(8)
      remaining = pocet_otazok - pouzite - 1
      _uloz_zapis(subor, zapis_id, otazka_id, test_id, predmet, trieda, skupina, kapitola, fileid)
      meta = f'event: meta\ndata: {json.dumps({"zapis_id": zapis_id, "remaining": remaining})}\n\n'
      headers = {'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}

      cache_subor = _cache_subor(predmet, trieda, skupina, kapitola, fileid)
      if not cache_subor:
         request.app.state.logger.warning('cache napoved vypnuta: adresar nie je sukromny')
      z_cache = _cache_ziskaj(cache_subor, otazka_id, cache_kluc)
      if z_cache:
         _aktualizuj_zapis(subor, zapis_id, z_cache['hint'])

         async def generate_cache():
            yield meta
            yield f'event: chunk\ndata: {json.dumps({"text": z_cache["hint"]})}\n\n'
            yield f'event: done\ndata: {json.dumps({"hint": z_cache["hint"]})}\n\n'

         return StreamingResponse(generate_cache(), media_type='text/event-stream', headers=headers)

      send, receive = anyio.create_memory_object_stream[tuple[str, dict]](max_buffer_size=float('inf'))
      prvy_chunk = anyio.Event()
      zrusenie = anyio.CancelScope()
      request.app.state.task_group.start_soon(_generuj_napovedu, messages, subor, zapis_id, send, request.app.state.logger,
                                              prvy_chunk, cache_subor, otazka_id, cache_kluc, zrusenie, zamok)
      predany = True
      request.app.state.task_group.start_soon(_hlas_cakanie, send, prvy_chunk)

      async def generate():
         try:
            yield meta
            async with receive:
               async for typ, data in receive:
                  yield f'event: {typ}\ndata: {json.dumps(data)}\n\n'
         finally:
            if not prvy_chunk.is_set():
               zrusenie.cancel()

      return StreamingResponse(generate(), media_type='text/event-stream', headers=headers)
   finally:
      if zamok and not predany:
         zamok.release()

@router.post('/ai/feedback')
async def ai_feedback(request: Request, test_id: StringForm, val: IntForm, zapis_id: StringForm):
   try:
      proc = request.app.state.proc
      test_node = find_test(proc=proc, kluc=test_id, admin=True, cache=request.app.state.kluc_cache)
      if not test_node:
         return {'ok': False, 'error': 'Test nenájdený'}

      predmet, trieda, skupina, kapitola, fileid = get_test_metadata(proc, test_node)
      subor = f'./res/xml/feedback/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}_{fileid}.xml'

      if not os.path.exists(subor):
         return {'ok': False, 'error': 'Feedback súbor neexistuje'}

      lock = FileLock(subor + '.lock')
      with lock:
         xmlParser = ET.XMLParser(remove_blank_text=True)
         tree = ET.parse(subor, xmlParser)
         root = tree.getroot()
         zapis = next((z for z in root.findall('.//zapis') if z.get('id') == zapis_id), None)
         if zapis is None:
            return {'ok': False, 'error': 'Záznam nenájdený'}
         zmena = _skore_hodnotenia(str(val)) - _skore_hodnotenia(zapis.get('val'))
         zapis.set('val', str(val))
         otazka_id = zapis.get('otazka_id', '')
         hint = zapis.findtext('hint') or ''
         tree = ET.ElementTree(root)
         ET.indent(tree, space='   ')
         tree.write(subor, encoding='UTF-8', xml_declaration=True)

      _cache_ohodnot(_cache_subor(predmet, trieda, skupina, kapitola, fileid), otazka_id, hint, zmena)
      return {'ok': True}
   except Exception as e:
      request.app.state.logger.error(f'chyba feedback: {e}')
      return {'ok': False, 'error': str(e)}

@router.post('/admin/feedbackreport', response_class=HTMLResponse)
async def feedbackreport(request: Request, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = ''):
   proc = request.app.state.proc
   try:
      params = {
         'predmet': predmet,
         'trieda': trieda,
         'skupina': skupina,
         'kapitola': kapitola,
         'fileid': fileid
      }
      subor = f'./res/xml/feedback/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}_{fileid}.xml'
      if not os.path.exists(subor):
         xml_data = ET.tostring(ET.Element('feedback', attrib={'predmet': predmet, 'trieda': trieda, 'skupina': skupina, 'kapitola': kapitola, 'fileid': fileid}), encoding='unicode')
      else:
         xml_data = xquery_to_string(proc, './res/xquery/feedback.xq', params=params)
      xml_node = proc.parse_xml(xml_text=xml_data)
      vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/feedbackreport.xsl', xdm_node=xml_node, xslt_pools=request.app.state.xslt_pools)
      return HTMLResponse(content=vysledok, status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba feedbackreport: {e}')
      raise HTTPException(status_code=400, detail=str(e))
