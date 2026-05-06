# -*- coding: utf-8 -*-

import os
import re
import json
import unicodedata
from pathlib import Path
import lxml.etree as ET
from app.mytypes import StringForm
from app.utils import find_test_file, xquery_to_string
from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool

router = APIRouter()

SYSTEM_PROMPT = (Path(__file__).parent.parent / 'templates' / 'aievaluate_system.md').read_text()


def _normalizuj(text: str) -> str:
   """Odstráni diakritiku — ekvivalent my:normalizuj() z XSL."""
   return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')


def _nahrad_placeholder(vzor: str, ziak: dict) -> str:
   """Nahradí {meno}, {priezvisko:low rep}, {X} atď.
   Známe typy → konkrétna hodnota.
   Neznáme typy → <any:X> (konzistentné naprieč otázkami).
   """
   hodnoty = {
      'meno':       ziak.get('meno', ''),
      'priezvisko': ziak.get('priezvisko', ''),
      'trieda':     ziak.get('trieda', ''),
      'kod':        ziak.get('kod', ''),
   }

   def nahrad(match: 're.Match') -> str:
      cast = match.group(1)
      parts = cast.split(':')
      typ = parts[0].strip()
      transforms = parts[1].split() if len(parts) > 1 else []
      if typ not in hodnoty:
         return f'<any:{typ}>'
      text = hodnoty[typ]
      if 'low' in transforms:
         text = text.lower()
      elif 'upp' in transforms:
         text = text.upper()
      if 'rep' in transforms:
         text = _normalizuj(text)
      return text

   return re.sub(r'\{([^}]+)\}', nahrad, vzor)


def _nacitaj_udaje_ziaka(cesta_tst: str, test_id: str, trieda: str) -> dict:
   """Načíta meno, priezvisko, triedu žiaka z tests XML."""
   meno = ''
   priezvisko = ''
   trieda_ziak = trieda
   try:
      tree = ET.parse(cesta_tst)
      test = next(iter(tree.xpath(".//test[@id=$id]", id=test_id)), None)
      if test is not None:
         meno = test.get('meno', '')
         priezvisko = test.get('priezvisko', '')
         trieda_ziak = test.get('trieda', '') or tree.getroot().get('trieda', trieda)
   except Exception:
      pass
   return {'meno': meno, 'priezvisko': priezvisko, 'trieda': trieda_ziak, 'kod': test_id}


def _nacitaj_otvorene_otazky(proc, cesta_tst: str, test_id: str, predmet: str, kapitola: str) -> list[dict]:
   """Načíta otvorené otázky testu s odpoveďami žiaka cez XQuery."""
   rel = cesta_tst.removeprefix('./res/')
   test_cesta      = '../' + rel
   answer_cesta    = '../' + rel.replace('tests/', 'answers/', 1)
   questions_cesta = f'../xml/questions/{predmet}/{predmet}_{kapitola}.xml'
   params = {
      'kluc':            test_id,
      'test_cesta':      test_cesta,
      'answer_cesta':    answer_cesta,
      'questions_cesta': questions_cesta,
   }
   try:
      xml_result = xquery_to_string(proc, './res/xquery/openquestions.xq', params=params)
      root = ET.fromstring(xml_result.encode())
      return [
         {
            'id':      o.get('id', ''),
            'body':    o.get('body', '1'),
            'znenie':  (o.findtext('znenie') or '').strip(),
            'vzor':    (o.findtext('vzor') or '').strip(),
            'klucove': [k.text.strip() for k in o.findall('klucove') if k.text],
            'odpoved': (o.findtext('odpoved') or '').strip(),
         }
         for o in root.findall('otazka')
      ]
   except Exception:
      return []


def _evaluate_test(otazky: list[dict], ziak: dict) -> list[dict]:
   """Pošle všetky otvorené otázky naraz do Claude a vráti hodnotenie."""
   import anthropic
   client = anthropic.Anthropic()

   meno_str = f"{ziak['meno']} {ziak['priezvisko']}".strip() or '(neznáme)'

   otazky_text = ''
   for i, ot in enumerate(otazky, 1):
      vzor = _nahrad_placeholder(ot['vzor'], ziak)
      klucove_str = ', '.join(ot['klucove']) if ot['klucove'] else '(žiadne)'
      otazky_text += f"""
Question {i} (id: {ot['id']}, max points: {ot['body']}):
  Text: {ot['znenie']}
  Model answer: {vzor}
  Key words: {klucove_str}
  Student's answer: {ot['odpoved']}
"""

   prompt = f"Student: {meno_str}\n{otazky_text}"

   resp = client.messages.create(
      model=os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-6'),
      max_tokens=500 + len(otazky) * 200,
      output_config={'effort': 'low'},
      system=SYSTEM_PROMPT,
      messages=[{'role': 'user', 'content': prompt}]
   )
   raw = resp.content[0].text.strip()
   if '```' in raw:
      raw = raw.split('```')[1]
      if raw.startswith('json'):
         raw = raw[4:]
      raw = raw.strip()
   return json.loads(raw)


@router.post('/admin/ai/evaluate-open')
async def evaluate_open(
   request: Request,
   test_id: StringForm,
   predmet: StringForm,
   trieda: StringForm,
   kapitola: StringForm,
   skupina: StringForm = ''
):
   """Vyhodnotí všetky otvorené odpovede žiaka naraz. Vráti zoznam {id, body, dovod}."""
   try:
      proc = request.app.state.proc
      cesta_tst = find_test_file(test_id) or ''
      ziak = await run_in_threadpool(_nacitaj_udaje_ziaka, cesta_tst, test_id, trieda)
      otazky = await run_in_threadpool(_nacitaj_otvorene_otazky, proc, cesta_tst, test_id, predmet, kapitola)

      if not otazky:
         return {'ok': False, 'kod': 'no_questions'}

      vysledky = await run_in_threadpool(_evaluate_test, otazky, ziak)
      return {'ok': True, 'vysledky': vysledky}

   except Exception as e:
      request.app.state.logger.error(f'chyba aievaluate: {e}')
      return {'ok': False, 'error': str(e)}
