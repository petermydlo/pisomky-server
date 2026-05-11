# -*- coding: utf-8 -*-

import os
import shutil
import tempfile
import qrcode
import qrcode.image.svg
import lxml.etree as ET
from fastapi.concurrency import run_in_threadpool
from app.utils import xslt_to_pdf, find_test, test_xml_path
from app.mytypes import StringForm, StringPath
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.get('/admin/downloadresult/{kluc}', response_class=FileResponse)
async def downloadresult(request: Request, background_tasks: BackgroundTasks, kluc: StringPath):
   proc = request.app.state.proc
   node = find_test(proc, kluc, admin=True, cache=request.app.state.kluc_cache)
   if node is None:
      return request.app.state.templates.TemplateResponse('index.html', {'request': request, 'detail': 'missingTest'}, status_code=404)
   try:
      pdffile = xslt_to_pdf(proc, stylesheet='./res/xslt/downloadresult.xsl', xdm_node=node.get_parent(), params={'kluc': kluc}, xslt_pools=request.app.state.xslt_pools)
      background_tasks.add_task(os.remove, pdffile.name)
      return FileResponse(path=pdffile.name, media_type='application/pdf', filename=kluc + '_result.pdf')
   except Exception as e:
      request.app.state.logger.error(f'chyba downloadresult: {e}')
      raise HTTPException(status_code=400, detail=str(e))

def _generuj_qr_kody(cesta: str) -> str:
   tree = ET.parse(cesta)
   qrdir = tempfile.mkdtemp()
   for test_id in tree.xpath('//test/@id'):  # type: ignore[union-attr]
      qr = qrcode.QRCode(
         error_correction=qrcode.constants.ERROR_CORRECT_L,
         box_size=3,
         border=1,
         image_factory=qrcode.image.svg.SvgPathImage,
      )
      qr.add_data(test_id)
      qr.make(fit=True)
      img = qr.make_image()
      img.save(f'{qrdir}/{test_id}.svg')  # type: ignore[str-bytes-safe]
   return qrdir

@router.post('/admin/downloadtests', response_class=FileResponse)
async def downloadtests(request: Request, background_tasks: BackgroundTasks, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = ''):
   cesta = test_xml_path(predmet, trieda, skupina, kapitola, fileid)
   if not os.path.exists(cesta):
      raise HTTPException(status_code=404, detail='Súbor nenájdený!')
   try:
      nazov = f'{predmet}_{trieda}{skupina}_{kapitola}{"_" + fileid if fileid else ""}_tests.pdf'
      proc = request.app.state.proc
      qrdir = await run_in_threadpool(_generuj_qr_kody, cesta)
      background_tasks.add_task(shutil.rmtree, qrdir, ignore_errors=True)
      pdffile = xslt_to_pdf(proc, stylesheet='./res/xslt/downloadtests.xsl', source_file=cesta, params={'qrdir': f'file://{qrdir}'}, xslt_pools=request.app.state.xslt_pools)
      background_tasks.add_task(os.remove, pdffile.name)
      return FileResponse(path=pdffile.name, headers={'Content-Disposition': f'attachment; filename="{nazov}"'}, media_type='application/pdf', filename=nazov)
   except Exception as e:
      request.app.state.logger.error(f'chyba downloadtests: {e}')
      raise HTTPException(status_code=400, detail=str(e))

@router.post('/admin/downloadresults', response_class=FileResponse)
async def downloadresults(request: Request, background_tasks: BackgroundTasks, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = ''):
   cesta = test_xml_path(predmet, trieda, skupina, kapitola, fileid)
   if not os.path.exists(cesta):
      raise HTTPException(status_code=404, detail='Súbor nenájdený!')
   try:
      nazov = f'{predmet}_{trieda}{skupina}_{kapitola}{"_" + fileid if fileid else ""}_results.pdf'
      proc = request.app.state.proc
      pdffile = xslt_to_pdf(proc, stylesheet='./res/xslt/downloadresult.xsl', source_file=cesta, xslt_pools=request.app.state.xslt_pools)
      background_tasks.add_task(os.remove, pdffile.name)
      return FileResponse(path=pdffile.name, headers={'Content-Disposition': f'attachment; filename="{nazov}"'}, media_type='application/pdf', filename=nazov)
   except Exception as e:
      request.app.state.logger.error(f'chyba downloadresults: {e}')
      raise HTTPException(status_code=400, detail=str(e))

@router.post('/admin/downloadcodes', response_class=FileResponse)
async def downloadcodes(request: Request, background_tasks: BackgroundTasks, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = ''):
   cesta = test_xml_path(predmet, trieda, skupina, kapitola, fileid)
   if not os.path.exists(cesta):
      raise HTTPException(status_code=404, detail='Súbor nenájdený!')
   try:
      nazov = f'{predmet}_{trieda}{skupina}_{kapitola}{"_" + fileid if fileid else ""}_codes.pdf'
      proc = request.app.state.proc
      pdffile = xslt_to_pdf(proc, stylesheet='./res/xslt/downloadcodes.xsl', source_file=cesta)
      background_tasks.add_task(os.remove, pdffile.name)
      return FileResponse(path=pdffile.name, headers={'Content-Disposition': f'attachment; filename="{nazov}"'}, media_type='application/pdf', filename=nazov)
   except Exception as e:
      request.app.state.logger.error(f'chyba downloadcodes: {e}')
      raise HTTPException(status_code=400, detail=str(e))
