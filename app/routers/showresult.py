# -*- coding: utf-8 -*-

from app.utils import find_test, xslt_to_string
from app.mytypes import StringPath
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.get('/admin/showresult/{kluc}', response_class=HTMLResponse)
async def showresult(request: Request, kluc: StringPath):
   proc = request.app.state.proc
   node = find_test(proc, kluc, True, cache=request.app.state.kluc_cache)
   if node is None: #ked nenajdem test prisluchajuci danemu klucu
      return request.app.state.templates.TemplateResponse('index.html', {'request': request, 'detail': 'missingTest'}, status_code=404)
   try:
      vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/showresult.xsl', xdm_node=node, xslt_pools=request.app.state.xslt_pools)
      return HTMLResponse(content=vysledok, status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba showresult: {e}')
      raise HTTPException(status_code=400, detail=str(e))
