# -*- coding: utf-8 -*-

import secrets
from app.utils import ensure_ids, test_xml_path
from fastapi import APIRouter, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse
from app.mytypes import StringForm

router = APIRouter()

@router.post('/admin/regeneratetests', response_class=RedirectResponse)
async def regeneratetests(request: Request, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = ''): #, X_Remote_User: StringHeader):
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
