# -*- coding: utf-8 -*-

import pytest
import lxml.etree as ET
from pathlib import Path

from app.utils import (
   _hash_question,
   _hash_category,
   ensure_ids,
   find_chapter,
   find_category,
   find_question,
   create_chapter,
   delete_chapter,
   add_category,
   update_category,
   delete_category,
   add_question,
   update_question,
   delete_question,
   is_used,
   find_test_file,
)

PREDMET = 'MAT'

QUESTIONS_XML = """\
<?xml version='1.0' encoding='utf-8'?>
<kapitola predmet="MAT" id="kap1" nazov="Kapitola 1">
   <kategoria id="kat1" pocet="2" body="1">
      <otazka id="otq1" body="1">
         <znenie>Koľko je 2+2?</znenie>
         <odpoved spravna="1">4</odpoved>
         <odpoved>3</odpoved>
      </otazka>
      <otazka id="otq2" body="1">
         <znenie>Koľko je 3+3?</znenie>
         <odpoved spravna="1">6</odpoved>
         <odpoved>5</odpoved>
      </otazka>
   </kategoria>
</kapitola>
"""

QUESTIONS_NO_IDS_XML = """\
<?xml version='1.0' encoding='utf-8'?>
<kapitola predmet="MAT" id="kap2" nazov="Kapitola 2">
   <kategoria pocet="1" body="1">
      <otazka body="1">
         <znenie>Koľko je 1+1?</znenie>
         <odpoved spravna="1">2</odpoved>
         <odpoved>3</odpoved>
      </otazka>
   </kategoria>
</kapitola>
"""

TESTS_XML = """\
<?xml version='1.0' encoding='utf-8'?>
<testy predmet="MAT" trieda="1A" skupina="" kapitola="kap1">
   <test id="ABC123">
      <otazka id="otq1"/>
   </test>
</testy>
"""


@pytest.fixture(autouse=True)
def workdir(tmp_path, monkeypatch):
   (tmp_path / 'res/xml/questions' / PREDMET).mkdir(parents=True)
   (tmp_path / 'res/xml/tests' / PREDMET).mkdir(parents=True)
   monkeypatch.chdir(tmp_path)


@pytest.fixture
def questions_file(tmp_path):
   cesta = tmp_path / 'res/xml/questions' / PREDMET / f'{PREDMET}_kap1.xml'
   cesta.write_text(QUESTIONS_XML, encoding='utf-8')
   return cesta


@pytest.fixture
def tests_file(tmp_path):
   cesta = tmp_path / 'res/xml/tests' / PREDMET / f'{PREDMET}_1A_kap1.xml'
   cesta.write_text(TESTS_XML, encoding='utf-8')
   return cesta


# --- _hash_question ---

def test_hash_question_stabilny():
   otazka = ET.fromstring('<otazka body="1"><znenie>text</znenie><odpoved spravna="1">a</odpoved></otazka>')
   assert _hash_question(otazka, 'MAT') == _hash_question(otazka, 'MAT')

def test_hash_question_rozny_predmet():
   otazka = ET.fromstring('<otazka><znenie>text</znenie></otazka>')
   assert _hash_question(otazka, 'MAT') != _hash_question(otazka, 'FYZ')

def test_hash_question_rozny_obsah():
   o1 = ET.fromstring('<otazka><znenie>A</znenie></otazka>')
   o2 = ET.fromstring('<otazka><znenie>B</znenie></otazka>')
   assert _hash_question(o1, 'MAT') != _hash_question(o2, 'MAT')

def test_hash_question_dlzka():
   otazka = ET.fromstring('<otazka><znenie>text</znenie></otazka>')
   assert len(_hash_question(otazka, 'MAT')) == 8


# --- _hash_category ---

def test_hash_category_stabilny():
   kat = ET.fromstring('<kategoria><otazka id="abc"/><otazka id="def"/></kategoria>')
   assert _hash_category(kat, 'subor1') == _hash_category(kat, 'subor1')

def test_hash_category_rozny_subor():
   kat = ET.fromstring('<kategoria><otazka id="abc"/></kategoria>')
   assert _hash_category(kat, 'subor1') != _hash_category(kat, 'subor2')


# --- ensure_ids ---

def test_ensure_ids_prida_id(tmp_path):
   cesta = tmp_path / 'res/xml/questions' / PREDMET / f'{PREDMET}_kap2.xml'
   cesta.write_text(QUESTIONS_NO_IDS_XML, encoding='utf-8')
   ensure_ids(str(cesta))
   tree = ET.parse(str(cesta))
   for otazka in tree.findall('.//otazka'):
      assert otazka.get('id') is not None
   for kat in tree.findall('.//kategoria'):
      assert kat.get('id') is not None

