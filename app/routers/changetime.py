# -*- coding: utf-8 -*-

from app.utils import modify_test_xml
from app.mytypes import StringForm, StringFormOptional
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.post('/admin/changetime', response_class=HTMLResponse)
async def changetime(request: Request, predmet: StringForm, trieda: StringForm, kapitola: StringForm, skupina: StringForm = '', start: StringFormOptional = None, stop: StringFormOptional = None, kluc: StringFormOptional = None):
   def _modify(tree):
      root = tree.getroot()

      def _set_attr(node, attr, value):
         if value is not None:
            if value.strip() != '':
               node.set(attr, value)
            else:
               node.attrib.pop(attr, None)

      if kluc is None:
         _set_attr(root, 'start', start)
         _set_attr(root, 'stop', stop)
      else:
         safe_kluc = kluc.replace("'", "")
         try:
            test = tree.xpath(f"//test[@id='{safe_kluc}']")[0]
         except IndexError:
            raise HTTPException(status_code=404, detail="Test nenájdený")
         _set_attr(test, 'start', start)
         _set_attr(test, 'stop', stop)
   try:
      modify_test_xml(predmet, trieda, skupina, kapitola, _modify)
      return HTMLResponse(content='ok', status_code=204)
   except HTTPException:
      raise
   except Exception as e:
      raise HTTPException(status_code=400, detail='chyba changetime: ' + str(e))
