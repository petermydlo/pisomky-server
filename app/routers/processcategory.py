# -*- coding: utf-8 -*-

from app.mytypes import StringForm, StringFormOptional
from app.utils import add_category, delete_category, update_category
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.post('/admin/process_category', response_class=JSONResponse)
async def process_category(request: Request, predmet: StringForm, kategoria_id: StringForm, operacia: StringForm, kapitola_id: StringFormOptional = None, za_kategoria_id: StringFormOptional = None, pocet: StringFormOptional = None, body: StringFormOptional = None, static: StringFormOptional = None, bonus: StringFormOptional = None):
   try:
      if operacia == 'create':
         if not kapitola_id:
            raise HTTPException(status_code=400, detail='kapitola_id je povinné pre vytvor')
         data = {k: v for k, v in {'pocet': pocet, 'body': body, 'static': static, 'bonus': bonus}.items() if v is not None}
         nova_id, ok = add_category(kapitola_id, data, za_kategoria_id=za_kategoria_id, predmet=predmet)
         if not ok:
            raise HTTPException(status_code=400, detail='Kategória sa nedala vytvoriť')
         return JSONResponse(content={'id': nova_id}, status_code=200)
      elif operacia == 'update':
         data = {'pocet': pocet, 'body': body, 'static': static, 'bonus': bonus}
         ok = update_category(kategoria_id, data)
         if not ok:
            raise HTTPException(status_code=400, detail='Kategória sa nedala upraviť')
         return JSONResponse(content={'ok': True}, status_code=200)
      elif operacia == 'delete':
         ok = delete_category(kategoria_id)
         if not ok:
            raise HTTPException(status_code=400, detail='Kategória sa nedala vymazať')
         return JSONResponse(content={'ok': True}, status_code=200)
      else:
         raise HTTPException(status_code=400, detail=f'Neznáma operácia: {operacia}')
   except HTTPException:
      raise
   except Exception as e:
      request.app.state.logger.error(f'chyba kategoria: {e}')
      raise HTTPException(status_code=400, detail=str(e))
