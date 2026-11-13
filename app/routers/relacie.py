# -*- coding: utf-8 -*-
"""Jedno otvorenie testu pocas pisania: prenajom s podpisanym tokenom.

Server pri otvoreni testu (stav 'during') vydá token, ktory ziakova stranka posiela pri kazdom zapise
a v pravidelnom pingu. Kym prenajom 'zije' (posledny signal je mladsi ako PRENAJOM s), dalsie otvorenie
rovnakeho kluca server odmietne. Token je podpisany HMAC (RELACIA_TAJNY_KLUC), takze jeho platnost
server overi aj po strate stavu (restart, reboot); stav je len 'aktualny nonce + cas posledneho signalu'
v tmpfs. Bez RELACIA_TAJNY_KLUC alebo pri nepouzitelnom adresari je funkcia vypnuta (nic sa neblokuje).
Ucitelska stranka (/admin/{kluc}) dostane token s rolou 'a': prenajom nevyzaduje ani neblokuje."""

import hashlib
import hmac
import json
import os
import secrets
import stat
import time

from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import HTTPException
from fastapi.responses import Response
from filelock import FileLock

from app.mytypes import StringForm, StringPath

load_dotenv()

router = APIRouter()

ADRESAR = '/tmp/pisomky-relacie'
#ako dlho po poslednom signali (ping, zapis) prenajom plati (s); klient posiela ping castejsie, pozri test.js
PRENAJOM = 60
CHYBA_OBSADENE = 'Test je otvorený na inom mieste.'
ROLA_ZIAK = 's'
ROLA_UCITEL = 'a'


def _tajny_kluc() -> bytes | None:
   kluc = os.getenv('RELACIA_TAJNY_KLUC', '').strip()
   return kluc.encode('utf-8') if kluc else None


def _sukromny_adresar() -> bool:
   """True when ADRESAR exists (it is created when missing) and is private to this user; /tmp is world-writable."""
   try:
      os.makedirs(ADRESAR, mode=0o700, exist_ok=True)
      st = os.lstat(ADRESAR)
   except OSError:
      return False
   return stat.S_ISDIR(st.st_mode) and st.st_uid == os.geteuid() and not st.st_mode & 0o077


def zapnute() -> bool:
   return _tajny_kluc() is not None and _sukromny_adresar()


def _podpis(kluc: str, nonce: str, rola: str) -> str:
   tajny = _tajny_kluc() or b''
   return hmac.new(tajny, f'{kluc}\0{nonce}\0{rola}'.encode('utf-8'), hashlib.sha256).hexdigest()[:32]


def _token(kluc: str, nonce: str, rola: str) -> str:
   return f'{nonce}.{rola}.{_podpis(kluc, nonce, rola)}'


def _rozparsuj(kluc: str, token: str) -> tuple[str, str] | None:
   """Vrati (nonce, rola) pre token podpisany pre tento kluc, inak None."""
   casti = token.split('.')
   if len(casti) != 3 or casti[1] not in (ROLA_ZIAK, ROLA_UCITEL):
      return None
   nonce, rola, podpis = casti
   if not hmac.compare_digest(podpis, _podpis(kluc, nonce, rola)):
      return None
   return nonce, rola


def _subor(kluc: str) -> str:
   return os.path.join(ADRESAR, hashlib.sha256(kluc.encode('utf-8')).hexdigest()[:16] + '.json')


def _nacitaj(subor: str) -> dict:
   try:
      with open(subor, encoding='utf-8') as f:
         data = json.load(f)
   except (OSError, ValueError):
      return {}
   return data if isinstance(data, dict) else {}


def _zapis(subor: str, data: dict) -> None:
   tmp = subor + '.tmp'
   with open(tmp, 'w', encoding='utf-8') as f:
      json.dump(data, f)
   os.replace(tmp, subor)


def _volny(stav: dict, teraz: float) -> bool:
   try:
      return teraz - float(stav.get('last_seen', 0)) > PRENAJOM
   except (TypeError, ValueError):
      return True


def vydaj_ucitelsky_token(kluc: str) -> str:
   """Token pre /admin/{kluc}; '' ak su relacie vypnute."""
   return _token(kluc, secrets.token_hex(8), ROLA_UCITEL) if zapnute() else ''


def otvor(kluc: str) -> str | None:
   """Zacne prenajom testu. Vrati token, '' ak su relacie vypnute, alebo None ak je test uz otvoreny inde."""
   if not zapnute():
      return ''
   subor = _subor(kluc)
   with FileLock(subor + '.lock'):
      teraz = time.time()
      if not _volny(_nacitaj(subor), teraz):
         return None
      nonce = secrets.token_hex(8)
      _zapis(subor, {'nonce': nonce, 'last_seen': teraz})
      return _token(kluc, nonce, ROLA_ZIAK)


def over(kluc: str, token: str | None) -> bool:
   """True, ak token smie s testom pracovat; obnovi prenajom. Platny token bez aktualneho drzitela
   (prenajom vyprsal, alebo sa stav stratil restartom) si prenajom znova zoberie."""
   if not zapnute():
      return True
   rozparsovane = _rozparsuj(kluc, token or '')
   if rozparsovane is None:
      return False
   nonce, rola = rozparsovane
   if rola == ROLA_UCITEL:
      return True
   subor = _subor(kluc)
   with FileLock(subor + '.lock'):
      stav = _nacitaj(subor)
      teraz = time.time()
      if _volny(stav, teraz) or stav.get('nonce') == nonce:
         _zapis(subor, {'nonce': nonce, 'last_seen': teraz})
         return True
      return False


def uvolni(kluc: str, token: str | None) -> None:
   """Ukonci prenajom, ak ho drzi tento token (zatvorenie alebo obnovenie stranky)."""
   if not zapnute():
      return
   rozparsovane = _rozparsuj(kluc, token or '')
   if rozparsovane is None or rozparsovane[1] != ROLA_ZIAK:
      return
   subor = _subor(kluc)
   with FileLock(subor + '.lock'):
      if _nacitaj(subor).get('nonce') == rozparsovane[0]:
         try:
            os.remove(subor)
         except OSError:
            pass


def over_alebo_403(kluc: str, token: str | None) -> None:
   if not over(kluc, token):
      raise HTTPException(status_code=423, detail=CHYBA_OBSADENE)


@router.post('/ping/{kluc}')
async def ping(kluc: StringPath, token: StringForm = ''):
   await run_in_threadpool(over_alebo_403, kluc, token)
   return Response(status_code=204)


@router.post('/uvolni/{kluc}')
async def uvolni_relaciu(kluc: StringPath, token: StringForm = ''):
   await run_in_threadpool(uvolni, kluc, token)
   return Response(status_code=204)
