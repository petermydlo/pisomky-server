# -*- coding: utf-8 -*-

import json
from app.mytypes import StringForm, StringFormOptional
from app.utils import add_question, update_question, delete_question
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.post('/admin/process_question', response_class=JSONResponse)
async def process_question(request: Request, otazka_id: StringForm, operacia: StringForm, kategoria_id: StringFormOptional = None, za_otazka_id: StringFormOptional = None, znenie: StringFormOptional = None, body: StringFormOptional = None, static: StringFormOptional = None, bonus: StringFormOptional = None, odpovede: StringFormOptional = None, vzor: StringFormOptional = None, klucove_slova: StringFormOptional = None):
   try:
      odpovede_list = json.loads(odpovede) if odpovede else []
      klucove_slova_list = json.loads(klucove_slova) if klucove_slova else []
      if operacia == 'create':
         if not kategoria_id:
            raise HTTPException(status_code=400, detail='kategoria_id je povinné pre vytvor')
         data = {k: v for k, v in {'znenie': znenie, 'body': body, 'static': static, 'bonus': bonus, 'vzor': vzor, 'klucove_slova': klucove_slova_list}.items() if v is not None}
         data['odpovede'] = odpovede_list
         nova_id, ok = add_question(kategoria_id, data, za_otazka_id=za_otazka_id)
         if not ok:
            raise HTTPException(status_code=400, detail='Otázka sa nedala vytvoriť')
         return JSONResponse(content={'id': nova_id}, status_code=200)
      elif operacia == 'update':
         data = {'znenie': znenie, 'body': body, 'static': static, 'bonus': bonus, 'odpovede': odpovede_list, 'vzor': vzor, 'klucove_slova': klucove_slova_list}
         ok = update_question(otazka_id, data)
         if not ok:
            raise HTTPException(status_code=400, detail='Otázka sa nedala upraviť')
         return JSONResponse(content={'ok': True}, status_code=200)
      elif operacia == 'delete':
         ok = delete_question(otazka_id)
         if not ok:
            raise HTTPException(status_code=400, detail='Otázka sa nedala vymazať')
         return JSONResponse(content={'ok': True}, status_code=200)
      else:
         raise HTTPException(status_code=400, detail=f'Neznáma operácia: {operacia}')
   except HTTPException:
      raise
   except Exception as e:
      request.app.state.logger.error(f'chyba otazka: {e}')
      raise HTTPException(status_code=400, detail=str(e))
