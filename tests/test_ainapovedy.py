# -*- coding: utf-8 -*-

import logging
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import anyio
import pytest
from fastapi.exceptions import HTTPException
from jinja2 import Environment, FileSystemLoader
from saxonche import PySaxonProcessor

from app.routers import ai, ainapovedy
from app.routers.ai import _cache_nacitaj, _cache_uloz, _priprav_prompt, _zamok_napovede
from app.routers.ainapovedy import (
   _kluce_sady,
   _pocet_hotovych,
   _pregeneruj,
   _stav,
   _zamok_drzany,
   _zamok_pregen,
   _ziaci_generuju,
   napovedy_pregeneruj,
   napovedy_stav,
)

PREDMET = 'MAT'
TRIEDA = '1A'
KAPITOLA = 'kap1'
FILEID = 'ab12'
SABLONY = Environment(loader=FileSystemLoader(Path(ai.__file__).parents[1] / 'templates'))
LOGGER = logging.getLogger('test')

# test a and b: the same options in a different order; test c: a different subset of the options
TESTS_XML = f"""\
<?xml version='1.0' encoding='utf-8'?>
<testy predmet="{PREDMET}" trieda="{TRIEDA}" skupina="" kapitola="{KAPITOLA}" fileid="{FILEID}">
   <test id="a">
      <otazka id="q1"><znenie>Aká je <underline>hlavná</underline> farba?</znenie>
         <odpoved spravna="0">modrá</odpoved><odpoved spravna="1">červená</odpoved>
         <odpoved spravna="0">zelená</odpoved><odpoved spravna="0">žltá</odpoved></otazka>
      <otazka id="q2"><znenie>Kto napísal Hamleta?</znenie></otazka>
   </test>
   <test id="b">
      <otazka id="q1"><znenie>Aká je <underline>hlavná</underline> farba?</znenie>
         <odpoved spravna="0">žltá</odpoved><odpoved spravna="0">zelená</odpoved>
         <odpoved spravna="1">červená</odpoved><odpoved spravna="0">modrá</odpoved></otazka>
   </test>
   <test id="c">
      <otazka id="q1"><znenie>Aká je <underline>hlavná</underline> farba?</znenie>
         <odpoved spravna="0">modrá</odpoved><odpoved spravna="1">červená</odpoved>
         <odpoved spravna="0">zelená</odpoved><odpoved spravna="0">čierna</odpoved></otazka>
   </test>
</testy>
"""


@pytest.fixture(params=['asyncio', 'trio'])
def backend(request):
   return request.param


@pytest.fixture(autouse=True)
def workdir(tmp_path, monkeypatch):
   (tmp_path / 'res/xml/tests' / PREDMET).mkdir(parents=True)
   adresar = tmp_path / 'napovedy'
   adresar.mkdir(mode=0o700)
   monkeypatch.setattr(ai, 'CACHE_ADRESAR', str(adresar))
   monkeypatch.setattr(ainapovedy, '_KLUCE_CACHE', {})
   monkeypatch.chdir(tmp_path)


@pytest.fixture
def subor(tmp_path):
   cesta = tmp_path / 'res/xml/tests' / PREDMET / f'{PREDMET}_{TRIEDA}_{KAPITOLA}_{FILEID}.xml'
   cesta.write_text(TESTS_XML, encoding='utf-8')
   return f'./res/xml/tests/{PREDMET}/{cesta.name}'


def _kluce(subor):
   return _kluce_sady(SABLONY, PREDMET, KAPITOLA, subor, LOGGER)


# --- _kluce_sady ---

def test_kluce_sady_poradie_moznosti_nema_vplyv_ale_ina_podmnozina_ano(subor):
   kluce = _kluce(subor)
   assert sorted(otazka_id for otazka_id, _ in kluce.values()) == ['q1', 'q1', 'q2']


