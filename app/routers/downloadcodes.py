# -*- coding: utf-8 -*-

import os
from app.utils import xslt_to_pdf
from app.mytypes import StringForm
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.post('/admin/downloadcodes', response_class=FileResponse)
async def downloadcodes(request: Request, background_tasks: BackgroundTasks, predmet: StringForm, trieda: StringForm, kapitola: StringForm, skupina: StringForm = ''):
   adresar = f'./res/xml/tests/{predmet}'
   cesta = f'{adresar}/{predmet}_{trieda}{skupina}_{kapitola}.xml'
   if not os.path.exists(cesta):
      raise HTTPException(status_code=404, detail='Súbor nenájdený!')
   try:
      nazov = f'{predmet}_{trieda}{skupina}_{kapitola}_codes.pdf'
      proc = request.app.state.proc
      pdffile = xslt_to_pdf(proc, stylesheet='./res/xslt/downloadcodes.xsl', source_file=cesta)
      background_tasks.add_task(os.remove, pdffile.name)
      return FileResponse(path=pdffile.name, headers={'Content-Disposition': f'attachment; filename="{nazov}"'}, media_type='application/pdf', filename=nazov)
   except Exception as e:
      request.app.state.logger.error(f'chyba downloadcodes: {e}')
      raise HTTPException(status_code=400, detail=str(e))
