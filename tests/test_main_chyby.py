# -*- coding: utf-8 -*-
"""Chyby pri zobrazení písomky žiakovi (GET /{kluc}) a štart aplikácie bez odpovedajúcej Ollamy."""

import logging
import shutil
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import anyio
import pytest
from fastapi.testclient import TestClient
from saxonche import PySaxonProcessor

import app.main as main

PROJECT_ROOT = Path(__file__).parent.parent
TAJNE = '/srv/web/pisomky/res/xml/tajna-cesta.xml'

TESTY_XML = """<?xml version='1.0' encoding='utf-8'?>
<testy predmet="MAT" trieda="1A" skupina="" kapitola="kap1" fileid="ab12">
   <test id="K1">
      <otazka id="q1"><znenie>Koľko je 1+1?</znenie><odpoved spravna="1">2</odpoved><odpoved spravna="0">3</odpoved></otazka>
   </test>
</testy>
"""


@pytest.fixture
def prostredie(tmp_path, monkeypatch):
   shutil.copytree(PROJECT_ROOT / 'app/templates', tmp_path / 'app/templates')
   (tmp_path / 'res/xml/tests/MAT').mkdir(parents=True)
   (tmp_path / 'res/xml/tests/MAT/MAT_1A_kap1_ab12.xml').write_text(TESTY_XML, encoding='utf-8')
   monkeypatch.chdir(tmp_path)
   main.app.state.kluc_cache.clear()
   main.app.state.mcq_hotove.clear()
   #Saxon riesi relativne cesty voci adresaru, v ktorom procesor vznikol, nie voci neskorsiemu chdir, preto vlastny procesor
   povodny = main.app.state.proc     #monkeypatch.setattr by pri undo atribut Starlette State zmazal, preto rucne
   with PySaxonProcessor(license=False) as proc:
      main.app.state.proc = proc
      try:
         yield
      finally:
         main.app.state.proc = povodny


def test_view_chyba_ukaze_ziakovi_obecnu_stranku_a_podrobnosti_zaloguje(prostredie, monkeypatch, caplog):
   def zlyhaj(*args, **kwargs):
      raise RuntimeError(TAJNE)

   monkeypatch.setattr(main, 'xslt_to_string', zlyhaj)
   with caplog.at_level(logging.ERROR, logger='pisomky'):
      odpoved = TestClient(main.app, base_url='http://pisomky.ternac.net').get('/K1')
   assert odpoved.status_code == 500
   assert 'nepodarilo načítať' in odpoved.text
   assert TAJNE not in odpoved.text
   assert TAJNE in caplog.text


def test_view_neznamy_kluc_je_stale_404(prostredie):
   odpoved = TestClient(main.app, base_url='http://pisomky.ternac.net').get('/NIE')
   assert odpoved.status_code == 404 and 'Test nenájdený' in odpoved.text


@pytest.fixture(params=['asyncio', 'trio'])
def backend(request):
   return request.param


class _NereagujucaOllama:
   async def chat(self, **_):
      await anyio.sleep_forever()


def test_start_nezablokuje_ollama_ktora_neodpoveda(monkeypatch, backend, caplog):
   import ollama
   monkeypatch.setattr(ollama, 'AsyncClient', lambda: _NereagujucaOllama())
   monkeypatch.setattr(main, 'OLLAMA_OHREV_TIMEOUT', 0.05)
   app = SimpleNamespace(state=SimpleNamespace(proc=MagicMock()))

   async def start():
      async with main.lifespan(app):  # type: ignore[arg-type]
         return app.state.task_group is not None

   zaciatok = time.monotonic()
   with caplog.at_level(logging.WARNING, logger='pisomky'):
      assert anyio.run(start, backend=backend) is True
   assert time.monotonic() - zaciatok < 3
   assert 'ohrev Ollamy zlyhal' in caplog.text
   app.state.proc.close.assert_called_once()
