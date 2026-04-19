# -*- coding: utf-8 -*-

import json
import os
import secrets
from datetime import datetime
from filelock import FileLock
from lxml import etree as ET
import ollama
from dotenv import load_dotenv
from app.utils import find_test, find_question, get_test_metadata
from app.mytypes import StringQuery
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

load_dotenv()

router = APIRouter()

def _najdi_napovedu(otazka_id, predmet, spravna_odpoved=None, logger=None):
   otazka_el, cesta = find_question(otazka_id)
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


def _nacitaj_predchadzajuce_keys(subor, otazka_id, limit=10):
   """Nacita klucove slova z predchadzajucich napovedi pre danu otazku."""
   if not os.path.exists(subor):
      return []
   try:
      tree = ET.parse(subor)
      zaznamy = tree.findall(f'.//zapis[@otazka_id="{otazka_id}"]')
      zaznamy = zaznamy[-limit:]
      result = []
      for z in zaznamy:
         keys_el = z.find('keys')
         if keys_el is not None and keys_el.text:
            val = z.get('val', '')
            result.append({'keys': keys_el.text.strip(), 'val': val})
      return result
   except Exception:
      return []


def _aktualizuj_keys(subor, zapis_id, keys):
   if not os.path.exists(subor):
      return
   lock = FileLock(subor + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(subor, xmlParser)
      root = tree.getroot()
      zapis = root.find(f'.//zapis[@id="{zapis_id}"]')
      if zapis is None:
         return
      keys_el = zapis.find('keys')
      if keys_el is None:
         keys_el = ET.SubElement(zapis, 'keys')
      keys_el.text = keys
      ET.indent(tree, space='   ')
      tree.write(subor, encoding='UTF-8', xml_declaration=True)


def _uloz_zapis(subor, zapis_id, otazka_id, test_id, hint, keys):
   os.makedirs(os.path.dirname(subor), exist_ok=True)
   lock = FileLock(subor + '.lock')
   with lock:
      if os.path.exists(subor):
         xmlParser = ET.XMLParser(remove_blank_text=True)
         tree = ET.parse(subor, xmlParser)
         root = tree.getroot()
      else:
         root = ET.Element('feedback')
         tree = ET.ElementTree(root)
      zapis = ET.SubElement(root, 'zapis')
      zapis.set('id', zapis_id)
      zapis.set('datum', datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
      zapis.set('otazka_id', otazka_id)
      zapis.set('test_id', test_id)
      zapis.set('val', '')
      hint_el = ET.SubElement(zapis, 'hint')
      hint_el.text = hint
      if keys:
         keys_el = ET.SubElement(zapis, 'keys')
         keys_el.text = keys
      ET.indent(tree, space='   ')
      tree.write(subor, encoding='UTF-8', xml_declaration=True)


def _parsuj_hint_keys(raw):
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
   safe_otazka_id = otazka_id.replace("'", "")

   test_node = find_test(proc, test_id, admin=True, cache=request.app.state.kluc_cache)
   if not test_node:
      return JSONResponse({'error': 'Test nenájdený'}, status_code=404)

   xsltpath.set_context(xdm_item=test_node)
   otazka = xsltpath.evaluate_single(f'otazka[@id="{safe_otazka_id}"]')
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

   predmet, trieda, skupina, kapitola = get_test_metadata(proc, test_node)

   napovedy_data = _najdi_napovedu(safe_otazka_id, predmet, spravna_odpoved, request.app.state.logger) if predmet else None
   napovedy = napovedy_data.get('napovedy') if isinstance(napovedy_data, dict) else napovedy_data
   vzor = napovedy_data.get('vzor') if isinstance(napovedy_data, dict) else None
   klucove = napovedy_data.get('klucove') if isinstance(napovedy_data, dict) else []

   subor = f'./res/xml/feedback/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}.xml'
   predchadzajuce = _nacitaj_predchadzajuce_keys(subor, safe_otazka_id)

   system_instrukcie = """\
   You are a helpful hint provider for a testing system.
   Treat every request as a completely isolated task. Ignore any previous context.

   ## Your role
   - Give the student exactly one short hint
   - Nudge them toward the correct answer without revealing it
   - Never mention the correct answer directly

   ## Language
   ALWAYS respond in English, regardless of the language of the question or hints.

   ## Response format
   Respond in EXACTLY this format, two lines only, nothing else:
   HINT: <one sentence hint>
   KEYS: <3-5 comma-separated key concepts in English>
   """

   if napovedy or vzor or klucove:
      hints_formatted = '\n'.join(f'- {h}' for h in napovedy) if napovedy else ''
      vzor_str = f'\nModel answer (DO NOT reveal directly, only hint toward it): {vzor}' if vzor else ''
      klucove_str = f"\nKey concepts to hint toward: {', '.join(klucove)}" if klucove else ''
      hint_instrukcie = f"""\
   ## Teacher's hints
   {hints_formatted} {vzor_str} {klucove_str}

   Use these as inspiration or improve them. Do not reveal the answer.
   """
   else:
      hint_instrukcie = """\
   ## Hint instructions
   Give the student a single short hint without revealing the answer.
   """

   if predchadzajuce:
      helped = [p['keys'] for p in predchadzajuce if p['val'] == '1']
      not_helped = [p['keys'] for p in predchadzajuce if p['val'] == '0']
      hist_parts = []
      if helped:
         hist_parts.append('Helpful approaches: ' + '; '.join(helped))
      if not_helped:
         hist_parts.append('Less helpful approaches: ' + '; '.join(not_helped))
      historia_instrukcie = f"""\

   ## Previous hint history for this question
   {chr(10).join(hist_parts)}
   Prefer different key concepts than already used. Avoid less helpful approaches.
   """
   else:
      historia_instrukcie = ''

   if spravna_odpoved:
      user_instrukcie = f"""\
   ## Question
   {znenie_text}

   ## Options
   {', '.join(moznosti)}

   {hint_instrukcie}{historia_instrukcie}
   ## Correct answer (for your reference only — do not reveal)
   {spravna_odpoved}
   """
   else:
      user_instrukcie = f"""\
   ## Question
   {znenie_text}

   {hint_instrukcie}{historia_instrukcie}
   """

   messages = [
      {'role': 'system', 'content': system_instrukcie},
      {'role': 'user', 'content': user_instrukcie}
   ]

   zapis_id = secrets.token_hex(8)

   async def generate():
      try:
         yield f'event: meta\ndata: {json.dumps({"zapis_id": zapis_id})}\n\n'

         full_text = ''
         done_sent = False
         client = ollama.AsyncClient()
         async for chunk in await client.chat(
            model=os.getenv('OLLAMA_MODEL', 'llama3.1'),
            messages=messages,
            stream=True,
            options={'temperature': 0.3, 'num_ctx': 32768}
         ):
            text = chunk['message']['content']
            if text:
               full_text += text
               if not done_sent:
                  yield f'event: chunk\ndata: {json.dumps({"text": text})}\n\n'
                  if '\n' in full_text:
                     done_sent = True
                     hint, _ = _parsuj_hint_keys(full_text)
                     _uloz_zapis(subor, zapis_id, safe_otazka_id, test_id, hint, '')
                     yield f'event: done\ndata: {json.dumps({"hint": hint})}\n\n'

         if not done_sent:
            hint, keys = _parsuj_hint_keys(full_text)
            _uloz_zapis(subor, zapis_id, safe_otazka_id, test_id, hint, keys)
            yield f'event: done\ndata: {json.dumps({"hint": hint})}\n\n'
         else:
            _, keys = _parsuj_hint_keys(full_text)
            if keys:
               _aktualizuj_keys(subor, zapis_id, keys)

      except Exception as e:
         request.app.state.logger.error(f'chyba napoveda stream: {e}')
         yield f'event: napoveda_error\ndata: {json.dumps({"error": "Služba nápovedy je momentálne zaneprázdnená."})}\n\n'

   return StreamingResponse(
      generate(),
      media_type='text/event-stream',
      headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
   )
