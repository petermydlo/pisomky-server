# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

import shutil
from pathlib import Path

import pytest
from saxonche import PySaxonProcessor

from app.routers.aievaluate import (
   _normalizuj,
   _nahrad_placeholder,
   _nacitaj_udaje_ziaka,
   _nacitaj_otvorene_otazky,
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


# --- _nacitaj_otvorene_otazky ---

OPEN_TESTS_XML = f"""\
<?xml version='1.0' encoding='utf-8'?>
<testy predmet="{PREDMET}" trieda="{TRIEDA}" skupina="" kapitola="kap1" fileid="ab12">
   <test id="{TEST_ID}">
      <otazka id="q1" body="2"/>
      <otazka id="q2" body="1"/>
   </test>
</testy>
"""

OPEN_ANSWERS_XML = f"""\
<?xml version='1.0' encoding='utf-8'?>
<testy>
   <test id="{TEST_ID}">
      <otazka id="q1">rmdir ./zoznamy</otazka>
      <otazka id="q2">ls</otazka>
   </test>
</testy>
"""

OPEN_QUESTIONS_XML = """\
<?xml version='1.0' encoding='utf-8'?>
<kapitola>
   <kategoria>
      <otazka id="q1">
         <znenie>vymaže prázdny adresár</znenie>
         <vzor>rmdir ./zoznamy</vzor>
         <vzor>rm -d ./zoznamy</vzor>
         <vzor>cd ./zoznamy
            cd ..
            rmdir ./zoznamy</vzor>
      </otazka>
      <otazka id="q2">
         <znenie>otázka bez vzoru</znenie>
      </otazka>
   </kategoria>
</kapitola>
"""

def test_nacitaj_otvorene_otazky_viac_vzorov(tmp_path):
   xq = tmp_path / 'res/xquery/openquestions.xq'
   xq.parent.mkdir(parents=True)
   shutil.copy(Path(__file__).parent.parent / 'res/xquery/openquestions.xq', xq)
   (tmp_path / 'res/xml/answers' / PREDMET).mkdir(parents=True)
   (tmp_path / 'res/xml/questions' / PREDMET).mkdir(parents=True)
   nazov = f'{PREDMET}_{TRIEDA}_kap1_ab12.xml'
   (tmp_path / 'res/xml/tests' / PREDMET / nazov).write_text(OPEN_TESTS_XML, encoding='utf-8')
   (tmp_path / 'res/xml/answers' / PREDMET / nazov).write_text(OPEN_ANSWERS_XML, encoding='utf-8')
   (tmp_path / 'res/xml/questions' / PREDMET / f'{PREDMET}_kap1.xml').write_text(OPEN_QUESTIONS_XML, encoding='utf-8')

   with PySaxonProcessor(license=False) as proc:
      otazky = _nacitaj_otvorene_otazky(proc, f'./res/xml/tests/{PREDMET}/{nazov}', TEST_ID, PREDMET, 'kap1')

   assert [o['id'] for o in otazky] == ['q1']
   assert otazky[0]['vzory'] == ['rmdir ./zoznamy', 'rm -d ./zoznamy', 'cd ./zoznamy\ncd ..\nrmdir ./zoznamy']


# --- _evaluate_test ---

def _fake_response(text: str):
   return SimpleNamespace(stop_reason='end_turn', content=[SimpleNamespace(type='text', text=text)])

def test_evaluate_test_parsuje_ciste_json(monkeypatch):
   fake_client = MagicMock()
   fake_client.messages.create.return_value = _fake_response(
      '[{"id": "q1", "body": 2, "dovod": "Správne a úplné"}]'
   )
   monkeypatch.setattr('anthropic.Anthropic', lambda: fake_client)

   otazky = [{'id': 'q1', 'body': '2', 'znenie': 'Otázka?', 'vzory': ['Vzor'], 'klucove': [], 'odpoved': 'Odpoveď'}]
   ziak = {'meno': 'Ján', 'priezvisko': 'Novák', 'trieda': '1A', 'kod': TEST_ID}

   vysledok = _evaluate_test(otazky, ziak)
   assert vysledok == [{'id': 'q1', 'body': 2, 'dovod': 'Správne a úplné'}]

def test_evaluate_test_parsuje_json_v_code_fence(monkeypatch):
   fake_client = MagicMock()
   fake_client.messages.create.return_value = _fake_response(
      '```json\n[{"id": "q1", "body": 0, "dovod": "Nesprávne"}]\n```'
   )
   monkeypatch.setattr('anthropic.Anthropic', lambda: fake_client)

   otazky = [{'id': 'q1', 'body': '2', 'znenie': '', 'vzory': [], 'klucove': [], 'odpoved': ''}]
   ziak = {'meno': '', 'priezvisko': '', 'trieda': '', 'kod': ''}

   vysledok = _evaluate_test(otazky, ziak)
   assert vysledok == [{'id': 'q1', 'body': 0, 'dovod': 'Nesprávne'}]

def test_evaluate_test_odmietne_nedokoncenu_odpoved(monkeypatch):
   fake_client = MagicMock()
   fake_client.messages.create.return_value = SimpleNamespace(
      stop_reason='max_tokens', content=[SimpleNamespace(type='text', text='[{"id": "q1", "bo')]
   )
   monkeypatch.setattr('anthropic.Anthropic', lambda: fake_client)

   otazky = [{'id': 'q1', 'body': '2', 'znenie': '', 'vzory': [], 'klucove': [], 'odpoved': ''}]
   ziak = {'meno': '', 'priezvisko': '', 'trieda': '', 'kod': ''}

   with pytest.raises(ValueError, match='max_tokens'):
      _evaluate_test(otazky, ziak)

def test_evaluate_test_posle_placeholder_nahradeny_vzor(monkeypatch):
   fake_client = MagicMock()
   fake_client.messages.create.return_value = _fake_response('[]')
   monkeypatch.setattr('anthropic.Anthropic', lambda: fake_client)

   otazky = [{'id': 'q1', 'body': '1', 'znenie': 'Q', 'vzory': ['Vzor pre {meno}'], 'klucove': ['k1'], 'odpoved': 'A'}]
   ziak = {'meno': 'Ján', 'priezvisko': 'Novák', 'trieda': '1A', 'kod': TEST_ID}

   _evaluate_test(otazky, ziak)

   poslany_prompt = fake_client.messages.create.call_args.kwargs['messages'][0]['content']
   assert 'Vzor pre Ján' in poslany_prompt
   assert 'Ján Novák' in poslany_prompt

def test_evaluate_test_viac_vzorov_ako_alternativy(monkeypatch):
   fake_client = MagicMock()
   fake_client.messages.create.return_value = _fake_response('[]')
   monkeypatch.setattr('anthropic.Anthropic', lambda: fake_client)

   otazky = [{'id': 'q1', 'body': '1', 'znenie': 'Q', 'vzory': ['rmdir ./a', 'rm -d ./a'], 'klucove': [], 'odpoved': 'A'}]
   _evaluate_test(otazky, {'meno': '', 'priezvisko': '', 'trieda': '', 'kod': ''})

   poslany_prompt = fake_client.messages.create.call_args.kwargs['messages'][0]['content']
   assert 'alternatives' in poslany_prompt
   assert '- rmdir ./a' in poslany_prompt
   assert '- rm -d ./a' in poslany_prompt

def test_evaluate_test_viacriadkovy_vzor_zachova_riadky(monkeypatch):
   fake_client = MagicMock()
   fake_client.messages.create.return_value = _fake_response('[]')
   monkeypatch.setattr('anthropic.Anthropic', lambda: fake_client)

   otazky = [{'id': 'q1', 'body': '1', 'znenie': 'Q', 'vzory': ['prvý riadok\ndruhý riadok'], 'klucove': [], 'odpoved': 'A'}]
   _evaluate_test(otazky, {'meno': '', 'priezvisko': '', 'trieda': '', 'kod': ''})

   poslany_prompt = fake_client.messages.create.call_args.kwargs['messages'][0]['content']
   assert 'alternatives' not in poslany_prompt
   assert 'prvý riadok\n      druhý riadok' in poslany_prompt
