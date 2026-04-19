# -*- coding: utf-8 -*-

import os
import re
import json
import glob
import unicodedata
import lxml.etree as ET
from app.mytypes import StringForm
from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool

router = APIRouter()

SYSTEM_PROMPT = """You are a teacher's assistant evaluating a student's test.
You will receive a list of open questions with model answers and the student's answers.

Your task for each question:
1. Compare the student's answer to the model answer and key words
2. Assign points from 0 to the maximum
3. Write a brief reason in Slovak (1-2 sentences) explaining the score

Rules:
- Be fair but strict — partial knowledge deserves partial points
- If key words are present but explanation is weak, give partial credit
- If the answer is completely wrong or missing, give 0
- The model answer may contain <any> markers — the student can use any reasonable value there
- The model answer may contain <any:X> markers where X is a name — ALL occurrences of the same
  <any:X> across all questions must have been answered with the SAME value by the student.
  Check consistency across questions — if the student used different values for the same <any:X>,
  deduct points accordingly.

Return ONLY a JSON array, one object per question, no other text:
[{"id": "<question id>", "body": <integer>, "dovod": "<reason in Slovak>"}, ...]"""


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

   def nahrad(match):
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


def _nacitaj_udaje_ziaka(predmet: str, trieda: str, skupina: str, kapitola: str, test_id: str) -> dict:
   """Načíta meno, priezvisko, triedu žiaka z tests XML."""
   cesta = f'./res/xml/tests/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}.xml'
   meno = ''
   priezvisko = ''
   trieda_ziak = trieda
   try:
      tree = ET.parse(cesta)
      test = next(iter(tree.xpath(".//test[@id=$id]", id=test_id)), None)
      if test is not None:
         meno = test.get('meno', '')
         priezvisko = test.get('priezvisko', '')
         trieda_ziak = test.get('trieda', '') or tree.getroot().get('trieda', trieda)
   except Exception:
      pass
   return {'meno': meno, 'priezvisko': priezvisko, 'trieda': trieda_ziak, 'kod': test_id}


def _nacitaj_otazku_questions(predmet: str, otazka_id: str) -> dict | None:
   """Načíta znenie, vzor a kľúčové slová z questions XML. None ak nemá vzor."""
   for cesta in glob.iglob(f'./res/xml/questions/{predmet}/*.xml'):
      try:
         tree = ET.parse(cesta)
         otazka = next(iter(tree.xpath(".//otazka[@id=$id]", id=otazka_id)), None)
         if otazka is None:
            continue
         vzor_el = otazka.find('vzor')
         if vzor_el is None or not vzor_el.text:
            return None
         znenie_el = otazka.find('znenie')
         znenie = ET.tostring(znenie_el, encoding='unicode', method='text').strip() if znenie_el is not None else ''
         klucove = [s.text.strip() for s in otazka.findall('klucove_slova/slovo') if s.text]
         return {'znenie': znenie, 'vzor': vzor_el.text.strip(), 'klucove': klucove}
      except Exception:
         continue
   return None


def _nacitaj_otvorene_otazky(predmet: str, test_id: str, trieda: str, skupina: str, kapitola: str) -> list[dict]:
   """Načíta všetky otvorené otázky testu s odpoveďami žiaka."""
   cesta_tst = f'./res/xml/tests/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}.xml'
   cesta_ans = f'./res/xml/answers/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}.xml'

   odpovede = {}
   try:
      tree = ET.parse(cesta_ans)
      for otazka in tree.xpath(".//test[@id=$id]/otazka", id=test_id):
         if otazka.text:
            odpovede[otazka.get('id', '')] = otazka.text.strip()
   except Exception:
      pass

   otazky_testu = []
   try:
      tree = ET.parse(cesta_tst)
      test = next(iter(tree.xpath(".//test[@id=$id]", id=test_id)), None)
      if test is None:
         return []
      for otazka in test.findall('otazka'):
         if otazka.find('odpoved') is not None:
            continue   # single choice — preskočíme
         otazky_testu.append({'id': otazka.get('id', ''), 'body': otazka.get('body', '1')})
   except Exception:
      return []

   vysledok = []
   for ot in otazky_testu:
      oid = ot['id']
      odpoved = odpovede.get(oid)
      if not odpoved:
         continue
      q_data = _nacitaj_otazku_questions(predmet, oid)
      if q_data is None:
         continue   # no_vzor — ticho preskočíme
      vysledok.append({
         'id':      oid,
         'body':    ot['body'],
         'znenie':  q_data['znenie'],
         'vzor':    q_data['vzor'],
         'klucove': q_data['klucove'],
         'odpoved': odpoved,
      })

   return vysledok


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
      ziak = await run_in_threadpool(_nacitaj_udaje_ziaka, predmet, trieda, skupina, kapitola, test_id)
      otazky = await run_in_threadpool(_nacitaj_otvorene_otazky, predmet, test_id, trieda, skupina, kapitola)

      if not otazky:
         return {'ok': False, 'kod': 'no_questions'}

      vysledky = await run_in_threadpool(_evaluate_test, otazky, ziak)
      return {'ok': True, 'vysledky': vysledky}

   except Exception as e:
      request.app.state.logger.error(f'chyba aievaluate: {e}')
      return {'ok': False, 'error': str(e)}
