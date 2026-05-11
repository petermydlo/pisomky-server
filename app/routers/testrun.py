# -*- coding: utf-8 -*-

from datetime import datetime
from pathlib import Path
from app.mytypes import StringForm, StringPath, StringFormOptional, FileListOptional
from app.utils import check_time, modify_test_xml, find_test_file, test_xml_path, get_testy_autor, update_category, update_question, store_mcq_scores
import lxml.etree as ET
from fastapi.concurrency import run_in_threadpool
from filelock import FileLock
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.post('/saveanswers/{kluc}')
async def saveanswers(request: Request, response: Response, kluc: StringPath, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = '', subory: FileListOptional = None):
   proc = request.app.state.proc
   if not check_time(proc, kluc):
      raise HTTPException(status_code=403, detail='Test už skončil!')
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
   async with request.form() as form:
      form_data = {k: v for k, v in form.items() if k not in {'predmet', 'trieda', 'skupina', 'kapitola', 'fileid', 'subory'}}
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

@router.post('/stoptime/{kluc}', response_class=HTMLResponse)
async def stoptime(request: Request, kluc: StringPath, stop: StringForm):
   def _modify(tree):
      tests = [t for t in tree.findall('.//test') if t.get('id') == kluc]
      if not tests:
         raise HTTPException(status_code=404, detail='Test nenájdený')
      tests[0].set('stop', stop)

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
async def set_paused(request: Request, id: StringForm, typ: StringForm, paused: StringForm):
   try:
      hodnota = '1' if paused == '1' else None
      if typ == 'kategoria':
         ok = update_category(id, {'paused': hodnota})
      elif typ == 'otazka':
         ok = update_question(id, {'paused': hodnota})
      else:
         raise HTTPException(status_code=400, detail=f'Neznámy typ: {typ}')
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
