# -*- coding: utf-8 -*-

import os
from app.utils import xslt_to_pdf, find_test
from app.mytypes import StringPath
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.get('/admin/downloadresult/{kluc}', response_class=FileResponse)
async def downloadresult(request: Request, background_tasks: BackgroundTasks, kluc: StringPath):
   proc = request.app.state.proc
   node = find_test(proc, kluc, admin=True, cache=request.app.state.kluc_cache)
   if node is None: #ked nenajdem test prisluchajuci danemu klucu
      return request.app.state.templates.TemplateResponse('index.html', {'request': request, 'detail': 'missingTest'}, status_code=404)
   try:
      pdffile = xslt_to_pdf(proc, stylesheet='./res/xslt/downloadresult.xsl', xdm_node=node.get_parent(), params={'kluc': kluc}, xslt_pools=request.app.state.xslt_pools)
      background_tasks.add_task(os.remove, pdffile.name)
      return FileResponse(path=pdffile.name, media_type='application/pdf', filename=kluc + '_result.pdf')
   except Exception as e:
      request.app.state.logger.error(f'chyba downloadresult: {e}')
      raise HTTPException(status_code=400, detail=str(e))
