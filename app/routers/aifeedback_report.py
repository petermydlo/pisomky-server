# -*- coding: utf-8 -*-

import os
import lxml.etree as ET
from app.utils import xquery_to_string, xslt_to_string
from app.mytypes import StringForm
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.post('/admin/feedbackreport', response_class=HTMLResponse)
async def feedbackreport(request: Request, predmet: StringForm, trieda: StringForm, kapitola: StringForm, skupina: StringForm = ''):
   proc = request.app.state.proc
   try:
      params = {
         'predmet': predmet,
         'trieda': trieda,
         'skupina': skupina,
         'kapitola': kapitola
      }
      subor = f'./res/xml/feedback/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}.xml'
      if not os.path.exists(subor):
         xml_data = ET.tostring(ET.Element('feedback', attrib={'predmet': predmet, 'trieda': trieda, 'skupina': skupina, 'kapitola': kapitola}), encoding='unicode')
      else:
         xml_data = xquery_to_string(proc, './res/xquery/feedback.xq', params=params)
      xml_node = proc.parse_xml(xml_text=xml_data)
      vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/feedbackreport.xsl', xdm_node=xml_node, xslt_pools=request.app.state.xslt_pools)
      return HTMLResponse(content=vysledok, status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba feedbackreport: {e}')
      raise HTTPException(status_code=400, detail=str(e))
