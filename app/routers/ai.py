# -*- coding: utf-8 -*-

import hashlib
import json
import os
import random
import re
import secrets
import stat
from typing import cast
from datetime import datetime
from filelock import FileLock
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


def _nacitaj_predchadzajuce_keys(subor: str, otazka_id: str, limit: int = 10) -> list[dict]:
   if not os.path.exists(subor):
      return []
   try:
      tree = ET.parse(subor)
      zaznamy = cast(list, tree.xpath('.//zapis[@otazka_id=$id]', id=otazka_id))[-limit:]
      return [
         {'keys': keys_el.text.strip(), 'val': z.get('val', '')}
         for z in zaznamy
         if (keys_el := z.find('keys')) is not None and keys_el.text
      ]
   except Exception:
      return []


def _aktualizuj_zapis(subor: str, zapis_id: str, hint: str | None = None, keys: str | None = None) -> None:
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
      if hint is not None:
         hint_el = zapis.find('hint')
         if hint_el is None:
            hint_el = ET.SubElement(zapis, 'hint')
         hint_el.text = hint
      if keys is not None:
         keys_el = zapis.find('keys')
         if keys_el is None:
            keys_el = ET.SubElement(zapis, 'keys')
         keys_el.text = keys
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


def _parsuj_hint_keys(raw: str) -> tuple[str, str]:
   hint = raw
   keys = ''
   for line in raw.split('\n'):
      line = line.strip()
      if line.upper().startswith('HINT:'):
         hint = line[5:].strip()
      elif line.upper().startswith('KEYS:'):
         keys = line[5:].strip()
   return hint, keys


def _cache_kluc(system_instrukcie: str, user_instrukcie: str) -> str:
   """Hash of the prompt without the rating history, so that a changed question text,
   answer or prompt template automatically misses the cache."""
   return hashlib.sha256(f'{system_instrukcie}\0{user_instrukcie}'.encode('utf-8')).hexdigest()[:16]


def _cache_subor(predmet: str, trieda: str, skupina: str, kapitola: str, fileid: str) -> str | None:
   """Path of the hint cache of one test (one file per fileid). It lives in /tmp, which is a
   tmpfs here: RAM only, shared by all workers, wiped on reboot. Returns None, which turns
   the cache off, when the directory cannot be created or is not private to this user."""
   try:
      os.makedirs(CACHE_ADRESAR, mode=0o700, exist_ok=True)
      st = os.lstat(CACHE_ADRESAR)
   except OSError:
      return None
   if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid() or st.st_mode & 0o077:
      return None
   nazov = re.sub(r'[^A-Za-z0-9_.-]', '_', f'{predmet}_{trieda}{skupina}_{kapitola}_{fileid}')
   return os.path.join(CACHE_ADRESAR, nazov + '.json')


def _cache_nacitaj(subor: str) -> dict:
   """Cache layout: {otazka_id: {kluc: {'generuj': bool, 'napovedy': [{'hint', 'keys', 'zle'}]}}}.
   Entries from the earlier single-hint layout ({'hint', 'keys'}) are upgraded on load."""
   try:
      with open(subor, encoding='utf-8') as f:
         data = json.load(f)
   except (OSError, ValueError):
      return {}
   if not isinstance(data, dict):
      return {}
   for varianty in data.values():
      for kluc, zaznam in varianty.items():
         if 'napovedy' not in zaznam:
            varianty[kluc] = {'generuj': False, 'napovedy': [{'hint': zaznam['hint'], 'keys': zaznam.get('keys', ''), 'zle': 0}]}
   return data


def _cache_zapis(subor: str, data: dict) -> None:
   tmp = subor + '.tmp'
   with open(tmp, 'w', encoding='utf-8') as f:
      json.dump(data, f, ensure_ascii=False)
   os.replace(tmp, subor)


def _cache_ziskaj(subor: str | None, otazka_id: str, kluc: str) -> dict | None:
   """Returns a random hint of the pool, or None when the caller has to generate a new one:
   the pool is empty, or a student rated a hint as unhelpful and this call claims the
   regeneration (the flag is cleared, so only one request generates)."""
   if not subor:
      return None
   zaznam = _cache_nacitaj(subor).get(otazka_id, {}).get(kluc)
   if zaznam and zaznam['generuj']:
      with FileLock(subor + '.lock'):
         data = _cache_nacitaj(subor)
         zaznam = data.get(otazka_id, {}).get(kluc)
         if zaznam and zaznam['generuj']:
            zaznam['generuj'] = False
            _cache_zapis(subor, data)
            return None
   if not zaznam or not zaznam['napovedy']:
      return None
   return random.choice(zaznam['napovedy'])


def _cache_uloz(subor: str | None, otazka_id: str, kluc: str, hint: str, keys: str) -> None:
   """Adds a hint to the pool; when the pool is full, the hint with the most unhelpful
   votes is dropped first."""
   if not subor:
      return
   with FileLock(subor + '.lock'):
      data = _cache_nacitaj(subor)
      zaznam = data.setdefault(otazka_id, {}).setdefault(kluc, {'generuj': False, 'napovedy': []})
      napovedy = zaznam['napovedy']
      if any(n['hint'] == hint for n in napovedy):
         return
      if len(napovedy) >= CACHE_MAX_NAPOVEDI:
         napovedy.remove(max(napovedy, key=lambda n: n['zle']))
      napovedy.append({'hint': hint, 'keys': keys, 'zle': 0})
      _cache_zapis(subor, data)


