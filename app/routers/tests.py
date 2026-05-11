# -*- coding: utf-8 -*-

import os
import secrets
from pathlib import Path
from app.utils import xslt_to_string, ensure_ids, test_xml_path
from app.mytypes import StringForm, StringListForm, StringHeader, BoolForm
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.get('/admin/selectcreate', response_class=HTMLResponse)
async def selectcreate(request: Request):
   proc = request.app.state.proc
   predmety = ' '.join([name for name in os.listdir('./res/xml/questions')])
   try:
      vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/selectcreate.xsl', params={'predmety': predmety})
      return HTMLResponse(content=vysledok, status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba selectcreate: {e}')
      raise HTTPException(status_code=400, detail=str(e))

@router.post('/admin/createtests', response_class=RedirectResponse)
async def createtests(request: Request, predmet: StringForm, trieda: StringListForm, kapitola: StringForm, X_Remote_User: StringHeader, skupina: StringForm = '', start: StringForm = '', stop: StringForm = '', anonymne: BoolForm = False, identita: BoolForm = False):
   try:
      proc = request.app.state.proc
      trieda_str = ','.join(trieda)
      skupina = '' if skupina == '-' else skupina
      xsltproc = proc.new_xslt30_processor()
      xsltproc.set_parameter('seed_ext', proc.make_string_value(secrets.token_hex(16)))
      xsltproc.set_parameter('predmet', proc.make_string_value(predmet))
      xsltproc.set_parameter('trieda', proc.make_string_value(trieda_str))
      xsltproc.set_parameter('skupina', proc.make_string_value(skupina))
      xsltproc.set_parameter('kapitola', proc.make_string_value(kapitola))
      xsltproc.set_parameter('start', proc.make_string_value(start))
      xsltproc.set_parameter('stop', proc.make_string_value(stop))
      xsltproc.set_parameter('anonymne', proc.make_boolean_value(anonymne))
      xsltproc.set_parameter('identita', proc.make_boolean_value(identita))
      xsltproc.set_parameter('autor', proc.make_string_value(X_Remote_User))
      try:
         fileid = secrets.token_hex(2)
         xsltproc.set_parameter('fileid', proc.make_string_value(fileid))
         Path(f'./res/xml/tests/{predmet}').mkdir(parents=True, exist_ok=True)
         ensure_ids(f'./res/xml/questions/{predmet}/{predmet}_{kapitola}.xml')
         executable = xsltproc.compile_stylesheet(stylesheet_file='./res/xslt/createtests.xsl')
         executable.set_output_file(test_xml_path(predmet, trieda_str, skupina, kapitola, fileid))
         executable.transform_to_file(source_file='./res/xml/lists/roster.xml')
         return RedirectResponse(url='/admin#' + predmet, status_code=302)
      except Exception as e:
         request.app.state.logger.error(f'chyba createtests1: {e}')
         raise HTTPException(status_code=400, detail=str(e))
   except Exception as e:
      request.app.state.logger.error(f'chyba createtests2: {e}')
      raise HTTPException(status_code=400, detail='chyba createtests2: ' + str(e))

@router.post('/admin/regeneratetests', response_class=RedirectResponse)
async def regeneratetests(request: Request, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = ''):
   try:
      proc = request.app.state.proc
      subor = test_xml_path(predmet, trieda, skupina, kapitola, fileid)
      xsltproc = proc.new_xslt30_processor()
      xsltproc.set_parameter('seed_ext', proc.make_string_value(secrets.token_hex(16)))
      xsltproc.set_parameter('fileid', proc.make_string_value(fileid))
      xsltproc.set_parameter('predmet', proc.make_string_value(predmet))
      xsltproc.set_parameter('kapitola', proc.make_string_value(kapitola))
      try:
         ensure_ids(f'./res/xml/questions/{predmet}/{predmet}_{kapitola}.xml')
         executable = xsltproc.compile_stylesheet(stylesheet_file='./res/xslt/createtests.xsl')
         executable.set_output_file(subor)
         executable.transform_to_file(source_file=subor)
         return RedirectResponse(url='/admin#' + predmet, status_code=302)
      except Exception as e:
         request.app.state.logger.error(f'chyba regeneratetests1: {e}')
         raise HTTPException(status_code=400, detail='chyba regenerates1: ' + str(e))
   except Exception as e:
      request.app.state.logger.error(f'chyba regeneratetests2: {e}')
      raise HTTPException(status_code=400, detail='chyba regeneratetests2: ' + str(e))

@router.delete('/admin/deletetests', response_class=PlainTextResponse)
async def delete(request: Request, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = '', del_test: BoolForm = True, del_answers: BoolForm = False, del_feedback: BoolForm = False):
   cesta_test = test_xml_path(predmet, trieda, skupina, kapitola, fileid)
   cesta_answers  = Path(cesta_test.replace('/tests/', '/answers/', 1))
   cesta_feedback = Path(cesta_test.replace('/tests/', '/feedback/', 1))
   if del_test and not os.path.exists(cesta_test):
      raise HTTPException(status_code=404, detail='Súbor nenájdený!')
   try:
      if del_test and os.path.exists(cesta_test):
         os.remove(cesta_test)
      if del_answers and cesta_answers.exists():
         cesta_answers.unlink()
      if del_feedback and cesta_feedback.exists():
         cesta_feedback.unlink()
      adresar = f'./res/xml/tests/{predmet}'
      if os.path.exists(adresar) and os.listdir(adresar):
         return PlainTextResponse(content='#' + predmet, status_code=200)
      else:
         return PlainTextResponse(content='', status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba deletetests: {e}')
      raise HTTPException(status_code=400, detail='chyba deletetests: ' + str(e))
