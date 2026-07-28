# -*- coding: utf-8 -*-

import glob
import json
import os
import tempfile
import lxml.etree as ET
from app.mytypes import StringForm, StringFormOptional, StringHeader, StringQuery
from app.utils import (
   xslt_to_string, xquery_to_string, ensure_ids, is_used,
   add_category, delete_category, update_category, restore_category, find_category,
   add_question, update_question, delete_question, restore_question, fork_question, find_question,
   zmenene_zamrznute_polia,
   delete_chapter, create_chapter, update_chapter,
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
   tmp_path = None
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
      if tmp_path is not None and os.path.exists(tmp_path):
         os.remove(tmp_path)

@router.post('/admin/process_chapter', response_class=JSONResponse)
async def process_chapter(request: Request, predmet: StringForm, kapitola_id: StringForm, operacia: StringForm, nazov: StringFormOptional = None):
   try:
      if operacia == 'create':
         nova_id, ok = create_chapter(predmet, kapitola_id, nazov)
         if not ok:
            raise HTTPException(status_code=400, detail='Kapitola sa nedala vytvoriť')
         return JSONResponse(content={'id': nova_id}, status_code=200)
      elif operacia == 'update':
         ok = update_chapter(kapitola_id, predmet, nazov)
         if not ok:
            raise HTTPException(status_code=400, detail='Kapitola sa nedala upraviť')
         return JSONResponse(content={'ok': True}, status_code=200)
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
async def process_category(request: Request, predmet: StringForm, operacia: StringForm, kategoria_id: StringFormOptional = None, kapitola_id: StringFormOptional = None, za_kategoria_id: StringFormOptional = None, pocet: StringFormOptional = None, body: StringFormOptional = None, static: StringFormOptional = None, bonus: StringFormOptional = None, nazov: StringFormOptional = None):
   try:
      body = body or None
      static = static or None
      bonus = bonus or None
      nazov = nazov or None
      if operacia == 'create':
         if not kapitola_id:
            raise HTTPException(status_code=400, detail='kapitola_id je povinné pre vytvor')
         data = {k: v for k, v in {'pocet': pocet, 'body': body, 'static': static, 'bonus': bonus, 'nazov': nazov}.items() if v is not None}
         nova_id, ok = add_category(kapitola_id, data, za_kategoria_id=za_kategoria_id, predmet=predmet)
         if not ok:
            raise HTTPException(status_code=400, detail='Kategória sa nedala vytvoriť')
         return JSONResponse(content={'id': nova_id}, status_code=200)
      if not kategoria_id:
         raise HTTPException(status_code=400, detail='kategoria_id je povinné pre túto operáciu')
      if operacia == 'update':
         update_data: dict[str, str | None] = {'pocet': pocet, 'body': body, 'static': static, 'bonus': bonus, 'nazov': nazov}
         ok = update_category(kategoria_id, update_data)
         if not ok:
            raise HTTPException(status_code=400, detail='Kategória sa nedala upraviť')
         return JSONResponse(content={'ok': True}, status_code=200)
      elif operacia == 'delete':
         ok = delete_category(kategoria_id)
         if not ok:
            raise HTTPException(status_code=400, detail='Kategória sa nedala vymazať')
         return JSONResponse(content={'ok': True}, status_code=200)
      elif operacia == 'restore':
         ok = restore_category(kategoria_id)
         if not ok:
            raise HTTPException(status_code=400, detail='Kategória sa nedala obnoviť')
         return JSONResponse(content={'ok': True}, status_code=200)
      else:
         raise HTTPException(status_code=400, detail=f'Neznáma operácia: {operacia}')
   except HTTPException:
      raise
   except Exception as e:
      request.app.state.logger.error(f'chyba kategoria: {e}')
      raise HTTPException(status_code=400, detail=str(e))

@router.get('/admin/category', response_class=JSONResponse)
async def get_category(id: StringQuery):
   kategoria, _ = find_category(id)
   if kategoria is None:
      raise HTTPException(status_code=404, detail='Kategória nenájdená')
   return JSONResponse(content={
      'pocet': kategoria.get('pocet'),
      'body': kategoria.get('body'),
      'static': kategoria.get('static'),
      'bonus': kategoria.get('bonus'),
      'nazov': kategoria.get('nazov'),
   }, status_code=200)

@router.post('/admin/process_question', response_class=JSONResponse)
async def process_question(request: Request, operacia: StringForm, otazka_id: StringFormOptional = None, kategoria_id: StringFormOptional = None, za_otazka_id: StringFormOptional = None, znenie: StringFormOptional = None, body: StringFormOptional = None, static: StringFormOptional = None, bonus: StringFormOptional = None, nazov: StringFormOptional = None, odpovede: StringFormOptional = None, napovede: StringFormOptional = None, vzor: StringFormOptional = None, klucove_slova: StringFormOptional = None):
   try:
      body = body or None
      static = static or None
      bonus = bonus or None
      nazov = nazov or None
      odpovede_list = json.loads(odpovede) if odpovede else []
      napovede_list = json.loads(napovede) if napovede else []
      klucove_slova_list = json.loads(klucove_slova) if klucove_slova else []
      if operacia == 'create':
         if not kategoria_id:
            raise HTTPException(status_code=400, detail='kategoria_id je povinné pre vytvor')
         data = {k: v for k, v in {'znenie': znenie, 'body': body, 'static': static, 'bonus': bonus, 'nazov': nazov, 'vzor': vzor, 'klucove_slova': klucove_slova_list}.items() if v is not None}
         data['odpovede'] = odpovede_list
         data['napovede'] = napovede_list
         nova_id, ok = add_question(kategoria_id, data, za_otazka_id=za_otazka_id)
         if not ok:
            raise HTTPException(status_code=400, detail='Otázka sa nedala vytvoriť')
         return JSONResponse(content={'id': nova_id}, status_code=200)
      if not otazka_id:
         raise HTTPException(status_code=400, detail='otazka_id je povinné pre túto operáciu')
      if operacia == 'update':
         data = {'znenie': znenie, 'body': body, 'static': static, 'bonus': bonus, 'nazov': nazov, 'odpovede': odpovede_list, 'napovede': napovede_list, 'vzor': vzor, 'klucove_slova': klucove_slova_list}
         otazka_el, _ = find_question(otazka_id)
         if otazka_el is None:
            raise HTTPException(status_code=400, detail='Otázka sa nedala upraviť')
         if is_used(otazka_id) and zmenene_zamrznute_polia(otazka_el, data):
            nova_id = fork_question(otazka_id, data)
            if nova_id is None:
               raise HTTPException(status_code=400, detail='Otázka sa nedala upraviť')
            return JSONResponse(content={'id': nova_id, 'forked': True}, status_code=200)
         ok = update_question(otazka_id, data)
         if not ok:
            raise HTTPException(status_code=400, detail='Otázka sa nedala upraviť')
         return JSONResponse(content={'id': otazka_id, 'forked': False}, status_code=200)
      elif operacia == 'delete':
         ok = delete_question(otazka_id)
         if not ok:
            raise HTTPException(status_code=400, detail='Otázka sa nedala vymazať')
         return JSONResponse(content={'ok': True}, status_code=200)
      elif operacia == 'restore':
         ok = restore_question(otazka_id)
         if not ok:
            raise HTTPException(status_code=400, detail='Otázka sa nedala obnoviť')
         return JSONResponse(content={'ok': True}, status_code=200)
      else:
         raise HTTPException(status_code=400, detail=f'Neznáma operácia: {operacia}')
   except HTTPException:
      raise
   except Exception as e:
      request.app.state.logger.error(f'chyba otazka: {e}')
      raise HTTPException(status_code=400, detail=str(e))

def _serializuj_znenie(otazka_el) -> str | None:
   znenie = otazka_el.find('znenie')
   return ET.tostring(znenie, encoding='unicode', with_tail=False) if znenie is not None else None

def _obsah_odpovede(odp_el) -> str:
   casti = [odp_el.text or '']
   for dieta in odp_el:
      casti.append(ET.tostring(dieta, encoding='unicode'))
   return ''.join(casti)

@router.get('/admin/question', response_class=JSONResponse)
async def get_question(id: StringQuery):
   otazka, _ = find_question(id)
   if otazka is None:
      raise HTTPException(status_code=404, detail='Otázka nenájdená')
   odpovede = []
   for odp in otazka.findall('odpoved'):
      kluc = odp.get('napoveda_key')
      napovedy = [n.text or '' for n in otazka.findall('napoveda') if kluc and n.get('pre') == kluc]
      odpovede.append({'text': _obsah_odpovede(odp), 'spravna': odp.get('spravna') or '0', 'napovedy': napovedy})
   napovede = [n.text or '' for n in otazka.findall('napoveda') if 'pre' not in n.attrib]
   vzor_el = otazka.find('vzor')
   klucove_slova = [s.text or '' for s in otazka.findall('klucove_slova/slovo')]
   return JSONResponse(content={
      'znenie': _serializuj_znenie(otazka),
      'odpovede': odpovede,
      'napovede': napovede,
      'vzor': vzor_el.text if vzor_el is not None else None,
      'klucove_slova': klucove_slova,
      'body': otazka.get('body'),
      'static': otazka.get('static'),
      'bonus': otazka.get('bonus'),
      'nazov': otazka.get('nazov'),
   }, status_code=200)

@router.get('/admin/is_used', response_class=JSONResponse)
async def get_is_used(id: StringQuery, typ: StringQuery):
   if typ == 'kategoria':
      kategoria, _ = find_category(id)
      if kategoria is None:
         raise HTTPException(status_code=404, detail='Kategória nenájdená')
      pouzita = any(is_used(o.get('id') or '') for o in kategoria.findall('.//otazka[@id]'))
   elif typ == 'otazka':
      pouzita = is_used(id)
   else:
      raise HTTPException(status_code=400, detail=f'Neznámy typ: {typ}')
   return JSONResponse(content={'used': pouzita}, status_code=200)
