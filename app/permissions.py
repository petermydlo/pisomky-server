# -*- coding: utf-8 -*-

"""Opravnenia ucitelov na upravu obsahu (kapitoly/kategorie/otazky/predmety), nacitane z .perm suboru.

Format riadku: 'meno: akcia:PREDMET[,PREDMET...] akcia:ALL ...'
Akcie: create, edit, delete, createp (vytvorenie predmetu, davaj len ako ALL),
deletep (vymazanie celeho predmetu). Chybajuci zaznam alebo akcia = zakazane.
"""

from pathlib import Path
from fastapi.exceptions import HTTPException

PERM_FILE = Path('.perm')


def _parse_perm_file(cesta: Path) -> dict[str, dict[str, set[str]]]:
   opravnenia: dict[str, dict[str, set[str]]] = {}
   if not cesta.exists():
      return opravnenia
   for riadok in cesta.read_text(encoding='utf-8').splitlines():
      riadok = riadok.strip()
      if not riadok or riadok.startswith('#') or ':' not in riadok:
         continue
      meno, _, zvysok = riadok.partition(':')
      meno = meno.strip()
      if not meno:
         continue
      akcie: dict[str, set[str]] = {}
      for token in zvysok.split():
         if ':' not in token:
            continue
         akcia, _, predmety = token.partition(':')
         akcia = akcia.strip()
         predmety_set = {p.strip() for p in predmety.split(',') if p.strip()}
         if not akcia or not predmety_set:
            continue
         akcie.setdefault(akcia, set()).update(predmety_set)
      opravnenia[meno] = akcie
   return opravnenia


def load_permissions(cache: dict) -> dict[str, dict[str, set[str]]]:
   """Nacita .perm subor, znovu naparsuje pri zmene mtime (hot reload)."""
   try:
      mtime = PERM_FILE.stat().st_mtime
   except FileNotFoundError:
      mtime = None
   if 'data' not in cache or cache.get('mtime') != mtime:
      cache['data'] = _parse_perm_file(PERM_FILE)
      cache['mtime'] = mtime
   return cache['data']


def has_permission(cache: dict, user: str, akcia: str, predmet: str) -> bool:
   predmety = load_permissions(cache).get(user, {}).get(akcia)
   if not predmety:
      return False
   return 'ALL' in predmety or predmet in predmety


def check_permission(cache: dict, user: str, akcia: str, predmet: str) -> None:
   """Vyhodi HTTPException(403), ak pouzivatel nema opravnenie 'akcia' pre 'predmet'."""
   if not has_permission(cache, user, akcia, predmet):
      raise HTTPException(status_code=403, detail=f'Nemáte oprávnenie "{akcia}" pre predmet {predmet}')


def predmet_from_cesta(cesta: str) -> str:
   """Odvodi kod predmetu z cesty k XML suboru v res/xml/questions/{predmet}/..."""
   return Path(cesta).parent.name
