# -*- coding: utf-8 -*-

"""HTTP klient nad skutocnou aplikaciou pre testy trás: parsovanie formulara, hlavicka `X-Remote-User` aj Depends bezia ako v produkcii.
Zavislosti z app/mytypes.py sa dajú prepísať cez `app.dependency_overrides` (napr. `proc=...`)."""

from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient
from app import main, mytypes

_ZAVISLOSTI = {
   'proc': mytypes._get_proc, 'logger': mytypes._get_logger, 'perm_cache': mytypes._get_perm_cache,
   'kluc_cache': mytypes._get_kluc_cache, 'mcq_hotove': mytypes._get_mcq_hotove, 'xslt_pools': mytypes._get_xslt_pools,
   'templates': mytypes._get_templates, 'task_group': mytypes._get_task_group, 'ai_provider': mytypes._get_ai_provider,
}

def _vrat(hodnota):
   """Prepis zavislosti bez parametrov (parameter s predvolenou hodnotou by FastAPI povazoval za query a kopiroval ho)."""
   return lambda: hodnota

@contextmanager
def http(user: str | None = 'sef', backend: Literal['asyncio', 'trio'] = 'asyncio', **zavislosti):
   """TestClient bez lifespan (task_group je preto None, ak ho test neprepise). Pouzitie: `with http(proc=proc) as c: c.post(...)`.
   Neosetrena vynimka v handleri sa vyhodi do testu (ako 500), HTTPException je odpoved so `status_code` a `json()['detail']`."""
   #kazdy test dostane cerstve cache (kluc_cache by inak drzala cesty z predosleho tmp_path); middleware cita perm_cache priamo z app.state
   zavislosti = {'task_group': None, 'perm_cache': {}, 'kluc_cache': {}, 'mcq_hotove': {}, **zavislosti}
   app = main.app
   povodne = dict(app.dependency_overrides)
   #chybovu stranku 404 renderuje app.state.templates s relativnou cestou, testy ale menia pracovny adresar
   povodne_sablony = app.state.templates
   app.state.perm_cache.clear()
   app.state.templates = Jinja2Templates(directory=Path(main.__file__).parent / 'templates')
   for nazov, hodnota in zavislosti.items():
      app.dependency_overrides[_ZAVISLOSTI[nazov]] = _vrat(hodnota)
   try:
      yield TestClient(app, base_url='http://pisomky.ternac.net', headers={'X-Remote-User': user} if user else {}, backend=backend)
   finally:
      app.state.templates = povodne_sablony
      app.dependency_overrides.clear()
      app.dependency_overrides.update(povodne)
