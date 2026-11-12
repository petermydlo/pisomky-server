# -*- coding: utf-8 -*-

import re
from datetime import datetime
from pathlib import Path
from app.mytypes import StringForm, StringPath, StringFormOptional, StringHeader, FileListOptional
from app.utils import find_test, get_test_metadata, modify_test_xml, find_test_file, test_xml_path, get_testy_autor, update_category, update_question, store_mcq_scores, find_category, find_question
from app.permissions import check_permission, predmet_from_cesta
import lxml.etree as ET
from fastapi.concurrency import run_in_threadpool
from filelock import FileLock
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

#odpoved ziaka je text jednej otazky; dlhsia (omylom vlozeny cely subor) sa orezie, aby neprerastal XML
MAX_DLZKA_ODPOVEDE = 20000
#znaky, ktore XML 1.0 nepripusta (napr. \x00, \x0b pri vlozeni z PDF); jediny taky znak by inak zhodil ulozenie vsetkych odpovedi
_NEPLATNE_XML_ZNAKY = re.compile('[^\t\n\r\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]')

def ocisti_odpovede(form_data: dict, povolene_id: set[str]) -> dict[str, str]:
   """Z formulara ziaka necha len odpovede na otazky jeho testu (kluc = @id otazky), bez neplatnych XML znakov a
   najviac MAX_DLZKA_ODPOVEDE dlhe; ine polia sa zahodia, ziak nesmie zapisovat do suboru lubovolne elementy."""
   return {k: _NEPLATNE_XML_ZNAKY.sub('', v)[:MAX_DLZKA_ODPOVEDE] for k, v in form_data.items() if k in povolene_id and isinstance(v, str)}

@router.post('/saveanswers/{kluc}')
async def saveanswers(request: Request, response: Response, kluc: StringPath, subory: FileListOptional = None):
   proc = request.app.state.proc
   test_node = find_test(proc, kluc, cache=request.app.state.kluc_cache)
   if test_node is None:
      raise HTTPException(status_code=403, detail='Test už skončil!')
   #predmet, trieda, ... sa berú z testu podľa kľúča; hodnoty z formulára sa ignorujú (žiak ich nesmie voliť, idú do ciest k súborom)
   predmet, trieda, skupina, kapitola, fileid = get_test_metadata(proc, test_node)
   adresar = f'./res/xml/answers/{predmet}'
   Path(adresar).mkdir(parents=True, exist_ok=True)
   if subory is not None:
      for subor in subory:
         try:
            nazov = Path(subor.filename or '').name
            obsah = await subor.read()
            with open(f'{adresar}/{predmet}_{trieda}{skupina}_{kapitola}_{fileid}_{kluc}-{nazov}_subor', 'wb') as f:
               f.write(obsah)
         except Exception as e:
            request.app.state.logger.error(f'chyba subory: {e}')
            raise HTTPException(status_code=400, detail='chyba subory: ' + str(e))
   cesta = Path(f'{adresar}/{predmet}_{trieda}{skupina}_{kapitola}_{fileid}.xml')
   xp = proc.new_xpath_processor()
   xp.set_context(xdm_item=test_node)
   id_otazok = {o.get_attribute_value('id') for o in (xp.evaluate('otazka') or [])}
   async with request.form() as form:
      form_data = ocisti_odpovede(dict(form.items()), id_otazok)
   lock = FileLock(f'{cesta}.lock')
   try:
      await run_in_threadpool(write_answers, lock, cesta, form_data, adresar, predmet, trieda, skupina, kapitola, fileid, kluc)
   except Exception as e:
      request.app.state.logger.error(f'chyba odpovede: {e}')
      raise HTTPException(status_code=400, detail='chyba odpovede: ' + str(e))
   response.status_code = 201
   return

def write_answers(lock: FileLock, cesta: Path, form_data: dict, adresar: str, predmet: str, trieda: str, skupina: str, kapitola: str, fileid: str, kluc: str) -> None:
   with lock:
      if not(cesta.is_file()):
         autor = get_testy_autor(predmet, trieda, skupina, kapitola, fileid)
         with open(cesta, 'w') as sub:
            sub.write('<?xml version="1.1" encoding="UTF-8"?>\n')
            sub.write(f'<odpovede xml:lang="sk" predmet="{predmet}" trieda="{trieda}" skupina="{skupina}" kapitola="{kapitola}" fileid="{fileid}" autor="{autor}">')
            sub.write('</odpovede>')
      try:
         xmlParser = ET.XMLParser(remove_blank_text=True)
         tree = ET.parse(f'{adresar}/{predmet}_{trieda}{skupina}_{kapitola}_{fileid}.xml', xmlParser)
         root = tree.getroot()
         dat = datetime.now().isoformat(timespec='seconds')
         existujuci = next(iter(root.xpath('test[@id=$id]', id=kluc)), None)  # type: ignore[arg-type]
         ma_odpovede = bool(form_data)
         if existujuci is not None:
            if not ma_odpovede:
               existujuci.set('dat', dat)
            else:
               root.remove(existujuci)
               testxml = ET.SubElement(root, 'test', attrib={'id': kluc, 'dat': dat})
               for key, value in form_data.items():
                  otazkaxml = ET.SubElement(testxml, 'otazka', attrib={'id': key})
                  otazkaxml.text = value
         else:
            testxml = ET.SubElement(root, 'test', attrib={'id': kluc, 'dat': dat})
            for key, value in form_data.items():
               otazkaxml = ET.SubElement(testxml, 'otazka', attrib={'id': key})
               otazkaxml.text = value
         ET.indent(tree, space='   ')
         tree.write(f'{adresar}/{predmet}_{trieda}{skupina}_{kapitola}_{fileid}.xml', encoding='utf-8', xml_declaration=True, pretty_print=True)
      except Exception as e:
         raise Exception('chyba odpovede: ' + str(e))

