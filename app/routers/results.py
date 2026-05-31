# -*- coding: utf-8 -*-

from pathlib import Path
from app.mytypes import StringForm, StringPath, StringHeader
from app.utils import find_test, xslt_to_string, xquery_to_string
import lxml.etree as ET
from fastapi.concurrency import run_in_threadpool
from filelock import FileLock
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.get('/admin/showresult/{kluc}', response_class=HTMLResponse)
async def showresult(request: Request, kluc: StringPath):
   proc = request.app.state.proc
   node = find_test(proc, kluc, True, cache=request.app.state.kluc_cache)
   if node is None:
      return request.app.state.templates.TemplateResponse(request, 'index.html', {'detail': 'missingTest'}, status_code=404)
   try:
      vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/showresult.xsl', xdm_node=node, xslt_pools=request.app.state.xslt_pools)
      return HTMLResponse(content=vysledok, status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba showresult: {e}')
      raise HTTPException(status_code=400, detail=str(e))

@router.post('/admin/savemarks/{kluc}')
async def savemarks(request: Request, response: Response, kluc: StringPath, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, dat: StringForm, skupina: StringForm = ''):
   adresar = f'./res/xml/answers/{predmet}'
   cesta = Path(f'{adresar}/{predmet}_{trieda}{skupina}_{kapitola}_{fileid}.xml')
   async with request.form() as form:
      form_data = {k: v for k, v in form.items() if k not in {'kluc', 'predmet', 'trieda', 'skupina', 'kapitola', 'fileid', 'dat'}}
   lock = FileLock(f'{cesta}.lock')
   try:
      await run_in_threadpool(write_marks, lock, cesta, form_data, kluc, dat)
   except Exception as e:
      request.app.state.logger.error(f'chyba savemarks: {e}')
      raise HTTPException(status_code=400, detail='chyba znamky: ' + str(e))
   response.status_code = 201
   return

def write_marks(lock: FileLock, cesta: Path, form_data: dict, kluc: str, dat: str) -> None:
   with lock:
      try:
         xmlParser = ET.XMLParser(remove_blank_text=True)
         tree = ET.parse(cesta, xmlParser)
         root = tree.getroot()
         testxml = next(iter(root.xpath('.//test[@id=$kluc][@dat=$dat]', kluc=kluc, dat=dat)), None)  # type: ignore[arg-type]
         if testxml is None:
            raise Exception(f'test {kluc} nenájdený v súbore')
         for key, value in form_data.items():
            typ, idotazky = key.split('_', 1)
            otazkaxml = next(iter(testxml.xpath('.//otazka[@id=$id]', id=idotazky)), None)  # type: ignore[union-attr]
            if otazkaxml is None:
               otazkaxml = ET.SubElement(testxml, 'otazka', attrib={'id': idotazky})  # type: ignore[arg-type]
            param = 'body' if typ in ('h', 'bh') else 'koment'
            otazkaxml.set(param, value)
         ET.indent(tree, space='   ')
         tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
      except Exception as e:
         raise Exception('chyba znamky: ' + str(e))

@router.post('/admin/groupstatistics', response_class=HTMLResponse)
async def groupstatistics(request: Request, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = '', X_Remote_User: StringHeader = ''):
   proc = request.app.state.proc
   try:
      params = {
         'predmet': predmet,
         'trieda': trieda,
         'skupina': skupina,
         'kapitola': kapitola,
         'fileid': fileid,
         'autor': X_Remote_User
      }
      xml_data = xquery_to_string(proc, './res/xquery/groupstatistics.xq', params=params)
      xml_node = proc.parse_xml(xml_text=xml_data)
      vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/groupstatistics.xsl', xdm_node=xml_node, xslt_pools=request.app.state.xslt_pools)
      return HTMLResponse(content=vysledok, status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba groupstatistics: {e}')
      raise HTTPException(status_code=400, detail=str(e))
