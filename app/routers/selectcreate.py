# -*- coding: utf-8 -*-

import os
from app.utils import xslt_to_string
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
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