def _cas(hodnota: str | None) -> datetime | None:
   try:
      return datetime.fromisoformat((hodnota or '').strip())
   except ValueError:
      return None

def nastav_stop(tree, kluc: str, teraz: datetime) -> None:
   """Ukonci test 'kluc' serverovym casom 'teraz'. Koniec sa nikdy nepredlzi: ak test uz skoncil
   (stop testu alebo sady je v minulosti), ostane tak; cas z formulara sa nepouziva, ziak ho nesmie volit."""
   tests = [t for t in tree.findall('.//test') if t.get('id') == kluc]
   if not tests:
      raise HTTPException(status_code=404, detail='Test nenájdený')
   test = tests[0]
   stop = _cas(test.get('stop')) or _cas(tree.getroot().get('stop'))
   if stop is not None and stop <= teraz:
      return
   test.set('stop', teraz.strftime('%Y-%m-%dT%H:%M'))

@router.post('/stoptime/{kluc}', response_class=HTMLResponse)
async def stoptime(request: Request, kluc: StringPath):
   def _modify(tree):
      nastav_stop(tree, kluc, datetime.now())

   try:
      cesta = find_test_file(kluc, request.app.state.kluc_cache)
      if not cesta:
         raise HTTPException(status_code=404, detail='Test nenájdený')
      modify_test_xml(cesta, _modify)
      await run_in_threadpool(store_mcq_scores, kluc, request.app.state.kluc_cache)
      return HTMLResponse(content='ok', status_code=204)
   except HTTPException:
      raise
   except Exception as e:
      raise HTTPException(status_code=400, detail='chyba stoptime: ' + str(e))

@router.post('/admin/setpaused', response_class=JSONResponse)
async def set_paused(request: Request, id: StringForm, typ: StringForm, paused: StringForm, X_Remote_User: StringHeader):
   try:
      hodnota = '1' if paused == '1' else None
      if typ == 'kategoria':
         _, cesta = find_category(id)
      elif typ == 'otazka':
         _, cesta = find_question(id)
      else:
         raise HTTPException(status_code=400, detail=f'Neznámy typ: {typ}')
      if cesta is None:
         raise HTTPException(status_code=404, detail='Nenájdené')
      #pozastavenie meni banku otazok, rovnako ako uprava (akcia 'edit')
      check_permission(request.app.state.perm_cache, X_Remote_User, 'edit', predmet_from_cesta(cesta))
      ok = update_category(id, {'paused': hodnota}) if typ == 'kategoria' else update_question(id, {'paused': hodnota})
      if not ok:
         raise HTTPException(status_code=404, detail='Nenájdené')
      return JSONResponse(content={'ok': True}, status_code=200)
   except HTTPException:
      raise
   except Exception as e:
      request.app.state.logger.error(f'chyba setpaused: {e}')
      raise HTTPException(status_code=400, detail=str(e))

@router.post('/admin/changetime', response_class=HTMLResponse)
async def changetime(request: Request, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = '', start: StringFormOptional = None, stop: StringFormOptional = None, kluc: StringFormOptional = None):
   def _modify(tree):
      root = tree.getroot()

      def _set_attr(node, attr, value):
         if value is not None:
            if value.strip() != '':
               node.set(attr, value)
            else:
               node.attrib.pop(attr, None)

      if kluc is None:
         _set_attr(root, 'start', start)
         _set_attr(root, 'stop', stop)
      else:
         tests = [t for t in tree.findall('.//test') if t.get('id') == kluc]
         if not tests:
            raise HTTPException(status_code=404, detail='Test nenájdený')
         test = tests[0]
         _set_attr(test, 'start', start)
         _set_attr(test, 'stop', stop)
   try:
      modify_test_xml(test_xml_path(predmet, trieda, skupina, kapitola, fileid), _modify)
      return HTMLResponse(content='ok', status_code=204)
   except HTTPException:
      raise
   except Exception as e:
      raise HTTPException(status_code=400, detail='chyba changetime: ' + str(e))
