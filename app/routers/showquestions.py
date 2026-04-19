# -*- coding: utf-8 -*-

import os
import tempfile
from app.mytypes import StringForm, StringHeader
from app.utils import xslt_to_string, xquery_to_string, ensure_ids
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.post('/admin/showquestions', response_class=HTMLResponse)
async def showquestions(request: Request, predmet: StringForm, X_Remote_User: StringHeader):
   proc = request.app.state.proc
   try:
      import glob
      for cesta in glob.iglob(f'./res/xml/questions/{predmet}/*.xml'):
         ensure_ids(cesta)
      xml_data = xquery_to_string(proc, './res/xquery/statistics.xq', params={'predmet': predmet, 'autor': X_Remote_User})
      with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
         f.write(xml_data)
         tmp_path = f.name
      vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/showquestions.xsl', params={'predmet': predmet, 'statistika': tmp_path}, xslt_pools=request.app.state.xslt_pools)
      return HTMLResponse(content=vysledok, status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba showquestions: {e}')
      raise HTTPException(status_code=400, detail=str(e))
   finally:
      if 'tmp_path' in locals() and os.path.exists(tmp_path):
         os.remove(tmp_path)