def _cache_zle(subor: str | None, otazka_id: str, hint: str) -> None:
   """Counts an unhelpful vote for the rated hint and requests a new hint for the next
   student asking about the same question (the hint itself stays in the pool)."""
   if not subor or not hint or not os.path.exists(subor):
      return
   with FileLock(subor + '.lock'):
      data = _cache_nacitaj(subor)
      zmena = False
      for zaznam in data.get(otazka_id, {}).values():
         for n in zaznam['napovedy']:
            if n['hint'] == hint:
               n['zle'] += 1
               zaznam['generuj'] = True
               zmena = True
      if zmena:
         _cache_zapis(subor, data)


def _cache_znovu_generuj(subor: str | None, otazka_id: str, kluc: str) -> None:
   """Gives the regeneration claimed by `_cache_ziskaj` back after a failed model call."""
   if not subor or not os.path.exists(subor):
      return
   with FileLock(subor + '.lock'):
      data = _cache_nacitaj(subor)
      zaznam = data.get(otazka_id, {}).get(kluc)
      if zaznam and zaznam['napovedy']:
         zaznam['generuj'] = True
         _cache_zapis(subor, data)


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
                            prvy_chunk: anyio.Event, cache_subor: str | None, otazka_id: str, cache_kluc: str) -> None:
   """Runs the model call independently of the client connection, so that hint and keys
   are always saved even if the client disconnects after the first line. Events for the
   client are passed through the stream; closing it marks the end."""

   def posli(udalost: tuple[str, dict]) -> None:
      _posli(send, udalost)

   full_text = ''
   hint_ulozeny = False
   try:
      client = ollama.AsyncClient()
      async for chunk in await client.chat(
         model=os.getenv('OLLAMA_MODEL', 'qwen3.5:9b'),
         messages=messages,
         stream=True,
         think=False,
         options={'temperature': 0.3, 'num_ctx': 4096, 'keep_alive': '45m'}
      ):
         text = chunk['message']['content']
         if not text:
            continue
         prvy_chunk.set()
         full_text += text
         if not hint_ulozeny:
            posli(('chunk', {'text': text}))
            if '\n' in full_text:
               hint_ulozeny = True
               hint, _ = _parsuj_hint_keys(full_text)
               _aktualizuj_zapis(subor, zapis_id, hint=hint)
               posli(('done', {'hint': hint}))

      hint, keys = _parsuj_hint_keys(full_text)
      if hint_ulozeny:
         if keys:
            _aktualizuj_zapis(subor, zapis_id, keys=keys)
      else:
         _aktualizuj_zapis(subor, zapis_id, hint=hint, keys=keys or None)
         posli(('done', {'hint': hint}))
      if hint:
         try:
            _cache_uloz(cache_subor, otazka_id, cache_kluc, hint, keys)
         except OSError as e:
            logger.error(f'chyba zapisu cache napovedy: {e}')
   except Exception as e:
      logger.error(f'chyba napoveda stream: {e}')
      posli(('napoveda_error', {'error': 'Služba nápovedy je momentálne zaneprázdnená.'}))
      try:
         _cache_znovu_generuj(cache_subor, otazka_id, cache_kluc)
      except OSError as e2:
         logger.error(f'chyba zapisu cache napovedy: {e2}')
   finally:
      prvy_chunk.set()
      send.close()


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

   predchadzajuce = _nacitaj_predchadzajuce_keys(subor, otazka_id)
   helped = [p['keys'] for p in predchadzajuce if p['val'] == '1']
   not_helped = [p['keys'] for p in predchadzajuce if p['val'] == '0']

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
      _aktualizuj_zapis(subor, zapis_id, hint=z_cache['hint'], keys=z_cache['keys'] or None)

      async def generate_cache():
         yield meta
         yield f'event: chunk\ndata: {json.dumps({"text": z_cache["hint"]})}\n\n'
         yield f'event: done\ndata: {json.dumps({"hint": z_cache["hint"]})}\n\n'

      return StreamingResponse(generate_cache(), media_type='text/event-stream', headers=headers)

   send, receive = anyio.create_memory_object_stream[tuple[str, dict]](max_buffer_size=float('inf'))
   prvy_chunk = anyio.Event()
   request.app.state.task_group.start_soon(_generuj_napovedu, messages, subor, zapis_id, send, request.app.state.logger,
                                           prvy_chunk, cache_subor, otazka_id, cache_kluc)
   request.app.state.task_group.start_soon(_hlas_cakanie, send, prvy_chunk)

   async def generate():
      yield meta
      async with receive:
         async for typ, data in receive:
            yield f'event: {typ}\ndata: {json.dumps(data)}\n\n'

   return StreamingResponse(generate(), media_type='text/event-stream', headers=headers)

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
         zapis.set('val', str(val))
         otazka_id = zapis.get('otazka_id', '')
         hint = zapis.findtext('hint') or ''
         tree = ET.ElementTree(root)
         ET.indent(tree, space='   ')
         tree.write(subor, encoding='UTF-8', xml_declaration=True)

      if val == 0:
         _cache_zle(_cache_subor(predmet, trieda, skupina, kapitola, fileid), otazka_id, hint)
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
