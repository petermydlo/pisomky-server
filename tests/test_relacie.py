# -*- coding: utf-8 -*-
"""Jedno otvorenie testu počas písania: token (HMAC), prenájom a jeho vynútenie na trasách."""

import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from saxonche import PySaxonProcessor

import app.main as main
from app.routers import relacie

PROJECT_ROOT = Path(__file__).parent.parent
KLUC = 'K1'

TESTY_XML = """<?xml version='1.0' encoding='utf-8'?>
<testy predmet="MAT" trieda="1A" skupina="" kapitola="kap1" fileid="ab12">
   <test id="K1">
      <otazka id="q1"><znenie>Koľko je 1+1?</znenie><odpoved spravna="1">2</odpoved><odpoved spravna="0">3</odpoved></otazka>
   </test>
</testy>
"""


class Hodiny:
   def __init__(self):
      self.t = 1000.0

   def time(self):
      return self.t


@pytest.fixture
def hodiny(monkeypatch):
   h = Hodiny()
   monkeypatch.setattr(relacie, 'time', SimpleNamespace(time=h.time))
   return h


@pytest.fixture
def zapnute(tmp_path, monkeypatch):
   monkeypatch.setenv('RELACIA_TAJNY_KLUC', 'tajny-kluc-pre-testy')
   monkeypatch.setattr(relacie, 'ADRESAR', str(tmp_path / 'relacie'))


# --- vypnutie ---

def test_bez_tajneho_kluca_je_funkcia_vypnuta(tmp_path, monkeypatch):
   monkeypatch.delenv('RELACIA_TAJNY_KLUC', raising=False)
   monkeypatch.setattr(relacie, 'ADRESAR', str(tmp_path / 'relacie'))
   assert relacie.otvor(KLUC) == ''
   assert relacie.otvor(KLUC) == ''
   assert relacie.over(KLUC, None) is True
   assert relacie.vydaj_ucitelsky_token(KLUC) == ''


def test_cudzi_alebo_nesukromny_adresar_vypne_funkciu(tmp_path, zapnute):
   adresar = Path(relacie.ADRESAR)
   adresar.mkdir(mode=0o755)
   os.chmod(adresar, 0o755)  #mkdir mode ovplyvni umask
   assert relacie.zapnute() is False
   assert relacie.otvor(KLUC) == ''
   assert relacie.over(KLUC, 'hocico') is True


# --- prenajom ---

def test_druhe_otvorenie_je_odmietnute_kym_prenajom_plati(zapnute, hodiny):
   token = relacie.otvor(KLUC)
   assert token
   assert relacie.otvor(KLUC) is None
   hodiny.t += relacie.PRENAJOM - 1
   assert relacie.otvor(KLUC) is None


def test_prenajom_vyprsi_a_novy_drzitel_vytlaci_stary_token(zapnute, hodiny):
   stary = relacie.otvor(KLUC)
   hodiny.t += relacie.PRENAJOM + 1
   novy = relacie.otvor(KLUC)
   assert novy and novy != stary
   assert relacie.over(KLUC, novy) is True
   assert relacie.over(KLUC, stary) is False


def test_signal_predlzi_prenajom(zapnute, hodiny):
   token = relacie.otvor(KLUC)
   for _ in range(5):
      hodiny.t += relacie.PRENAJOM - 10
      assert relacie.over(KLUC, token) is True
   assert relacie.otvor(KLUC) is None


def test_uvolnenie_umozni_nove_otvorenie(zapnute, hodiny):
   token = relacie.otvor(KLUC)
   relacie.uvolni(KLUC, token)
   assert relacie.otvor(KLUC)


def test_uvolnit_moze_len_drzitel(zapnute, hodiny):
   drzitel = relacie.otvor(KLUC)
   hodiny.t += relacie.PRENAJOM + 1
   relacie.otvor(KLUC)   #prevzal novy drzitel
   relacie.uvolni(KLUC, drzitel)
   assert relacie.otvor(KLUC) is None


def test_prenajmy_roznych_klucov_su_nezavisle(zapnute, hodiny):
   assert relacie.otvor('K1')
   assert relacie.otvor('K2')


# --- token ---

def test_token_pre_iny_kluc_alebo_s_podvrhnutym_podpisom_neplati(zapnute, hodiny):
   token = relacie.otvor('K1')
   assert token
   assert relacie.over('K2', token) is False
   nonce, rola, podpis = token.split('.')
   assert relacie.over('K1', f'{nonce}.{rola}.{"0" * len(podpis)}') is False
   assert relacie.over('K1', f'{nonce}.a.{podpis}') is False   #zmena role nezachova podpis
   assert relacie.over('K1', '') is False
   assert relacie.over('K1', None) is False
   assert relacie.over('K1', 'a.b') is False


def test_token_podpisany_inym_kluckom_neplati(zapnute, hodiny, monkeypatch):
   token = relacie.otvor(KLUC)
   hodiny.t += relacie.PRENAJOM + 1   #nikto prenajom nedrzi, takze len podpis rozhoduje
   monkeypatch.setenv('RELACIA_TAJNY_KLUC', 'ina-hodnota')
   assert relacie.over(KLUC, token) is False


