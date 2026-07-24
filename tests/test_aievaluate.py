# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.routers.aievaluate import (
   _normalizuj,
   _nahrad_placeholder,
   _nacitaj_udaje_ziaka,
   _evaluate_test,
)

PREDMET = 'MAT'
TRIEDA = '1A'
TEST_ID = 'TEST01'

TESTS_XML = f"""\
<?xml version='1.0' encoding='utf-8'?>
<testy predmet="{PREDMET}" trieda="{TRIEDA}" skupina="" kapitola="kap1" fileid="ab12">
   <test id="{TEST_ID}" meno="Ján" priezvisko="Novák" trieda="{TRIEDA}">
      <otazka id="q1"/>
   </test>
   <test id="TEST02">
      <otazka id="q1"/>
   </test>
</testy>
"""


@pytest.fixture(autouse=True)
def workdir(tmp_path, monkeypatch):
   (tmp_path / 'res/xml/tests' / PREDMET).mkdir(parents=True)
   monkeypatch.chdir(tmp_path)


@pytest.fixture
def tests_file(tmp_path):
   cesta = tmp_path / 'res/xml/tests' / PREDMET / f'{PREDMET}_{TRIEDA}_kap1_ab12.xml'
   cesta.write_text(TESTS_XML, encoding='utf-8')
   return cesta


# --- _normalizuj ---

def test_normalizuj_odstrani_diakritiku():
   assert _normalizuj('Ľuboš Čerešňa') == 'Lubos Ceresna'

def test_normalizuj_bez_diakritiky_nezmeni():
   assert _normalizuj('Peter Novak') == 'Peter Novak'


# --- _nahrad_placeholder ---

def test_nahrad_placeholder_zakladne_hodnoty():
   ziak = {'meno': 'Ján', 'priezvisko': 'Novák', 'trieda': '1A', 'kod': 'TEST01'}
   assert _nahrad_placeholder('Ahoj {meno} {priezvisko}!', ziak) == 'Ahoj Ján Novák!'

def test_nahrad_placeholder_low_transform():
   ziak = {'meno': 'Ján', 'priezvisko': '', 'trieda': '', 'kod': ''}
   assert _nahrad_placeholder('{meno:low}', ziak) == 'ján'

def test_nahrad_placeholder_upp_transform():
   ziak = {'meno': 'Ján', 'priezvisko': '', 'trieda': '', 'kod': ''}
   assert _nahrad_placeholder('{meno:upp}', ziak) == 'JÁN'

def test_nahrad_placeholder_rep_transform_odstrani_diakritiku():
   ziak = {'meno': 'Ján', 'priezvisko': '', 'trieda': '', 'kod': ''}
   assert _nahrad_placeholder('{meno:rep}', ziak) == 'Jan'

def test_nahrad_placeholder_kombinovane_transformy():
   ziak = {'meno': 'Ján', 'priezvisko': '', 'trieda': '', 'kod': ''}
   assert _nahrad_placeholder('{meno:low rep}', ziak) == 'jan'

def test_nahrad_placeholder_neznamy_typ():
   ziak = {'meno': '', 'priezvisko': '', 'trieda': '', 'kod': ''}
   assert _nahrad_placeholder('{xyz}', ziak) == '<any:xyz>'

def test_nahrad_placeholder_bez_placeholderov():
   ziak = {'meno': '', 'priezvisko': '', 'trieda': '', 'kod': ''}
   assert _nahrad_placeholder('Obyčajný text', ziak) == 'Obyčajný text'


# --- _nacitaj_udaje_ziaka ---

def test_nacitaj_udaje_ziaka_najde_ziaka(tests_file):
   udaje = _nacitaj_udaje_ziaka(str(tests_file), TEST_ID, TRIEDA)
   assert udaje == {'meno': 'Ján', 'priezvisko': 'Novák', 'trieda': TRIEDA, 'kod': TEST_ID}

def test_nacitaj_udaje_ziaka_bez_triedy_pouzije_root(tests_file):
   udaje = _nacitaj_udaje_ziaka(str(tests_file), 'TEST02', 'iná')
   assert udaje['trieda'] == TRIEDA

def test_nacitaj_udaje_ziaka_neexistujuci_test():
   udaje = _nacitaj_udaje_ziaka('./neexistuje.xml', TEST_ID, TRIEDA)
   assert udaje == {'meno': '', 'priezvisko': '', 'trieda': TRIEDA, 'kod': TEST_ID}


# --- _evaluate_test ---

def _fake_response(text: str):
   return SimpleNamespace(content=[SimpleNamespace(type='text', text=text)])

def test_evaluate_test_parsuje_ciste_json(monkeypatch):
   fake_client = MagicMock()
   fake_client.messages.create.return_value = _fake_response(
      '[{"id": "q1", "body": 2, "dovod": "Správne a úplné"}]'
   )
   monkeypatch.setattr('anthropic.Anthropic', lambda: fake_client)

   otazky = [{'id': 'q1', 'body': '2', 'znenie': 'Otázka?', 'vzor': 'Vzor', 'klucove': [], 'odpoved': 'Odpoveď'}]
   ziak = {'meno': 'Ján', 'priezvisko': 'Novák', 'trieda': '1A', 'kod': TEST_ID}

   vysledok = _evaluate_test(otazky, ziak)
   assert vysledok == [{'id': 'q1', 'body': 2, 'dovod': 'Správne a úplné'}]

def test_evaluate_test_parsuje_json_v_code_fence(monkeypatch):
   fake_client = MagicMock()
   fake_client.messages.create.return_value = _fake_response(
      '```json\n[{"id": "q1", "body": 0, "dovod": "Nesprávne"}]\n```'
   )
   monkeypatch.setattr('anthropic.Anthropic', lambda: fake_client)

   otazky = [{'id': 'q1', 'body': '2', 'znenie': '', 'vzor': '', 'klucove': [], 'odpoved': ''}]
   ziak = {'meno': '', 'priezvisko': '', 'trieda': '', 'kod': ''}

   vysledok = _evaluate_test(otazky, ziak)
   assert vysledok == [{'id': 'q1', 'body': 0, 'dovod': 'Nesprávne'}]

def test_evaluate_test_posle_placeholder_nahradeny_vzor(monkeypatch):
   fake_client = MagicMock()
   fake_client.messages.create.return_value = _fake_response('[]')
   monkeypatch.setattr('anthropic.Anthropic', lambda: fake_client)

   otazky = [{'id': 'q1', 'body': '1', 'znenie': 'Q', 'vzor': 'Vzor pre {meno}', 'klucove': ['k1'], 'odpoved': 'A'}]
   ziak = {'meno': 'Ján', 'priezvisko': 'Novák', 'trieda': '1A', 'kod': TEST_ID}

   _evaluate_test(otazky, ziak)

   poslany_prompt = fake_client.messages.create.call_args.kwargs['messages'][0]['content']
   assert 'Vzor pre Ján' in poslany_prompt
   assert 'Ján Novák' in poslany_prompt
