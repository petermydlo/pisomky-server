# -*- coding: utf-8 -*-

from app.mytypes import StringForm, StringHeader
from app.utils import xslt_to_string, xquery_to_string
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.post('/admin/groupstatistics', response_class=HTMLResponse)
async def groupstatistics(request: Request, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = '', X_Remote_User: StringHeader = ''):
   proc = request.app.state.proc
   try:
      params = {
         'predmet': predmet,
         'trieda': trieda,
         'skupina': skupina,
         'kapitola': kapitola,
         'fileid': fileid,
         'autor': X_Remote_User
      }
      xml_data = xquery_to_string(proc, './res/xquery/groupstatistics.xq', params=params)
      xml_node = proc.parse_xml(xml_text=xml_data)
      vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/groupstatistics.xsl', xdm_node=xml_node, xslt_pools=request.app.state.xslt_pools)
      return HTMLResponse(content=vysledok, status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba groupstatistics: {e}')
      raise HTTPException(status_code=400, detail=str(e))
