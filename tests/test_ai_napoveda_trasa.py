# -*- coding: utf-8 -*-
"""Trasa GET /ai/napoveda bez modelu: chybove vetvy, limit nápoved, zamok testu a odpoved z cache."""

import json
import logging
from pathlib import Path
from types import SimpleNamespace

import anyio
import lxml.etree as ET
import pytest
from jinja2 import Environment, FileSystemLoader
from saxonche import PySaxonProcessor

from app.routers import ai
from app.routers.ai import napoveda, _priprav_prompt, _cache_subor, _cache_uloz, _uloz_zapis, _zamok_napovede

PREDMET = 'MAT'
KLUC = 'TEST01'
KLUC_JEDNA = 'TEST_JEDNA'
SABLONY = Environment(loader=FileSystemLoader(Path(ai.__file__).parents[1] / 'templates'))
ZNENIE = 'Koľko je 1/2 + 1/4?'
FEEDBACK = f'./res/xml/feedback/{PREDMET}/{PREDMET}_1A_kap1_ab12.xml'

TESTY_XML = f"""\
<?xml version='1.0' encoding='utf-8'?>
<testy predmet="{PREDMET}" trieda="1A" skupina="" kapitola="kap1" fileid="ab12">
   <test id="{KLUC}">
      <otazka id="q1">
         <znenie>{ZNENIE}</znenie>
         <odpoved spravna="0">1/6</odpoved>
         <odpoved spravna="1">3/4</odpoved>
      </otazka>
      <otazka id="qt">
         <znenie>Doplň tabuľku</znenie>
         <tabulka><riadok><bunka odpoved="1"/></riadok></tabulka>
      </otazka>
      <otazka id="qprazdna">
         <znenie/>
         <odpoved spravna="1">a</odpoved>
      </otazka>
   </test>
   <test id="{KLUC_JEDNA}">
      <otazka id="q1">
         <znenie>{ZNENIE}</znenie>
         <odpoved spravna="0">1/6</odpoved>
         <odpoved spravna="1">3/4</odpoved>
      </otazka>
   </test>
</testy>
"""


def _zapis_banku(tmp_path, otazky_xml):
   """Banka otazok kapitoly kap1, z ktorej trasa cita povolenie AI napovede (s_napovedou)."""
   (tmp_path / f'res/xml/questions/{PREDMET}/{PREDMET}_kap1.xml').write_text(
      f'<kapitola id="kap1" predmet="{PREDMET}"><kategoria id="k1" pocet="1">{otazky_xml}</kategoria></kapitola>', encoding='utf-8')


@pytest.fixture(autouse=True)
def pracovny_adresar(tmp_path, monkeypatch):
   for cesta in ('res/xml/tests', 'res/xml/feedback', 'res/xml/questions'):
      (tmp_path / cesta / PREDMET).mkdir(parents=True)
   (tmp_path / f'res/xml/tests/{PREDMET}/{PREDMET}_1A_kap1_ab12.xml').write_text(TESTY_XML, encoding='utf-8')
   _zapis_banku(tmp_path, '<otazka id="q1" s_napovedou="1"><znenie>x</znenie></otazka><otazka id="qprazdna" s_napovedou="1"><znenie>x</znenie></otazka>')
   cache = tmp_path / 'napovedy'
   cache.mkdir(mode=0o700)
   monkeypatch.setattr(ai, 'CACHE_ADRESAR', str(cache))
   monkeypatch.chdir(tmp_path)


@pytest.fixture(params=['asyncio', 'trio'])
def backend(request):
   return request.param


def _zavolaj(backend, test_id=KLUC, otazka_id='q1'):
   """Zavola trasu a vrati (status, udalosti SSE alebo JSON telo)."""
   async def disconnected():
      return False

   async def run():
      with PySaxonProcessor(license=False) as proc:
         state = SimpleNamespace(proc=proc, kluc_cache={}, logger=logging.getLogger('test'), templates=SABLONY, task_group=None)
         request = SimpleNamespace(app=SimpleNamespace(state=state), is_disconnected=disconnected)
         odpoved = await napoveda(request, otazka_id, test_id)  # type: ignore[arg-type]
         if hasattr(odpoved, 'body_iterator'):
            text = ''.join([c if isinstance(c, str) else c.decode() async for c in odpoved.body_iterator])  # type: ignore[union-attr]
            return odpoved.status_code, [(blok.split('\n')[0][len('event: '):], json.loads(blok.split('\n')[1][len('data: '):])) for blok in text.strip().split('\n\n')]
         return odpoved.status_code, json.loads(bytes(odpoved.body))
   return anyio.run(run, backend=backend)


