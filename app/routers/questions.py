# -*- coding: utf-8 -*-

import glob
import json
import os
import tempfile
from app.mytypes import StringForm, StringFormOptional, StringHeader
from app.utils import (
   xslt_to_string, xquery_to_string, ensure_ids,
   add_category, delete_category, update_category,
   add_question, update_question, delete_question,
   delete_chapter, create_chapter,
)
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import HTTPException

router = APIRouter()

@router.get('/admin/selectquestions', response_class=HTMLResponse)
async def selectquestions(request: Request):
   proc = request.app.state.proc
   predmety = ' '.join([name for name in os.listdir('./res/xml/questions')])
   try:
      vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/selectquestions.xsl', params={'predmety': predmety})
      return HTMLResponse(content=vysledok, status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba selectquestions: {e}')
      raise HTTPException(status_code=400, detail=str(e))

@router.post('/admin/showquestions', response_class=HTMLResponse)
async def showquestions(request: Request, predmet: StringForm, X_Remote_User: StringHeader):
   proc = request.app.state.proc
   try:
      for cesta in glob.iglob(f'./res/xml/questions/{predmet}/*.xml'):
         ensure_ids(cesta)
      xml_data = xquery_to_string(proc, './res/xquery/statistics.xq', params={'predmet': predmet, 'autor': X_Remote_User})
      with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
         f.write(xml_data)
         tmp_path = f.name
      vysledok = xslt_to_string(proc, stylesheet_file='./res/xslt/showquestions.xsl', params={'predmet': predmet, 'statistika': tmp_path}, xslt_pools=request.app.state.xslt_pools)
      return HTMLResponse(content=vysledok, status_code=200)
   except Exception as e:
      request.app.state.logger.error(f'chyba showquestions: {e}')
      raise HTTPException(status_code=400, detail=str(e))
   finally:
      if 'tmp_path' in locals() and os.path.exists(tmp_path):
         os.remove(tmp_path)

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
         update_data: dict[str, str | None] = {'pocet': pocet, 'body': body, 'static': static, 'bonus': bonus}
         ok = update_category(kategoria_id, update_data)
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
