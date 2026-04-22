# -*- coding: utf-8 -*-

from app.utils import find_test, get_test_metadata
from app.mytypes import IntForm, StringForm
from fastapi import APIRouter, Request
from filelock import FileLock
from lxml import etree
import os

router = APIRouter()

@router.post('/ai/feedback')
async def ai_feedback(request: Request, test_id: StringForm, val: IntForm, zapis_id: StringForm):
   try:
      proc = request.app.state.proc
      test_node = find_test(proc=proc, kluc=test_id, admin=True, cache=request.app.state.kluc_cache)
      if not test_node:
         return {'ok': False, 'error': 'Test nenájdený'}

      predmet, trieda, skupina, kapitola = get_test_metadata(proc, test_node)

      nazov = f'{predmet}_{trieda}{skupina}_{kapitola}.xml'
      subor = f'./res/xml/feedback/{predmet}/{nazov}'

      if not os.path.exists(subor):
         return {'ok': False, 'error': 'Feedback súbor neexistuje'}

      lock = FileLock(subor + '.lock')
      with lock:
         xmlParser = etree.XMLParser(remove_blank_text=True)
         tree = etree.parse(subor, xmlParser)
         root = tree.getroot()

         zapis = next((z for z in root.findall('.//zapis') if z.get('id') == zapis_id), None)
         if zapis is None:
            return {'ok': False, 'error': 'Záznam nenájdený'}

         zapis.set('val', str(val))

         tree = etree.ElementTree(root)
         etree.indent(tree, space='   ')
         tree.write(subor, encoding='UTF-8', xml_declaration=True)

      return {'ok': True}
   except Exception as e:
      request.app.state.logger.error(f'chyba feedback: {e}')
      return {'ok': False, 'error': str(e)}
