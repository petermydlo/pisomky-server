# -*- coding: utf-8 -*-

from app.mytypes import StringForm
from app.utils import update_category, update_question
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.post('/admin/setpaused', response_class=JSONResponse)
async def set_paused(request: Request, id: StringForm, typ: StringForm, paused: StringForm):
   try:
      hodnota = '1' if paused == '1' else None
      if typ == 'kategoria':
         ok = update_category(id, {'paused': hodnota})
      elif typ == 'otazka':
         ok = update_question(id, {'paused': hodnota})
      else:
         raise HTTPException(status_code=400, detail=f'Neznámy typ: {typ}')
      if not ok:
         raise HTTPException(status_code=404, detail='Nenájdené')
      return JSONResponse(content={'ok': True}, status_code=200)
   except HTTPException:
      raise
   except Exception as e:
      request.app.state.logger.error(f'chyba setpaused: {e}')
      raise HTTPException(status_code=400, detail=str(e))
