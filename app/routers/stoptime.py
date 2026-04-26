# -*- coding: utf-8 -*-

from app.utils import modify_test_xml, find_test_file
from app.mytypes import StringPath, StringForm
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.post('/stoptime/{kluc}', response_class=HTMLResponse)
async def stoptime(request: Request, kluc: StringPath, stop: StringForm):
   def _modify(tree):
      tests = [t for t in tree.findall('.//test') if t.get('id') == kluc]
      if not tests:
         raise HTTPException(status_code=404, detail="Test nenájdený")
      tests[0].set('stop', stop)

   try:
      cesta = find_test_file(kluc, request.app.state.kluc_cache)
      if not cesta:
         raise HTTPException(status_code=404, detail='Test nenájdený')
      modify_test_xml(cesta, _modify)
      return HTMLResponse(content='ok', status_code=204)
   except HTTPException:
      raise
   except Exception as e:
      raise HTTPException(status_code=400, detail='chyba stoptime: ' + str(e))
