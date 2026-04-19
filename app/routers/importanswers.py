# -*- coding: utf-8 -*-

import lxml.etree as ET
from pathlib import Path
from filelock import FileLock
from datetime import datetime
from dotenv import load_dotenv
import anyio
from fastapi import APIRouter, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.concurrency import run_in_threadpool
from app.mytypes import StringForm, StringPath
from app.utils import find_test_file

load_dotenv()

router = APIRouter()

def write_answers_import(lock, cesta, form_data, kluc):
   with lock:
      if not Path(cesta).is_file():
         with open(cesta, 'w') as sub:
            sub.write('<?xml version="1.1" encoding="UTF-8"?>\n')
            sub.write('<odpovede xml:lang="sk">')
            sub.write('</odpovede>')
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(str(cesta), xmlParser)
      root = tree.getroot()
      dat = datetime.now().isoformat(timespec='seconds')
      testxml = next(iter(root.xpath("test[@id=$id]", id=kluc)), None)
      if testxml is None:
         testxml = ET.SubElement(root, 'test', attrib={'id': kluc, 'dat': dat})
      else:
         testxml.set('dat', dat)
      for key, value in form_data.items():
         otazka = next(iter(testxml.xpath("otazka[@id=$id]", id=key)), None)
         if otazka is not None:
            otazka.text = value
         else:
            otazkaxml = ET.SubElement(testxml, 'otazka', attrib={'id': key})
            otazkaxml.text = value
      ET.indent(tree, space='   ')
      tree.write(str(cesta), encoding='utf-8', xml_declaration=True, pretty_print=True)

def nacitaj_tests_xml(cesta, test_id):
   """Nacita obsah tests XML suboru ako string."""
   tree = ET.parse(cesta)
   test = next(iter(tree.xpath(".//test[@id=$id]", id=test_id)), None)
   if test is not None:
      return ET.tostring(test, encoding='unicode')
   return ''

def ziskaj_metadata(cesta):
   tree = ET.parse(cesta)
   root = tree.getroot()
   return root.get('predmet', ''), root.get('trieda', ''), root.get('skupina', ''), root.get('kapitola', '')


def precitaj_qr_kody(obsah: bytes, mime_type: str) -> list[str]:
   """Prečíta QR kódy z obrázka alebo PDF bez AI. Vráti list nájdených textov."""
   import io
   import zxingcpp
   from PIL import Image

   imgs = []
   if mime_type == 'application/pdf':
      import fitz
      doc = fitz.open(stream=obsah, filetype='pdf')
      for page in doc:
         pix = page.get_pixmap(dpi=150)
         imgs.append(Image.frombytes('RGB', [pix.width, pix.height], pix.samples))
      doc.close()
   else:
      imgs.append(Image.open(io.BytesIO(obsah)))

   ids = []
   for img in imgs:
      for r in zxingcpp.read_barcodes(img):
         if r.valid and r.text and r.text not in ids:
            ids.append(r.text)
   return ids


@router.get('/admin/ai/importanswers', response_class=HTMLResponse)
async def importanswers_page(request: Request):
   return request.app.state.templates.TemplateResponse('importanswers.html', {'request': request})


@router.post('/admin/ai/importmanual/{kluc}')
async def importmanual(request: Request, kluc: StringPath, predmet: StringForm, trieda: StringForm, kapitola: StringForm, skupina: StringForm = ''):
   adresar = f'./res/xml/answers/{predmet}'
   Path(adresar).mkdir(parents=True, exist_ok=True)
   cesta = Path(f'{adresar}/{predmet}_{trieda}{skupina}_{kapitola}.xml')
   lock = FileLock(f'{cesta}.lock')
   async with request.form() as form:
      form_data = {k: v for k, v in form.items() if k not in {'predmet', 'trieda', 'skupina', 'kapitola'}}
   try:
      await run_in_threadpool(write_answers_import, lock, cesta, form_data,  kluc)
   except Exception as e:
      request.app.state.logger.error(f'chyba importmanual: {e}')
      raise HTTPException(status_code=400, detail=str(e))
   return JSONResponse(content={'ok': True})


