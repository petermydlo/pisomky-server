# -*- coding: utf-8 -*-

import json
import os
import secrets
from datetime import datetime
from filelock import FileLock
from lxml import etree as ET
import ollama
from dotenv import load_dotenv
from app.utils import find_test, find_question, get_test_metadata, xquery_to_string, xslt_to_string
from app.mytypes import StringQuery, IntForm, StringForm
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.exceptions import HTTPException

load_dotenv()

router = APIRouter()


def _najdi_napovedu(otazka_id: str, spravna_odpoved: str | None = None, logger=None) -> dict | None:
   otazka_el, _ = find_question(otazka_id)
   if otazka_el is None:
      return None
   try:
      spravna_key = None
      if spravna_odpoved:
         for odp in otazka_el.findall('odpoved[@spravna="1"]'):
            if odp.text and odp.text.strip() == spravna_odpoved:
               spravna_key = odp.get('napoveda')
               break
      napovedy_els = otazka_el.findall('napoveda')
      if spravna_key:
         keys_ = [k.strip() for k in spravna_key.split(',')]
         napovedy_els = [n for n in napovedy_els if not n.get('pre') or n.get('pre') in keys_]
      else:
         napovedy_els = [n for n in napovedy_els if not n.get('pre')]
      napovedy = [n.text.strip() for n in napovedy_els if n.text and n.text.strip()] or None
      vzor_el = otazka_el.find('vzor')
      vzor = vzor_el.text.strip() if vzor_el is not None and vzor_el.text else None
      klucove = [s.text.strip() for s in otazka_el.findall('klucove_slova/slovo') if s.text]
      return {'napovedy': napovedy, 'vzor': vzor, 'klucove': klucove}
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
      zaznamy = tree.xpath('.//zapis[@otazka_id=$id]', id=otazka_id)[-limit:]  # type: ignore[arg-type]
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
         root = ET.Element('feedback', attrib={'predmet': predmet, 'trieda': trieda, 'skupina': skupina, 'kapitola': kapitola, 'fileid': fileid})
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
   vzor = napovedy_data.get('vzor') if isinstance(napovedy_data, dict) else None
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
      vzor=vzor,
      klucove=klucove or [],
      helped=helped,
      not_helped=not_helped,
      spravna_odpoved=spravna_odpoved,
   )

   messages = [
      {'role': 'system', 'content': system_instrukcie},
      {'role': 'user', 'content': user_instrukcie}
   ]

   zapis_id = secrets.token_hex(8)
   remaining = pocet_otazok - pouzite - 1
   _uloz_zapis(subor, zapis_id, otazka_id, test_id, predmet, trieda, skupina, kapitola, fileid)

   async def generate():
      try:
         yield f'event: meta\ndata: {json.dumps({"zapis_id": zapis_id, "remaining": remaining})}\n\n'

         full_text = ''
         done_sent = False
         client = ollama.AsyncClient()
         async for chunk in await client.chat(
            model=os.getenv('OLLAMA_MODEL', 'llama3.1'),
            messages=messages,
            stream=True,
            options={'temperature': 0.3, 'num_ctx': 32768, 'keep_alive': '45m'}
         ):
            text = chunk['message']['content']
            if text:
               full_text += text
               if not done_sent:
                  yield f'event: chunk\ndata: {json.dumps({"text": text})}\n\n'
                  if '\n' in full_text:
                     done_sent = True
                     hint, _ = _parsuj_hint_keys(full_text)
                     _aktualizuj_zapis(subor, zapis_id, hint=hint)
                     yield f'event: done\ndata: {json.dumps({"hint": hint})}\n\n'

         if not done_sent:
            hint, keys = _parsuj_hint_keys(full_text)
            _aktualizuj_zapis(subor, zapis_id, hint=hint, keys=keys or None)
            yield f'event: done\ndata: {json.dumps({"hint": hint})}\n\n'
         else:
            _, keys = _parsuj_hint_keys(full_text)
            if keys:
               _aktualizuj_zapis(subor, zapis_id, keys=keys)

      except Exception as e:
         request.app.state.logger.error(f'chyba napoveda stream: {e}')
         yield f'event: napoveda_error\ndata: {json.dumps({"error": "Služba nápovedy je momentálne zaneprázdnená."})}\n\n'

   return StreamingResponse(
      generate(),
      media_type='text/event-stream',
      headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
   )

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
         tree = ET.ElementTree(root)
         ET.indent(tree, space='   ')
         tree.write(subor, encoding='UTF-8', xml_declaration=True)

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
