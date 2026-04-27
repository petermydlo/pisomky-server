# -*- coding: utf-8 -*-

import os
import logging
from fastapi import FastAPI, Request
from saxonche import PySaxonProcessor
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.utils import find_test, xslt_to_string, get_test_metadata
from app.routers.ai import _spocitaj_napovedy_testu
from fastapi.exceptions import HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.mytypes import BoolQuery, StringPath, StringHeader
from app.routers import tests
from app.routers import testrun
from app.routers import results
from app.routers import downloads
from app.routers import questions
from app.routers import ai
from app.routers import importanswers
from app.routers import aievaluate
from app.routers.aiproviders import get_provider


async def custom_http_exception_handler(request: Request, exc: HTTPException):
   return app.state.templates.TemplateResponse('error404_pisomky.html', {'request': request}, status_code=404)

exceptions = {404: custom_http_exception_handler}

app = FastAPI(exception_handlers=exceptions, docs_url=None, redoc_url=None)  # type: ignore[arg-type]

#globalny Saxon procesor aby sa nemusel vytvarat niekolkokrat
app.state.proc = PySaxonProcessor(license=False)

#globalne Jinja2Templates
app.state.templates = Jinja2Templates(directory='./app/templates')

#cache pre rychle vyhladavanie testov podla kluca
app.state.kluc_cache = {}

#cache pre rychle vyhladavanie otazok podla id
app.state.otazka_cache = {}

#cache pre rychle vyhladavanie kategorii podla id
app.state.kategoria_cache = {}

#cache pre rychle vyhladavanie kapitol podla id
app.state.kapitola_cache = {}

#pool skompilovaných XSLT šablón (stylesheet_file -> Queue[XsltExecutable])
app.state.xslt_pools = {}

#AI provider pre import skenovanych odpovedi
app.state.ai_provider = get_provider()

logging.basicConfig(level=logging.INFO)
app.state.logger = logging.getLogger("pisomky")

#spracovanie poziadaviek, len ak maju spravne nastavenu hlavicku Host
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[os.getenv('ALLOWED_HOST', 'pisomky.ternac.net')])

#zakomponovanie ineho suboru
app.include_router(tests.router)
app.include_router(testrun.router)
app.include_router(results.router)
app.include_router(downloads.router)
app.include_router(questions.router)
app.include_router(ai.router)
app.include_router(importanswers.router)
app.include_router(aievaluate.router)

#adresar so statickymi zdrojmi
app.mount('/pubres', StaticFiles(directory='./pubres'), name='pubres')

@app.on_event('shutdown')
def shutdown_event():
   app.state.proc.close()

@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
   return request.app.state.templates.TemplateResponse('index.html', {'request': request})

@app.get('/admin', response_class=HTMLResponse)
async def admin(request: Request, X_Remote_User: StringHeader):
   proc = request.app.state.proc
   try:
      vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/overviewtests.xsl', params={'autor': X_Remote_User}, xslt_pools=request.app.state.xslt_pools)
      return HTMLResponse(content=vysledok, status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba admin: {e}')
      raise HTTPException(status_code=400, detail=str(e))

@app.get('/{kluc}', response_class=HTMLResponse)
async def view(request: Request, kluc: StringPath, edit: BoolQuery = False):
   if not (kluc := kluc.strip()): #ked uzivatel zada kluc z prazdnych znakov
      return request.app.state.templates.TemplateResponse('index.html', {'request': request, 'detail': 'wrongKey'}, status_code=400)
   proc = request.app.state.proc
   node = find_test(proc, kluc, False, cache=request.app.state.kluc_cache)
   if node is None: #ked nenajdem test prisluchajuci danemu klucu
      return request.app.state.templates.TemplateResponse('index.html', {'request': request, 'detail': 'missingTest'}, status_code=404)
   try:
      xp = proc.new_xpath_processor()
      xp.set_context(xdm_item=node)
      pocet_otazok = int(xp.evaluate_single('count(otazka)') or 0)
      predmet, trieda, skupina, kapitola, fileid = get_test_metadata(proc, node)
      subor = f'./res/xml/feedback/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}_{fileid}.xml'
      napovedy_zostatok = max(0, pocet_otazok - _spocitaj_napovedy_testu(subor, kluc))
      if edit:
         vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/writetest.xsl', xdm_node=node, params={'admin': False, 'napovedy_zostatok': napovedy_zostatok}, xslt_pools=request.app.state.xslt_pools)
      else:
         vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/showtest.xsl', xdm_node=node, params={'admin': False, 'napovedy_zostatok': napovedy_zostatok}, xslt_pools=request.app.state.xslt_pools)
      return HTMLResponse(content=vysledok, status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba view: {e}')
      raise HTTPException(status_code=400, detail=str(e))

@app.get('/admin/{kluc}', response_class=HTMLResponse)
async def adminview(request: Request, X_Remote_User: StringHeader, kluc: StringPath, edit: BoolQuery = False):
   proc = request.app.state.proc
   node = find_test(proc, kluc, True, cache=request.app.state.kluc_cache)
   if node is None: #ked nenajdem test prisluchajuci danemu klucu
      return request.app.state.templates.TemplateResponse('index.html', {'request': request, 'detail': 'missingTest'}, status_code=404)
   try:
      xp = proc.new_xpath_processor()
      xp.set_context(xdm_item=node)
      pocet_otazok = int(xp.evaluate_single('count(otazka)') or 0)
      predmet, trieda, skupina, kapitola, fileid = get_test_metadata(proc, node)
      subor = f'./res/xml/feedback/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}_{fileid}.xml'
      napovedy_zostatok = max(0, pocet_otazok - _spocitaj_napovedy_testu(subor, kluc))
      if edit:
         vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/writetest.xsl', xdm_node=node, params={'admin': True, 'napovedy_zostatok': napovedy_zostatok}, xslt_pools=request.app.state.xslt_pools)
      else:
         vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/showtest.xsl', xdm_node=node, params={'admin': True, 'napovedy_zostatok': napovedy_zostatok}, xslt_pools=request.app.state.xslt_pools)
      return HTMLResponse(content=vysledok, status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba adminview: {e}')
      raise HTTPException(status_code=400, detail=str(e))