async def _spracuj_subor(subor, cache, provider, vysledky):
   """Spracuje jeden nahraný súbor — QR/AI identifikácia + extrakcia odpovedí + zápis."""
   obsah = await subor.read()
   mime_type = subor.content_type or 'application/pdf'

   # 1. KROK: Identifikácia ID testov — najprv QR, potom AI ako fallback
   try:
      najdene_ids = await run_in_threadpool(precitaj_qr_kody, obsah, mime_type)
   except Exception:
      najdene_ids = []

   if not najdene_ids:
      try:
         najdene_ids = await run_in_threadpool(provider.get_test_ids, obsah, mime_type)
      except Exception as e:
         vysledky.append({'subor': subor.filename, 'chyba': f'Nepodarilo sa prečítať id testu: {str(e)}'})
         return

   if not najdene_ids:
      vysledky.append({'subor': subor.filename, 'chyba': 'Nenašli sa žiadne ID testov.'})
      return

   # 2. KROK: Príprava XML kontextu
   xml_context = ''
   for tid in najdene_ids:
      cesta_xml = find_test_file(tid, cache)
      if cesta_xml:
         xml_context += f'\nContext for {tid}:\n{nacitaj_tests_xml(cesta_xml, tid)}'
      else:
         vysledky.append({'subor': subor.filename, 'test_id': tid, 'chyba': 'Zadanie nenájdené v DB'})

   if not xml_context:
      return

   # 3. KROK: Extrakcia odpovedí
   try:
      ai_data = await run_in_threadpool(provider.get_answers, obsah, mime_type, xml_context)
   except Exception as e:
      vysledky.append({'subor': subor.filename, 'chyba': f'Chyba pri rozpoznávaní odpovedí: {str(e)}'})
      return

   # 4. KROK: Zápis každého nájdeného testu
   for entry in ai_data.get('tests', []):
      tid = entry.get('test_id')
      cesta_tests = find_test_file(tid, cache)

      if not cesta_tests:
         vysledky.append({'subor': subor.filename, 'test_id': tid, 'chyba': 'Zadanie nenájdené v DB'})
         continue

      predmet, trieda, skupina, kapitola = ziskaj_metadata(cesta_tests)
      adresar = f'./res/xml/answers/{predmet}'
      Path(adresar).mkdir(parents=True, exist_ok=True)
      cesta_ans = Path(f'{adresar}/{predmet}_{trieda}{skupina}_{kapitola}.xml')
      lock = FileLock(f'{cesta_ans}.lock')
      form_data = {o['id']: o['odpoved'] for o in entry.get('odpovede', [])}

      try:
         await run_in_threadpool(write_answers_import, lock, cesta_ans, form_data, tid)
         vysledky.append({
            'subor': subor.filename,
            'test_id': tid,
            'predmet': predmet,
            'trieda': trieda,
            'skupina': skupina,
            'kapitola': kapitola,
            'zapisane': len(form_data),
            'nejasnosti': entry.get('nejasnosti', [])
         })
      except Exception as e:
         vysledky.append({'subor': subor.filename, 'test_id': tid, 'chyba': f'Chyba pri zápise: {str(e)}'})


@router.post('/admin/ai/importanswers')
async def importanswers(request: Request):
   form = await request.form()
   subory = form.getlist('obrazky')
   if not subory:
      raise HTTPException(status_code=400, detail='Žiadne súbory neboli nahrané.')

   cache = request.app.state.kluc_cache
   provider = request.app.state.ai_provider
   vysledky = []

   async with anyio.create_task_group() as tg:
      for subor in subory:
         tg.start_soon(_spracuj_subor, subor, cache, provider, vysledky)

   return JSONResponse(content={'vysledky': vysledky})
