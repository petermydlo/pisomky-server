# -*- coding: utf-8 -*-

import os
from app.mytypes import StringForm
from app.utils import test_xml_path
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.delete('/admin/deletetests', response_class=PlainTextResponse)
async def delete(request: Request, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = ''):
   adresar = f'./res/xml/tests/{predmet}'
   cesta = test_xml_path(predmet, trieda, skupina, kapitola, fileid)
   if not os.path.exists(cesta):
      raise HTTPException(status_code=404, detail='Súbor nenájdený!')
   try:
      os.remove(cesta)
      if os.listdir(adresar):
         return PlainTextResponse(content="#" + predmet, status_code=200)
      else:
         return PlainTextResponse(content="", status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba deletetests: {e}')
      raise HTTPException(status_code=400, detail='chyba deletetests: ' + str(e))