def _pocet_zapisov():
   try:
      return len(ET.parse(FEEDBACK).findall('.//zapis'))
   except OSError:
      return 0


def test_neznamy_test_je_404(backend):
   status, telo = _zavolaj(backend, test_id='NEEXISTUJE')
   assert status == 404 and telo == {'error': 'Test nenájdený'}


def test_otazka_bez_povolenej_napovedy_je_403_a_nezapise(backend, tmp_path):
   _zapis_banku(tmp_path, '<otazka id="q1"><znenie>x</znenie></otazka>')
   status, telo = _zavolaj(backend)
   assert status == 403 and telo == {'error': 'Pre túto otázku nie je nápoveda'}
   assert _pocet_zapisov() == 0


def test_neznama_otazka_je_404(backend):
   status, telo = _zavolaj(backend, otazka_id='nie')
   assert status == 404 and telo == {'error': 'Otázka nenájdená'}
   assert _pocet_zapisov() == 0


def test_otazka_s_tabulkou_nema_napovedu(backend):
   status, telo = _zavolaj(backend, otazka_id='qt')
   assert status == 400 and telo == {'error': 'Pre túto otázku nie je nápoveda'}
   assert _pocet_zapisov() == 0


def test_prazdne_znenie_je_400(backend):
   status, telo = _zavolaj(backend, otazka_id='qprazdna')
   assert status == 400 and telo == {'error': 'Prázdne znenie otázky'}
   assert _pocet_zapisov() == 0


def test_vycerpany_limit_posle_udalost_a_nezapise(backend):
   _uloz_zapis(FEEDBACK, 'z1', 'q1', KLUC_JEDNA, PREDMET, '1A', '', 'kap1', 'ab12')   # test ma jednu otazku, teda jednu napovedu
   status, udalosti = _zavolaj(backend, test_id=KLUC_JEDNA)
   assert status == 200 and udalosti == [('napoveda_limit', {})]
   assert _pocet_zapisov() == 1


def test_obsadeny_zamok_posle_udalost_a_nezapise(backend, monkeypatch):
   async def nikdy(*_, **__):
      return False

   monkeypatch.setattr(ai, '_zamok_ziskaj', nikdy)
   zamok = _zamok_napovede(KLUC)
   assert zamok is not None
   with zamok:
      status, udalosti = _zavolaj(backend)
   assert status == 200 and udalosti == [('napoveda_obsadena', {})]
   assert _pocet_zapisov() == 0


def test_napoveda_z_cache_vytvori_zapis_a_zapocita_sa(backend):
   _, cache_kluc = _priprav_prompt(SABLONY, PREDMET, 'q1', ZNENIE, ['1/6', '3/4'], '3/4', [], [], logging.getLogger('test'))
   _cache_uloz(_cache_subor(PREDMET, 'kap1'), 'q1', cache_kluc, 'Zamysli sa nad menovateľom')
   status, udalosti = _zavolaj(backend)
   assert status == 200
   assert [typ for typ, _ in udalosti] == ['meta', 'chunk', 'done']
   assert udalosti[0][1]['remaining'] == 1     # napovedu maju 2 z 3 otazok (tabulka nie), jedna sa prave spotrebovala
   assert udalosti[2][1] == {'hint': 'Zamysli sa nad menovateľom'}
   zapis = ET.parse(FEEDBACK).find('.//zapis')
   assert zapis is not None
   assert [zapis.get('id'), zapis.get('test_id'), zapis.get('otazka_id')] == [udalosti[0][1]['zapis_id'], KLUC, 'q1']
   assert zapis.findtext('hint') == 'Zamysli sa nad menovateľom'
   # a zlozka lock je uvolnena, takze dalsia nepozastavena ziadost prejde k zamku
   zamok = _zamok_napovede(KLUC)
   assert zamok is not None
   zamok.acquire(timeout=0)
   zamok.release()