def test_kluce_sady_zhoduju_sa_s_kluckami_z_extrakcie_cez_saxon(subor):
   kluce = _kluce(subor)
   with PySaxonProcessor(license=False) as proc:
      xp = proc.new_xpath_processor()
      xp.set_context(xdm_item=proc.parse_xml(xml_file_name=subor))
      pocet = 0
      for test in xp.evaluate('//test') or []:
         xp.set_context(xdm_item=test)
         for otazka in xp.evaluate('otazka') or []:
            xp.set_context(xdm_item=otazka)
            znenie = xp.evaluate_single('string(znenie)').string_value
            spravna = xp.evaluate_single('odpoved[@spravna="1"]')
            moznosti = xp.evaluate('odpoved')
            _, kluc = _priprav_prompt(SABLONY, PREDMET, otazka.get_attribute_value('id'), znenie,
                                      [m.string_value.strip() for m in moznosti] if moznosti else [],
                                      spravna.string_value.strip() if spravna else None, [], [], LOGGER)
            assert kluc in kluce
            pocet += 1
      assert pocet == 4


def test_kluce_sady_sa_prepocita_po_zmene_suboru(subor, tmp_path):
   assert len(_kluce(subor)) == 3
   cesta = tmp_path / subor
   cesta.write_text(TESTS_XML.replace('<odpoved spravna="0">čierna</odpoved>', '<odpoved spravna="0">biela</odpoved>'), encoding='utf-8')
   st = cesta.stat()
   os.utime(cesta, ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))
   assert len(_kluce(subor)) == 3
   assert _kluce(subor) is _kluce(subor)


# --- stav ---

def test_stav_prazdna_ciastocna_uplna_cache(subor):
   kluce = _kluce(subor)
   cache = ai._cache_subor(PREDMET, TRIEDA, '', KAPITOLA, FILEID)
   assert _stav(kluce, cache, None) == {'hotove': 0, 'celkom': 3, 'bezi': False}
   for i, (kluc, (otazka_id, _)) in enumerate(kluce.items()):
      _cache_uloz(cache, otazka_id, kluc, f'hint {i}')
      assert _pocet_hotovych(kluce, cache) == i + 1
   assert _stav(kluce, cache, None)['hotove'] == 3


def test_stav_bez_cache_je_nula(subor):
   assert _pocet_hotovych(_kluce(subor), None) == 0


def test_stav_bezi_podla_zamku(subor):
   zamok = _zamok_pregen(subor)
   assert zamok is not None
   assert _stav({}, None, zamok)['bezi'] is False
   zamok.acquire()
   try:
      assert _stav({}, None, zamok)['bezi'] is True  # also for the instance that holds the lock
      assert _stav({}, None, _zamok_pregen(subor))['bezi'] is True
   finally:
      zamok.release()


def test_ziaci_generuju_podla_zamku_testu():
   assert _ziaci_generuju() is False
   zamok = _zamok_napovede('test_a')
   assert zamok is not None
   zamok.acquire()
   try:
      assert _ziaci_generuju() is True
      assert _zamok_drzany(_zamok_napovede('test_a')) is True  # type: ignore[arg-type]
   finally:
      zamok.release()
   assert _ziaci_generuju() is False


# --- _pregeneruj ---

class _Klient:
   def __init__(self, hinty, chyba_pri=None):
      self.volania = []
      self.hinty = hinty
      self.chyba_pri = chyba_pri

   async def chat(self, **kwargs):
      self.volania.append(kwargs['messages'])
      if self.chyba_pri == len(self.volania):
         raise ConnectionError('ollama nebezi')
      return {'message': {'content': f'HINT: {self.hinty[len(self.volania) - 1]}'}}


def _spusti(monkeypatch, backend, subor, klient):
   monkeypatch.setattr(ainapovedy.ollama, 'AsyncClient', lambda: klient)
   kluce = _kluce(subor)
   cache = ai._cache_subor(PREDMET, TRIEDA, '', KAPITOLA, FILEID)
   assert cache is not None
   zamok = _zamok_pregen(subor)
   assert zamok is not None
   zamok.acquire()
   anyio.run(_pregeneruj, kluce, cache, zamok, LOGGER, backend=backend)
   return kluce, cache, zamok


def test_pregeneruj_doplni_vsetky_kluce_a_uvolni_zamok(monkeypatch, backend, subor):
   klient = _Klient(['prvy', 'druhy', 'treti'])
   kluce, cache, zamok = _spusti(monkeypatch, backend, subor, klient)
   assert len(klient.volania) == 3
   assert _stav(kluce, cache, zamok) == {'hotove': 3, 'celkom': 3, 'bezi': False}
   hinty = {n['hint'] for varianty in _cache_nacitaj(cache).values() for v in varianty.values() for n in v['napovedy']}
   assert hinty == {'prvy', 'druhy', 'treti'}


