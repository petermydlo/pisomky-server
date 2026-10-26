# -*- coding: utf-8 -*-

import glob
import hashlib
import os
import anyio
import ollama
from filelock import FileLock, Timeout
from lxml import etree as ET
from fastapi import APIRouter, Request
from fastapi.exceptions import HTTPException
from app.routers import ai
from app.routers.ai import (
   OLLAMA_RUNNER_OPTIONS,
   _cache_nacitaj,
   _cache_subor,
   _cache_uloz,
   _parsuj_hint,
   _priprav_prompt,
   _sukromny_adresar,
)
from app.mytypes import StringForm, StringQuery
from app.utils import test_xml_path

router = APIRouter()

VOLNO_KROK = 2

# {cesta testov: ((mtime testov, mtime otazok), {cache kluc: (otazka_id, messages)})}
_KLUCE_CACHE: dict[str, tuple[tuple[int, int], dict[str, tuple[str, list[dict]]]]] = {}


def _mtime(cesta: str) -> int:
   try:
      return os.stat(cesta).st_mtime_ns
   except OSError:
      return 0


def _kluce_sady(templates, predmet: str, kapitola: str, subor: str, logger) -> dict[str, tuple[str, list[dict]]]:
   """Returns {cache key: (question id, messages)} for every distinct hint request that the
   tests of one set can produce. Students share a key when the question has the same wording
   and options (in any order), so this is about one entry per question. The result is kept until
   the test file or the question bank changes."""
   verzia = (_mtime(subor), _mtime(f'./res/xml/questions/{predmet}/{predmet}_{kapitola}.xml'))
   zaznam = _KLUCE_CACHE.get(subor)
   if zaznam and zaznam[0] == verzia:
      return zaznam[1]
   kluce: dict[str, tuple[str, list[dict]]] = {}
   videne: set[tuple] = set()
   for otazka in ET.parse(subor).getroot().iterfind('test/otazka'):
      znenie = str(otazka.xpath('string(znenie)'))
      if not znenie:
         continue
      otazka_id = otazka.get('id', '')
      moznosti = [str(o.xpath('string(.)')).strip() for o in otazka.iterfind('odpoved')]
      spravna = otazka.find('odpoved[@spravna="1"]')
      spravna_odpoved = str(spravna.xpath('string(.)')).strip() if spravna is not None else None
      vstup = (otazka_id, znenie, tuple(sorted(moznosti)), spravna_odpoved)
      if vstup in videne:
         continue
      videne.add(vstup)
      messages, kluc = _priprav_prompt(templates, predmet, otazka_id, znenie, moznosti, spravna_odpoved, [], [], logger)
      kluce.setdefault(kluc, (otazka_id, messages))
   _KLUCE_CACHE[subor] = (verzia, kluce)
   return kluce


def _pocet_hotovych(kluce: dict[str, tuple[str, list[dict]]], cache_subor: str | None) -> int:
   """Number of keys that have at least one hint in the cache."""
   if not cache_subor:
      return 0
   data = _cache_nacitaj(cache_subor)
   return sum(1 for kluc, (otazka_id, _) in kluce.items() if data.get(otazka_id, {}).get(kluc, {}).get('napovedy'))


def _zamok_pregen(subor: str) -> FileLock | None:
   """Lock held while the hints of one set are being generated (flock: released by the kernel
   if the worker dies). None when the private cache directory is not available."""
   if not _sukromny_adresar():
      return None
   return FileLock(os.path.join(ai.CACHE_ADRESAR, f'pregen_{hashlib.sha256(subor.encode("utf-8")).hexdigest()[:16]}.lock'))


def _zamok_drzany(zamok: FileLock) -> bool:
   """True when somebody holds the lock. A new instance is used for the probe: an instance is
   reentrant, so the one that holds the lock would always acquire it again."""
   proba = FileLock(zamok.lock_file)
   try:
      proba.acquire(timeout=0)
   except Timeout:
      return True
   proba.release()
   return False


def _ziaci_generuju() -> bool:
   """True while any student waits for a hint (the per-test lock of `/ai/napoveda` is held)."""
   return any(_zamok_drzany(FileLock(cesta)) for cesta in glob.glob(os.path.join(ai.CACHE_ADRESAR, 'bezi_*.lock')))


async def _pregeneruj(kluce: dict[str, tuple[str, list[dict]]], cache_subor: str, zamok: FileLock, logger) -> None:
   """Generates one hint for every key without a hint in the cache, one after another. While
   a student waits for a hint the job pauses, so it never queues in front of the students."""
   try:
      client = ollama.AsyncClient()
      for kluc, (otazka_id, messages) in kluce.items():
         if _cache_nacitaj(cache_subor).get(otazka_id, {}).get(kluc, {}).get('napovedy'):
            continue
         while _ziaci_generuju():
            await anyio.sleep(VOLNO_KROK)
         odpoved = await client.chat(
            model=os.getenv('OLLAMA_MODEL', 'qwen3.5:9b'),
            messages=messages,
            think=False,
            options={'temperature': 0.3, **OLLAMA_RUNNER_OPTIONS, 'keep_alive': '45m'}
         )
         hint = _parsuj_hint(odpoved['message']['content'])
         if hint:
            _cache_uloz(cache_subor, otazka_id, kluc, hint)
   except Exception as e:
      logger.error(f'chyba pregeneracia napovedi: {e}')
   finally:
      zamok.release()


def _sada(request: Request, predmet: str, trieda: str, skupina: str, kapitola: str, fileid: str):
   """Returns (test file, cache file, keys, lock) of one set, or raises 400/404."""
   try:
      subor = test_xml_path(predmet, trieda, skupina, kapitola, fileid)
   except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e))
   if not os.path.isfile(subor):
      raise HTTPException(status_code=404, detail='Testy neexistujú')
   kluce = _kluce_sady(request.app.state.templates, predmet, kapitola, subor, request.app.state.logger)
   return subor, _cache_subor(predmet, kapitola), kluce, _zamok_pregen(subor)


def _stav(kluce: dict[str, tuple[str, list[dict]]], cache_subor: str | None, zamok: FileLock | None) -> dict:
   return {'hotove': _pocet_hotovych(kluce, cache_subor), 'celkom': len(kluce), 'bezi': bool(zamok and _zamok_drzany(zamok))}


@router.get('/admin/napovedy/stav')
async def napovedy_stav(request: Request, predmet: StringQuery, trieda: StringQuery, kapitola: StringQuery, fileid: StringQuery, skupina: StringQuery = ''):
   _, cache_subor, kluce, zamok = _sada(request, predmet, trieda, skupina, kapitola, fileid)
   return _stav(kluce, cache_subor, zamok)


@router.post('/admin/napovedy/pregeneruj')
async def napovedy_pregeneruj(request: Request, predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = ''):
   _, cache_subor, kluce, zamok = _sada(request, predmet, trieda, skupina, kapitola, fileid)
   if not zamok or not cache_subor:
      raise HTTPException(status_code=503, detail='Cache nápovedí nie je dostupná')
   spusteny = False
   try:
      zamok.acquire(timeout=0)
      request.app.state.task_group.start_soon(_pregeneruj, kluce, cache_subor, zamok, request.app.state.logger)
      spusteny = True
   except Timeout:
      pass
   return {**_stav(kluce, cache_subor, zamok), 'spusteny': spusteny}
