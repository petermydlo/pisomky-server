# -*- coding: utf-8 -*-

import secrets
from pathlib import Path
from app.utils import ensure_ids, test_xml_path
from fastapi import APIRouter, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse
from app.mytypes import StringForm, StringListForm, StringHeader, BoolForm

router = APIRouter()

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
         return RedirectResponse(url="/admin#" + predmet, status_code=302)
      except Exception as e:
         request.app.state.logger.error(f'chyba createtests1: {e}')
         raise HTTPException(status_code=400, detail=str(e))
   except Exception as e:
      request.app.state.logger.error(f'chyba createtests2: {e}')
      raise HTTPException(status_code=400, detail='chyba createtests2: ' + str(e))