def test_pregeneruj_preskoci_kluce_s_napovedou(monkeypatch, backend, subor):
   kluce = _kluce(subor)
   cache = ai._cache_subor(PREDMET, TRIEDA, '', KAPITOLA, FILEID)
   kluc, (otazka_id, _) = next(iter(kluce.items()))
   _cache_uloz(cache, otazka_id, kluc, 'uz tu je')
   klient = _Klient(['a', 'b'])
   _spusti(monkeypatch, backend, subor, klient)
   assert len(klient.volania) == 2
   assert _pocet_hotovych(kluce, cache) == 3


def test_pregeneruj_pri_chybe_skonci_a_uvolni_zamok(monkeypatch, backend, subor):
   klient = _Klient(['a', 'b', 'c'], chyba_pri=2)
   kluce, cache, zamok = _spusti(monkeypatch, backend, subor, klient)
   assert len(klient.volania) == 2
   assert _stav(kluce, cache, zamok) == {'hotove': 1, 'celkom': 3, 'bezi': False}


def test_pregeneruj_pocka_kym_ziak_caka_na_napovedu(monkeypatch, backend, subor):
   monkeypatch.setattr(ainapovedy, 'VOLNO_KROK', 0.02)
   klient = _Klient(['a', 'b', 'c'])
   monkeypatch.setattr(ainapovedy.ollama, 'AsyncClient', lambda: klient)
   kluce = _kluce(subor)
   cache = ai._cache_subor(PREDMET, TRIEDA, '', KAPITOLA, FILEID)
   zamok = _zamok_pregen(subor)
   ziak = _zamok_napovede('test_a')
   assert cache is not None and zamok is not None and ziak is not None
   zamok.acquire()
   ziak.acquire()

   async def run():
      async with anyio.create_task_group() as tg:
         tg.start_soon(_pregeneruj, kluce, cache, zamok, LOGGER)
         await anyio.sleep(0.2)
         assert klient.volania == []  # a student is waiting, the job does not queue in front of them
         ziak.release()
   anyio.run(run, backend=backend)
   assert len(klient.volania) == 3


# --- endpointy ---

class _TaskGroup:
   def __init__(self):
      self.ulohy = []

   def start_soon(self, *args):
      self.ulohy.append(args)


def _request() -> Any:
   state = SimpleNamespace(templates=SABLONY, logger=LOGGER, task_group=_TaskGroup())
   return SimpleNamespace(app=SimpleNamespace(state=state))


def test_endpoint_stav_vrati_postup(subor):
   vysledok = anyio.run(napovedy_stav, _request(), PREDMET, TRIEDA, KAPITOLA, FILEID, '')
   assert vysledok == {'hotove': 0, 'celkom': 3, 'bezi': False}


def test_endpoint_stav_neexistujuca_sada_je_404():
   with pytest.raises(HTTPException) as e:
      anyio.run(napovedy_stav, _request(), PREDMET, TRIEDA, KAPITOLA, 'nic', '')
   assert e.value.status_code == 404


def test_endpoint_stav_neplatny_parameter_je_400():
   with pytest.raises(HTTPException) as e:
      anyio.run(napovedy_stav, _request(), PREDMET, TRIEDA, '../x', FILEID, '')
   assert e.value.status_code == 400


def test_endpoint_pregeneruj_spusti_ulohu_len_raz(subor):
   request = _request()
   prvy = anyio.run(napovedy_pregeneruj, request, PREDMET, TRIEDA, KAPITOLA, FILEID, '')
   assert prvy == {'hotove': 0, 'celkom': 3, 'bezi': True, 'spusteny': True}
   assert len(request.app.state.task_group.ulohy) == 1
   druhy = anyio.run(napovedy_pregeneruj, request, PREDMET, TRIEDA, KAPITOLA, FILEID, '')
   assert druhy == {'hotove': 0, 'celkom': 3, 'bezi': True, 'spusteny': False}
   assert len(request.app.state.task_group.ulohy) == 1
   zamok = request.app.state.task_group.ulohy[0][3]
   zamok.release()
