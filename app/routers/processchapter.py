# -*- coding: utf-8 -*-

from app.mytypes import StringForm, StringFormOptional
from app.utils import delete_chapter, create_chapter
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.post('/admin/process_chapter', response_class=JSONResponse)
async def process_chapter(request: Request, predmet: StringForm, kapitola_id: StringForm, operacia: StringForm, nazov: StringFormOptional = None):
   try:
      if operacia == 'create':
         nova_id, ok = create_chapter(predmet, kapitola_id, nazov)
         if not ok:
            raise HTTPException(status_code=400, detail='Kapitola sa nedala vytvoriť')
         return JSONResponse(content={'id': nova_id}, status_code=200)
      elif operacia == 'delete':
         ok = delete_chapter(kapitola_id, predmet)
         if not ok:
            raise HTTPException(status_code=400, detail='Kapitola sa nedala vymazať')
         return JSONResponse(content={'ok': True}, status_code=200)
      else:
         raise HTTPException(status_code=400, detail=f'Neznáma operácia: {operacia}')
   except HTTPException:
      raise
   except Exception as e:
      request.app.state.logger.error(f'chyba kapitola: {e}')
      raise HTTPException(status_code=400, detail=str(e))
