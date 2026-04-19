# -*- coding: utf-8 -*-

from app.mytypes import StringForm, StringPath
from pathlib import Path
import lxml.etree as ET
from fastapi.concurrency import run_in_threadpool
from filelock import FileLock
from fastapi import APIRouter, Request, Response
from fastapi.exceptions import HTTPException

router = APIRouter()

#savemarks
@router.post('/admin/savemarks/{kluc}')
async def savemarks(request: Request, response: Response, kluc: StringPath, predmet: StringForm, trieda: StringForm, kapitola: StringForm, dat: StringForm, skupina: StringForm = ''):
   adresar = f'./res/xml/answers/{predmet}'
   cesta = Path(f'{adresar}/{predmet}_{trieda}{skupina}_{kapitola}.xml')
   async with request.form() as form:
      form_data = {k: v for k, v in form.items() if k not in {'kluc', 'predmet', 'trieda', 'skupina', 'kapitola', 'dat'}}
   lock = FileLock(f'{cesta}.lock')
   try:
      await run_in_threadpool(write_marks, lock, cesta, form_data, kluc, dat)
   except Exception as e:
      request.app.state.logger.error(f'chyba savemarks: {e}')
      raise HTTPException(status_code=400, detail='chyba znamky: ' + str(e))
   response.status_code = 201
   return

def write_marks(lock, cesta, form_data, kluc, dat):
   with lock:
      try:
         xmlParser = ET.XMLParser(remove_blank_text=True)
         tree = ET.parse(cesta, xmlParser)
         root = tree.getroot()
         testxml = next(iter(root.xpath(".//test[@id=$kluc][@dat=$dat]", kluc=kluc, dat=dat)), None)
         for key, value in form_data.items():
            typ, idotazky = key.split('_', 1)
            otazkaxml = next(iter(testxml.xpath(".//otazka[@id=$id]", id=idotazky)), None)
            if otazkaxml is None:
               otazkaxml = ET.SubElement(testxml, 'otazka', attrib={'id': idotazky})
            param = 'body' if typ in ('h', 'bh') else 'koment'
            otazkaxml.set(param, value)
         ET.indent(tree, space='   ')
         tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
      except Exception as e:
         raise Exception('chyba znamky: ' + str(e))