def test_ensure_ids_idempotentny(tmp_path):
   cesta = tmp_path / 'res/xml/questions' / PREDMET / f'{PREDMET}_kap2.xml'
   cesta.write_text(QUESTIONS_NO_IDS_XML, encoding='utf-8')
   ensure_ids(str(cesta))
   ids1 = [o.get('id') for o in ET.parse(str(cesta)).findall('.//otazka')]
   ensure_ids(str(cesta))
   ids2 = [o.get('id') for o in ET.parse(str(cesta)).findall('.//otazka')]
   assert ids1 == ids2

def test_ensure_ids_unikatne(tmp_path):
   xml = """\
<?xml version='1.0' encoding='utf-8'?>
<kapitola predmet="MAT" id="kap3">
   <kategoria pocet="1">
      <otazka body="1"><znenie>Q1</znenie><odpoved spravna="1">A</odpoved></otazka>
      <otazka body="1"><znenie>Q2</znenie><odpoved spravna="1">B</odpoved></otazka>
      <otazka body="1"><znenie>Q3</znenie><odpoved spravna="1">C</odpoved></otazka>
   </kategoria>
</kapitola>
"""
   cesta = tmp_path / 'res/xml/questions' / PREDMET / f'{PREDMET}_kap3.xml'
   cesta.write_text(xml, encoding='utf-8')
   ensure_ids(str(cesta))
   ids = [o.get('id') for o in ET.parse(str(cesta)).findall('.//otazka')]
   assert len(ids) == len(set(ids))

def test_ensure_ids_neexistujuci_subor(tmp_path):
   ensure_ids(str(tmp_path / 'neexistuje.xml'))  # nesmie vyhodiť výnimku


# --- find_chapter ---

def test_find_chapter_najde(questions_file):
   kapitola, _ = find_chapter('kap1', PREDMET)
   assert kapitola is not None
   assert kapitola.get('id') == 'kap1'

def test_find_chapter_nenajde(questions_file):
   kapitola, cesta = find_chapter('neexistuje', PREDMET)
   assert kapitola is None
   assert cesta is None

def test_find_chapter_cache(questions_file):
   cache = {}
   find_chapter('kap1', PREDMET, cache)
   assert any('kap1' in k for k in cache)
   kapitola, _ = find_chapter('kap1', PREDMET, cache)
   assert kapitola is not None


# --- find_category ---

def test_find_category_najde(questions_file):
   kategoria, _ = find_category('kat1')
   assert kategoria is not None
   assert kategoria.get('id') == 'kat1'

def test_find_category_nenajde(questions_file):
   kategoria, _ = find_category('neexistuje')
   assert kategoria is None


# --- find_question ---

def test_find_question_najde(questions_file):
   otazka, _ = find_question('otq1')
   assert otazka is not None
   assert otazka.get('id') == 'otq1'

def test_find_question_nenajde(questions_file):
   otazka, _ = find_question('neexistuje')
   assert otazka is None


# --- create_chapter ---

def test_create_chapter_uspech(tmp_path):
   kid, ok = create_chapter(PREDMET, 'novakap')
   assert ok is True
   assert kid == 'novakap'
   assert (tmp_path / 'res/xml/questions' / PREDMET / f'{PREDMET}_novakap.xml').exists()

def test_create_chapter_duplicit(tmp_path):
   create_chapter(PREDMET, 'novakap')
   kid, ok = create_chapter(PREDMET, 'novakap')
   assert ok is False
   assert kid is None


# --- delete_chapter ---

def test_delete_chapter_uspech(questions_file):
   result = delete_chapter('kap1', PREDMET)
   assert result is True
   assert not questions_file.exists()

def test_delete_chapter_pouzita(questions_file, tests_file):
   result = delete_chapter('kap1', PREDMET)
   assert result is False  # kap1 obsahuje otq1 ktorá je v tests
   assert questions_file.exists()

def test_delete_chapter_nenajde(questions_file):
   result = delete_chapter('neexistuje', PREDMET)
   assert result is False


# --- is_used ---

def test_is_used_pouzita(tests_file):
   assert is_used('otq1') is True

def test_is_used_nepouzita(tests_file):
   assert is_used('neexistuje') is False


# --- find_test_file ---

def test_find_test_file_najde(tests_file):
   assert find_test_file('ABC123') is not None

