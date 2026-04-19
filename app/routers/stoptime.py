# -*- coding: utf-8 -*-

from app.utils import modify_test_xml
from app.mytypes import StringForm, StringPath
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.post('/stoptime/{kluc}', response_class=HTMLResponse)
async def stoptime(request: Request, kluc: StringPath, predmet: StringForm, trieda: StringForm, kapitola: StringForm, stop: StringForm, skupina: StringForm = ''):
   def _modify(tree):
      safe_kluc = kluc.replace("'", "")
      try:
         test = tree.xpath(f"//test[@id='{safe_kluc}']")[0]
      except IndexError:
         raise HTTPException(status_code=404, detail="Test nenájdený")
      test.set('stop', stop)

   try:
      modify_test_xml(predmet, trieda, skupina, kapitola, _modify)
      return HTMLResponse(content='ok', status_code=204)
   except HTTPException:
      raise
   except Exception as e:
      raise HTTPException(status_code=400, detail='chyba stoptime: ' + str(e))
