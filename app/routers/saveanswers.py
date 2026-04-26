# -*- coding: utf-8 -*-

from app.mytypes import StringForm, StringPath, FileListOptional
from datetime import datetime
from pathlib import Path
from app.utils import check_time
import lxml.etree as ET
from fastapi.concurrency import run_in_threadpool
from filelock import FileLock
from fastapi import APIRouter, Request, Response
from fastapi.exceptions import HTTPException

router = APIRouter()

#saveanswers
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
         with open(cesta, 'w') as sub:
            sub.write('<?xml version="1.1" encoding="UTF-8"?>\n')
            sub.write('<odpovede xml:lang="sk">')
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
