# -*- coding: utf-8 -*-

import os
import shutil
import tempfile
import qrcode
import qrcode.image.svg
import lxml.etree as ET
from fastapi.concurrency import run_in_threadpool
from app.utils import xslt_to_pdf, find_test
from app.sada import SadaTestov
from app.mytypes import StringForm, StringPath, Proc, Logger, KlucCache, XsltPools, Templates
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.get('/admin/downloadresult/{kluc}', response_class=FileResponse)
async def downloadresult(request: Request, proc: Proc, logger: Logger, kluc_cache: KlucCache, xslt_pools: XsltPools, templates: Templates, background_tasks: BackgroundTasks, kluc: StringPath):
   node = find_test(proc, kluc, admin=True, cache=kluc_cache)
   if node is None:
      return templates.TemplateResponse(request, 'index.html', {'detail': 'missingTest'}, status_code=404)
   try:
      pdffile = await run_in_threadpool(xslt_to_pdf, proc, stylesheet='./res/xslt/downloadresult.xsl', xdm_node=node.get_parent(), params={'kluc': kluc}, xslt_pools=xslt_pools)
      background_tasks.add_task(os.remove, pdffile.name)
      return FileResponse(path=pdffile.name, headers={'Content-Disposition': f'attachment; filename="{kluc}_result.pdf"'}, media_type='application/pdf')
   except Exception as e:
      logger.error(f'chyba downloadresult: {e}')
      raise HTTPException(status_code=400, detail=str(e))

def _generuj_qr_kody(cesta: str) -> str:
   tree = ET.parse(cesta)
   qrdir = tempfile.mkdtemp()
   try:
      for test_id in tree.xpath('//test/@id'):  # type: ignore[union-attr]
         qr = qrcode.QRCode(
            error_correction=qrcode.ERROR_CORRECT_L,
            box_size=3,
            border=1,
            image_factory=qrcode.image.svg.SvgPathImage,
         )
         qr.add_data(test_id)
         qr.make(fit=True)
         img = qr.make_image()
         img.save(f'{qrdir}/{test_id}.svg')  # type: ignore[str-bytes-safe]
   except BaseException:
      shutil.rmtree(qrdir, ignore_errors=True)  #volajuci adresar nepozna, nikto ho inak neupracie
      raise
   return qrdir

@router.post('/admin/downloadtests', response_class=FileResponse)
async def downloadtests(proc: Proc, logger: Logger, xslt_pools: XsltPools, background_tasks: BackgroundTasks, sada: SadaTestov, vodoznak: StringForm = ''):
   predmet, trieda, skupina, kapitola, fileid = sada
   cesta = sada.cesta
   try:
      nazov = f'{predmet}_{trieda}{skupina}_{kapitola}{"_" + fileid if fileid else ""}_tests.pdf'
      qrdir = await run_in_threadpool(_generuj_qr_kody, cesta)
      try:
         pdffile = await run_in_threadpool(xslt_to_pdf, proc, stylesheet='./res/xslt/downloadtests.xsl', source_file=cesta, params={'qrdir': f'file://{qrdir}', 'vodoznak': vodoznak == '1'}, xslt_pools=xslt_pools)
      except BaseException:
         shutil.rmtree(qrdir, ignore_errors=True)  #background_tasks sa pri vyhodenej vynimke nespustia
         raise
      background_tasks.add_task(shutil.rmtree, qrdir, ignore_errors=True)
      background_tasks.add_task(os.remove, pdffile.name)
      return FileResponse(path=pdffile.name, headers={'Content-Disposition': f'attachment; filename="{nazov}"'}, media_type='application/pdf', filename=nazov)
   except Exception as e:
      logger.error(f'chyba downloadtests: {e}')
      raise HTTPException(status_code=400, detail=str(e))

@router.post('/admin/downloadresults', response_class=FileResponse)
async def downloadresults(proc: Proc, logger: Logger, xslt_pools: XsltPools, background_tasks: BackgroundTasks, sada: SadaTestov):
   predmet, trieda, skupina, kapitola, fileid = sada
   cesta = sada.cesta
   try:
      nazov = f'{predmet}_{trieda}{skupina}_{kapitola}{"_" + fileid if fileid else ""}_results.pdf'
      pdffile = await run_in_threadpool(xslt_to_pdf, proc, stylesheet='./res/xslt/downloadresult.xsl', source_file=cesta, xslt_pools=xslt_pools)
      background_tasks.add_task(os.remove, pdffile.name)
      return FileResponse(path=pdffile.name, headers={'Content-Disposition': f'attachment; filename="{nazov}"'}, media_type='application/pdf', filename=nazov)
   except Exception as e:
      logger.error(f'chyba downloadresults: {e}')
      raise HTTPException(status_code=400, detail=str(e))

@router.post('/admin/downloadcodes', response_class=FileResponse)
async def downloadcodes(proc: Proc, logger: Logger, xslt_pools: XsltPools, background_tasks: BackgroundTasks, sada: SadaTestov):
   predmet, trieda, skupina, kapitola, fileid = sada
   cesta = sada.cesta
   try:
      nazov = f'{predmet}_{trieda}{skupina}_{kapitola}{"_" + fileid if fileid else ""}_codes.pdf'
      pdffile = await run_in_threadpool(xslt_to_pdf, proc, stylesheet='./res/xslt/downloadcodes.xsl', source_file=cesta, xslt_pools=xslt_pools)
      background_tasks.add_task(os.remove, pdffile.name)
      return FileResponse(path=pdffile.name, headers={'Content-Disposition': f'attachment; filename="{nazov}"'}, media_type='application/pdf', filename=nazov)
   except Exception as e:
      logger.error(f'chyba downloadcodes: {e}')
      raise HTTPException(status_code=400, detail=str(e))