def test_find_test_file_nenajde(tests_file):
   assert find_test_file('XXXXXX') is None

def test_find_test_file_cache(tests_file):
   cache = {}
   find_test_file('ABC123', cache)
   assert 'ABC123' in cache
   assert find_test_file('ABC123', cache) is not None


# --- update_category ---

def test_update_category_pocet(questions_file):
   assert update_category('kat1', {'pocet': '5'}) is True
   kat = ET.parse(str(questions_file)).find('.//kategoria[@id="kat1"]')
   assert kat.get('pocet') == '5'

def test_update_category_odstran_atribut(questions_file):
   update_category('kat1', {'static': '1'})
   update_category('kat1', {'static': None})
   kat = ET.parse(str(questions_file)).find('.//kategoria[@id="kat1"]')
   assert kat.get('static') is None

def test_update_category_nenajde(questions_file):
   assert update_category('neexistuje', {'pocet': '5'}) is False


# --- delete_category ---

def test_delete_category_nepouzita(questions_file):
   assert delete_category('kat1') is True
   assert ET.parse(str(questions_file)).find('.//kategoria[@id="kat1"]') is None

def test_delete_category_pouzita(questions_file, tests_file):
   assert delete_category('kat1') is True
   kat = ET.parse(str(questions_file)).find('.//kategoria[@id="kat1"]')
   assert kat is not None
   assert kat.get('deprecated') == '1'

def test_delete_category_nenajde(questions_file):
   assert delete_category('neexistuje') is False


# --- add_category ---

def test_add_category_uspech(questions_file):
   kid, ok = add_category('kap1', {'pocet': '3', 'body': '2'}, predmet=PREDMET)
   assert ok is True
   assert kid is not None
   kat = ET.parse(str(questions_file)).find(f'.//kategoria[@id="{kid}"]')
   assert kat is not None
   assert kat.get('pocet') == '3'

def test_add_category_nenajde_kapitolu(questions_file):
   kid, ok = add_category('neexistuje', {'pocet': '1'})
   assert ok is False
   assert kid is None


# --- update_question ---

def test_update_question_body(questions_file):
   assert update_question('otq1', {'body': '5'}) is True
   otazka = ET.parse(str(questions_file)).find('.//otazka[@id="otq1"]')
   assert otazka.get('body') == '5'

def test_update_question_znenie(questions_file):
   assert update_question('otq1', {'znenie': '<znenie>Nové znenie</znenie>'}) is True
   otazka = ET.parse(str(questions_file)).find('.//otazka[@id="otq1"]')
   assert otazka.find('znenie').text == 'Nové znenie'

def test_update_question_odpovede(questions_file):
   nove = [{'text': 'X', 'spravna': '1'}, {'text': 'Y', 'spravna': '0'}]
   update_question('otq1', {'odpovede': nove})
   odpovede = ET.parse(str(questions_file)).findall('.//otazka[@id="otq1"]/odpoved')
   assert len(odpovede) == 2
   assert odpovede[0].text == 'X'
   assert odpovede[0].get('spravna') == '1'
   assert odpovede[1].get('spravna') is None

def test_update_question_nenajde(questions_file):
   assert update_question('neexistuje', {'body': '5'}) is False


# --- delete_question ---

def test_delete_question_nepouzita(questions_file):
   assert delete_question('otq2') is True
   assert ET.parse(str(questions_file)).find('.//otazka[@id="otq2"]') is None

def test_delete_question_pouzita(questions_file, tests_file):
   assert delete_question('otq1') is True
   otazka = ET.parse(str(questions_file)).find('.//otazka[@id="otq1"]')
   assert otazka is not None
   assert otazka.get('deprecated') == '1'

def test_delete_question_nenajde(questions_file):
   assert delete_question('neexistuje') is False


# --- add_question ---

def test_add_question_uspech(questions_file):
   nova = {
      'znenie': '<znenie>Nová otázka?</znenie>',
      'body': '2',
      'odpovede': [{'text': 'Áno', 'spravna': '1'}, {'text': 'Nie', 'spravna': '0'}],
   }
   qid, ok = add_question('kat1', nova)
   assert ok is True
   assert qid is not None
   otazka = ET.parse(str(questions_file)).find(f'.//otazka[@id="{qid}"]')
   assert otazka is not None
   assert otazka.get('body') == '2'

def test_add_question_nenajde_kategoriu(questions_file):
   qid, ok = add_question('neexistuje', {'znenie': '<znenie>?</znenie>'})
   assert ok is False
   assert qid is None
