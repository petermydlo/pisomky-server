# -*- coding: utf-8 -*-

from pathlib import Path
from app.mytypes import StringForm, StringFormOptional, StringPath, StringHeader
from app.utils import find_test, xslt_to_string, xquery_to_string, test_xml_path, get_time_state
import lxml.etree as ET
from fastapi.concurrency import run_in_threadpool
from filelock import FileLock
from fastapi import APIRouter, Request, Response
from typing import TYPE_CHECKING
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import HTTPException

if TYPE_CHECKING:
   from saxonche import PySaxonProcessor

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
   try:
      test_xml_path(predmet, trieda, skupina, kapitola, fileid)
   except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e))
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
            otazkaxml = next(iter(testxml.xpath('.//otazka[@id=$id]', id=idotazky)), None)
            if otazkaxml is None:
               otazkaxml = ET.SubElement(testxml, 'otazka', attrib={'id': idotazky})
            param = 'body' if typ in ('h', 'bh') else 'koment'
            otazkaxml.set(param, value)
         ET.indent(tree, space='   ')
         tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
      except Exception as e:
         raise Exception('chyba znamky: ' + str(e))

@router.post('/admin/setrevealed', response_class=JSONResponse)
async def setrevealed(request: Request, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, odhalene: StringForm, skupina: StringForm = '', kluc: StringFormOptional = None):
   """Odhali (odhalene=1) alebo skryje (odhalene=0) zakom spravne odpovede; bez kluca pre celu sadu testov."""
   try:
      cesta_testov = test_xml_path(predmet, trieda, skupina, kapitola, fileid)
   except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e))
   cesta = Path(cesta_testov.replace('/tests/', '/answers/', 1))
   if not cesta.is_file():
      raise HTTPException(status_code=404, detail='Súbor odpovedí nenájdený')
   odhalit = odhalene == '1'
   skoncene = skoncene_testy(request.app.state.proc, cesta_testov) if odhalit else set()
   lock = FileLock(f'{cesta}.lock')
   try:
      zmenene = await run_in_threadpool(write_odhalene, lock, cesta, odhalit, skoncene, kluc)
   except HTTPException:
      raise
   except Exception as e:
      request.app.state.logger.error(f'chyba setrevealed: {e}')
      raise HTTPException(status_code=400, detail='chyba setrevealed: ' + str(e))
   return JSONResponse(content={'zmenene': zmenene}, status_code=200)

def skoncene_testy(proc: 'PySaxonProcessor', cesta_testov: str) -> set[str]:
   """Vrati id testov, ktorym uz skoncil cas pisania (stav 'after')."""
   node = proc.parse_xml(xml_file_name=cesta_testov)
   xp = proc.new_xpath_processor()
   xp.set_context(xdm_item=node)
   return {t.get_attribute_value('id') for t in (xp.evaluate('/testy/test') or []) if get_time_state(t, t.get_parent()) == 'after'}

def write_odhalene(lock: FileLock, cesta: Path, odhalit: bool, skoncene: set[str], kluc: str | None = None) -> list[str]:
   """Nastavi/zrusi test/@odhalene v subore odpovedi; odhalit sa daju len testy zo 'skoncene' a s elementom v subore."""
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      testy = [t for t in tree.getroot().findall('test') if kluc is None or t.get('id') == kluc]
      if kluc is not None and not testy:
         raise HTTPException(status_code=404, detail='Test nenájdený v súbore odpovedí')
      if odhalit and kluc is not None and kluc not in skoncene:
         raise HTTPException(status_code=409, detail='Test ešte neskončil')
      zmenene = []
      for t in testy:
         if odhalit:
            if t.get('id') in skoncene and t.get('odhalene') != '1':
               t.set('odhalene', '1')
               zmenene.append(str(t.get('id')))
         elif 'odhalene' in t.attrib:
            del t.attrib['odhalene']
            zmenene.append(str(t.get('id')))
      if zmenene:
         ET.indent(tree, space='   ')
         tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
      return zmenene

@router.post('/admin/groupstatistics', response_class=HTMLResponse)
async def groupstatistics(request: Request, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = '', X_Remote_User: StringHeader = ''):
   try:
      test_xml_path(predmet, trieda, skupina, kapitola, fileid)
   except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e))
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