def test_strata_stavu_po_restarte_platny_token_znova_prevezme_prenajom(zapnute, hodiny):
   token = relacie.otvor(KLUC)
   shutil.rmtree(relacie.ADRESAR)   #reboot vymaze tmpfs
   assert relacie.over(KLUC, token) is True
   assert relacie.otvor(KLUC) is None   #prenajom je opat obsadeny


def test_ucitelsky_token_prenajom_ani_nevyzaduje_ani_neblokuje(zapnute, hodiny):
   ucitel = relacie.vydaj_ucitelsky_token(KLUC)
   assert relacie.over(KLUC, ucitel) is True
   ziak = relacie.otvor(KLUC)
   assert ziak                                   #ucitel ziakovi prenajom nezablokoval
   assert relacie.over(KLUC, ucitel) is True      #a ziakov prenajom neblokuje ucitela
   assert relacie.over(KLUC, ziak) is True
   assert relacie.otvor(KLUC) is None


# --- trasy ---

@pytest.fixture
def stranka(tmp_path, monkeypatch, zapnute):
   shutil.copytree(PROJECT_ROOT / 'app/templates', tmp_path / 'app/templates')
   (tmp_path / 'res/xml/tests/MAT').mkdir(parents=True)
   (tmp_path / 'res/xml/tests/MAT/MAT_1A_kap1_ab12.xml').write_text(TESTY_XML, encoding='utf-8')
   monkeypatch.chdir(tmp_path)
   main.app.state.kluc_cache.clear()
   main.app.state.mcq_hotove.clear()
   monkeypatch.setattr(main, 'xslt_to_string', lambda proc, **kw: f'<div id="hlavicka" token="{kw["params"]["token"]}"></div>')
   povodny = main.app.state.proc
   with PySaxonProcessor(license=False) as proc:
      main.app.state.proc = proc
      try:
         yield TestClient(main.app, base_url='http://pisomky.ternac.net')
      finally:
         main.app.state.proc = povodny


def _token(odpoved) -> str:
   return odpoved.text.split('token="')[1].split('"')[0]


def _uloz(klient, token, odpoved='a'):
   polia = {'q1': (None, odpoved)}
   if token is not None:
      polia['token'] = (None, token)
   return klient.post(f'/saveanswers/{KLUC}', files=polia)


def test_stranka_druhy_otvori_dostane_423_bez_obsahu_testu(stranka):
   prvy = stranka.get(f'/{KLUC}')
   assert prvy.status_code == 200 and _token(prvy)
   druhy = stranka.get(f'/{KLUC}')
   assert druhy.status_code == 423
   assert 'otvorený na inom mieste' in druhy.text
   assert 'hlavicka' not in druhy.text
   assert 'data-obsadene' in druhy.text  #stranku skryva index.js, kym skusi obnovit prenajom


def test_stranka_po_uvolneni_sa_da_otvorit_znova(stranka):
   token = _token(stranka.get(f'/{KLUC}'))
   assert stranka.post(f'/uvolni/{KLUC}', data={'token': token}).status_code == 204
   assert stranka.get(f'/{KLUC}').status_code == 200


def test_ping_s_tokenom_je_204_bez_neho_alebo_cudzom_423(stranka):
   token = _token(stranka.get(f'/{KLUC}'))
   assert stranka.post(f'/ping/{KLUC}', data={'token': token}).status_code == 204
   assert stranka.post(f'/ping/{KLUC}', data={'token': 'nie.s.token'}).status_code == 423
   assert stranka.post(f'/ping/{KLUC}').status_code == 423


def test_saveanswers_vyzaduje_platny_token(stranka):
   token = _token(stranka.get(f'/{KLUC}'))
   assert _uloz(stranka, None).status_code == 423
   assert _uloz(stranka, 'nie.s.token').status_code == 423
   assert _uloz(stranka, token).status_code == 201
   subor = next(Path('res/xml/answers/MAT').glob('*.xml'))
   assert '>a</otazka>' in subor.read_text(encoding='utf-8')


def test_odmietnute_ulozenie_nic_nezapise(stranka):
   assert _uloz(stranka, None).status_code == 423
   assert not list(Path('res/xml/answers').glob('**/*.xml'))


def test_stoptime_napoveda_a_hodnotenie_vyzaduju_token(stranka):
   assert stranka.post(f'/stoptime/{KLUC}').status_code == 423
   assert stranka.get('/ai/napoveda', params={'otazka_id': 'q1', 'test_id': KLUC}).status_code == 423
   assert stranka.post('/ai/feedback', data={'test_id': KLUC, 'val': 1, 'zapis_id': 'z'}).status_code == 423


def test_ucitelska_stranka_dostane_token_ktory_prenajom_ziaka_nezablokuje(stranka):
   ucitel = stranka.get(f'/admin/{KLUC}', headers={'X-Remote-User': 'sef'})
   assert ucitel.status_code == 200
   token_ucitela = _token(ucitel)
   ziak = stranka.get(f'/{KLUC}')
   assert ziak.status_code == 200
   assert _uloz(stranka, token_ucitela).status_code == 201   #ucitel pise aj ked ziak drzi prenajom


def test_vypnute_relacie_nic_neblokuju(stranka, monkeypatch):
   monkeypatch.delenv('RELACIA_TAJNY_KLUC')
   assert stranka.get(f'/{KLUC}').status_code == 200
   assert stranka.get(f'/{KLUC}').status_code == 200
   assert _uloz(stranka, None).status_code == 201
