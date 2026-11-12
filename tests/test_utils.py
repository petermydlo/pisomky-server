# -*- coding: utf-8 -*-

import logging

import pytest
import lxml.etree as ET

from app.utils import (
   _hash_question,
   normalizuj_vzor,
   _hash_category,
   ensure_ids,
   find_chapter,
   find_category,
   find_question,
   create_chapter,
   over_id_kapitoly,
   over_predmet,
   update_chapter,
   delete_chapter,
   create_predmet,
   delete_predmet,
   _skolsky_rok,
   add_category,
   update_category,
   delete_category,
   restore_category,
   add_question,
   update_question,
   delete_question,
   restore_question,
   fork_question,
   zmenene_zamrznute_polia,
   is_used,
   find_test_file,
   test_xml_path as xml_path,
   modify_test_xml,
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

@pytest.mark.parametrize('predmet, kapitola_id', [('PIT3', '01'), ('AUT3', '02.5'), ('SXT4', 'kap_1-a'), ('DEMO', 'A')])
def test_over_id_kapitoly_platne(predmet, kapitola_id):
   over_id_kapitoly(predmet, kapitola_id)

@pytest.mark.parametrize('kapitola_id', ['', '../x', 'a/b', 'a\\b', 'a b', 'č', '01\n'])
def test_over_id_kapitoly_zle_id(kapitola_id):
   with pytest.raises(ValueError, match='ID kapitoly'):
      over_id_kapitoly('PIT3', kapitola_id)

@pytest.mark.parametrize('predmet', ['', 'pit3', 'P', '../..', 'PIT3/x', '*', 'ABCDEFGHIJK', 'PIT3\n'])
def test_over_id_kapitoly_zly_predmet(predmet):
   with pytest.raises(ValueError, match='Skratka predmetu'):
      over_id_kapitoly(predmet, '01')

@pytest.mark.parametrize('predmet', ['PIT3', 'AUT3', 'DEMO', 'AB'])
def test_over_predmet_platny(predmet):
   over_predmet(predmet)

@pytest.mark.parametrize('predmet', ['', 'pit3', 'P', '../..', 'PIT3/x', '*', 'PIT3\n'])
def test_over_predmet_zly(predmet):
   with pytest.raises(ValueError, match='Skratka predmetu'):
      over_predmet(predmet)


# --- update_chapter ---

def test_update_chapter_nazov(questions_file):
   assert update_chapter('kap1', PREDMET, 'Nový názov') is True
   root = ET.parse(str(questions_file)).getroot()
   assert root.get('nazov') == 'Nový názov'

def test_update_chapter_nenajde(questions_file):
   assert update_chapter('neexistuje', PREDMET, 'X') is False


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


# --- create_predmet ---

def test_create_predmet_uspech(tmp_path):
   assert create_predmet('NOV4') is True
   assert (tmp_path / 'res/xml/questions' / 'NOV4').is_dir()

def test_create_predmet_duplicit(tmp_path):
   assert create_predmet(PREDMET) is False  # existuje uz z fixtury workdir

def test_create_predmet_zly_format():
   assert create_predmet('nov4') is False  # male pismena
   assert create_predmet('../etc') is False
   assert create_predmet('X') is False  # prilis kratke
   assert create_predmet('NOV4\n') is False  # koncovy novy riadok


# --- delete_predmet ---

def test_delete_predmet_uspech(questions_file, tmp_path):
   ok, dovod = delete_predmet(PREDMET)
   assert ok is True
   assert dovod is None
   assert not (tmp_path / 'res/xml/questions' / PREDMET).exists()
   rok = _skolsky_rok()
   assert (tmp_path / 'res/xml/archiv' / rok / f'{PREDMET}_{rok}_otazky.tar.xz').exists()

def test_delete_predmet_pouzita(questions_file, tests_file, tmp_path):
   ok, dovod = delete_predmet(PREDMET)
   assert ok is False
   assert dovod is not None
   assert (tmp_path / 'res/xml/questions' / PREDMET).exists()

def test_delete_predmet_neexistuje():
   ok, dovod = delete_predmet('NEEXIST')
   assert ok is False

def test_delete_predmet_zly_format():
   ok, dovod = delete_predmet('../etc')
   assert ok is False
   ok, _ = delete_predmet('NOV4\n')
   assert ok is False


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
   assert kat is not None
   assert kat.get('pocet') == '5'

def test_update_category_odstran_atribut(questions_file):
   update_category('kat1', {'static': '1'})
   update_category('kat1', {'static': None})
   kat = ET.parse(str(questions_file)).find('.//kategoria[@id="kat1"]')
   assert kat is not None
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
   assert otazka is not None
   assert otazka.get('body') == '5'

def test_update_question_znenie(questions_file):
   assert update_question('otq1', {'znenie': '<znenie>Nové znenie</znenie>'}) is True
   otazka = ET.parse(str(questions_file)).find('.//otazka[@id="otq1"]')
   assert otazka is not None
   znenie = otazka.find('znenie')
   assert znenie is not None
   assert znenie.text == 'Nové znenie'

def test_update_question_odpovede(questions_file):
   nove = [{'text': 'X', 'spravna': '1'}, {'text': 'Y', 'spravna': '0'}]
   update_question('otq1', {'odpovede': nove})
   odpovede = ET.parse(str(questions_file)).findall('.//otazka[@id="otq1"]/odpoved')
   assert len(odpovede) == 2
   assert odpovede[0].text == 'X'
   assert odpovede[0].get('spravna') == '1'
   assert odpovede[1].get('spravna') == '0'

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


# --- test_xml_path ---

def test_xml_path_bez_skupiny():
   cesta = xml_path('MAT', '1A', '', 'kap1', 'ab12')
   assert cesta == './res/xml/tests/MAT/MAT_1A_kap1_ab12.xml'

def test_xml_path_so_skupinou():
   cesta = xml_path('MAT', '1A', 'sk1', 'kap1', 'ab12')
   assert cesta == './res/xml/tests/MAT/MAT_1Ask1_kap1_ab12.xml'

def test_xml_path_kapitola_s_bodkou():
   cesta = xml_path('AUT3', '1A', '', '02.5', 'ab12')
   assert cesta == './res/xml/tests/AUT3/AUT3_1A_02.5_ab12.xml'

def test_xml_path_bez_fileid():
   cesta = xml_path('MAT', '1A', '', 'kap1', '')
   assert cesta == './res/xml/tests/MAT/MAT_1A_kap1_.xml'

@pytest.mark.parametrize('predmet, trieda, skupina, kapitola, fileid', [
   ('../x', '1A', '', 'kap1', 'ab12'),
   ('MAT', '1A', '', '../..', 'ab12'),
   ('MAT', '1A', '', 'kap1', 'a/b'),
   ('MAT', '1A', '', 'kap/1', 'ab12'),
   ('..', '1A', '', 'kap1', 'ab12'),
   ('MAT.', '1A', '', 'kap1', 'ab12'),
   ('MAT', '1A', '', 'kap1', 'a.b'),
   ('MAT', '/../x', '', 'kap1', 'ab12'),
   ('MAT', '1A', 'sk/1', 'kap1', 'ab12'),
   ('MAT\n', '1A', '', 'kap1', 'ab12'),
   ('MAT', '1A\n', '', 'kap1', 'ab12'),
   ('MAT', '1A', '', 'kap1\n', 'ab12'),
   ('MAT', '1A', '', 'kap1', 'ab12\n'),
])
def test_xml_path_odmietne_neplatny_parameter(predmet, trieda, skupina, kapitola, fileid):
   with pytest.raises(ValueError, match='Neplatný parameter'):
      xml_path(predmet, trieda, skupina, kapitola, fileid)


# --- modify_test_xml ---

def test_modify_test_xml_zmeni_atribut(tests_file):
   def callback(tree):
      tree.getroot().set('start', '2026-01-01T08:00')
   modify_test_xml(str(tests_file), callback)
   tree = ET.parse(str(tests_file))
   assert tree.getroot().get('start') == '2026-01-01T08:00'

def test_modify_test_xml_neexistujuci_subor(tmp_path):
   cesta = str(tmp_path / 'neexistuje.xml')
   with pytest.raises(OSError):
      modify_test_xml(cesta, lambda tree: None)


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


# --- restore_category ---

def test_restore_category_odstrani_deprecated(questions_file, tests_file):
   delete_category('kat1')
   kat = ET.parse(str(questions_file)).find('.//kategoria[@id="kat1"]')
   assert kat is not None
   assert kat.get('deprecated') == '1'
   assert restore_category('kat1') is True
   kat = ET.parse(str(questions_file)).find('.//kategoria[@id="kat1"]')
   assert kat is not None
   assert kat.get('deprecated') is None

def test_restore_category_nenajde(questions_file):
   assert restore_category('neexistuje') is False


# --- restore_question ---

def test_restore_question_odstrani_deprecated(questions_file, tests_file):
   delete_question('otq1')
   otazka = ET.parse(str(questions_file)).find('.//otazka[@id="otq1"]')
   assert otazka is not None
   assert otazka.get('deprecated') == '1'
   assert restore_question('otq1') is True
   otazka = ET.parse(str(questions_file)).find('.//otazka[@id="otq1"]')
   assert otazka is not None
   assert otazka.get('deprecated') is None

def test_restore_question_nenajde(questions_file):
   assert restore_question('neexistuje') is False


# --- napoveda_key a markup v odpovediach ---

def test_update_question_odpovede_zachova_markup(questions_file):
   nove = [{'text': 'X <bold>tučné</bold>', 'spravna': '1'}]
   update_question('otq1', {'odpovede': nove})
   odpoved = ET.parse(str(questions_file)).find('.//otazka[@id="otq1"]/odpoved')
   assert odpoved is not None
   assert odpoved.text == 'X '
   bold = odpoved.find('bold')
   assert bold is not None
   assert bold.text == 'tučné'

def test_update_question_odpovede_napoveda_key_a_napoveda_elementy(questions_file):
   nove = [{'text': 'X', 'spravna': '1', 'napovedy': ['Prvá', 'Druhá']}, {'text': 'Y', 'spravna': '0'}]
   update_question('otq1', {'odpovede': nove})
   otazka = ET.parse(str(questions_file)).find('.//otazka[@id="otq1"]')
   assert otazka is not None
   odpovede = otazka.findall('odpoved')
   kluc = odpovede[0].get('napoveda_key')
   assert kluc is not None
   assert odpovede[1].get('napoveda_key') is None
   napovedy = [n.text for n in otazka.findall('napoveda') if n.get('pre') == kluc]
   assert napovedy == ['Prvá', 'Druhá']

def test_update_question_napovede_celoplosne(questions_file):
   update_question('otq1', {'napovede': ['Vždy platná']})
   otazka = ET.parse(str(questions_file)).find('.//otazka[@id="otq1"]')
   assert otazka is not None
   napovedy = [n.text for n in otazka.findall('napoveda') if 'pre' not in n.attrib]
   assert napovedy == ['Vždy platná']

@pytest.mark.parametrize('text, ocakavany', [
   ('rmdir ./a', 'rmdir ./a'),
   ('\n   rmdir ./a\n   ', 'rmdir ./a'),
   ('riadok1\n            riadok2\n            riadok3', 'riadok1\nriadok2\nriadok3'),
   ('\n      def f():\n         return 1\n   ', 'def f():\n   return 1'),
   ('if x:\n            y\n         z', 'if x:\n   y\nz'),
   ('a\n\n      b', 'a\n\nb'),
])
def test_normalizuj_vzor_odstrani_odsadenie_z_xml(text, ocakavany):
   assert normalizuj_vzor(text) == ocakavany

def test_update_question_vzory_nahradi_vsetky(questions_file):
   update_question('otq1', {'vzory': ['a', 'b']})
   update_question('otq1', {'vzory': ['rmdir ./x', 'prvý\ndruhý']})
   otazka = ET.parse(str(questions_file)).find('.//otazka[@id="otq1"]')
   assert otazka is not None
   assert [v.text for v in otazka.findall('vzor')] == ['rmdir ./x', 'prvý\ndruhý']

def test_add_question_napovede_a_odpoved_napoveda(questions_file):
   nova = {
      'znenie': '<znenie>Q?</znenie>',
      'odpovede': [{'text': 'A', 'spravna': '1', 'napovedy': ['nápoveda k A']}],
      'napovede': ['celoplošná'],
   }
   qid, ok = add_question('kat1', nova)
   assert ok is True
   otazka = ET.parse(str(questions_file)).find(f'.//otazka[@id="{qid}"]')
   assert otazka is not None
   odpoved = otazka.find('odpoved')
   assert odpoved is not None
   kluc = odpoved.get('napoveda_key')
   assert kluc is not None
   napovedy = {n.get('pre'): n.text for n in otazka.findall('napoveda')}
   assert napovedy[kluc] == 'nápoveda k A'
   assert napovedy[None] == 'celoplošná'


# --- fork_question ---

def test_fork_question_stara_deprecated_nova_nezavisla(questions_file, tests_file):
   nova_data = {
      'znenie': '<znenie>Opravené znenie</znenie>',
      'body': '3',
      'odpovede': [{'text': 'nová', 'spravna': '1'}],
   }
   nova_id = fork_question('otq1', nova_data)
   assert nova_id is not None
   assert nova_id != 'otq1'
   tree = ET.parse(str(questions_file))
   stara = tree.find('.//otazka[@id="otq1"]')
   assert stara is not None
   assert stara.get('deprecated') == '1'
   assert stara.get('nahrada_za') is None
   assert stara.get('autor') is None
   nova = tree.find(f'.//otazka[@id="{nova_id}"]')
   assert nova is not None
   assert nova.get('nahrada_za') is None
   assert nova.get('autor') is None
   assert nova.get('body') == '3'
   znenie = nova.find('znenie')
   assert znenie is not None
   assert znenie.text == 'Opravené znenie'

def test_fork_question_nenajde(questions_file):
   assert fork_question('neexistuje', {'znenie': '<znenie>x</znenie>'}) is None


# --- zmenene_zamrznute_polia ---

def test_zmenene_zamrznute_polia_bez_zmeny(questions_file):
   otazka = ET.parse(str(questions_file)).find('.//otazka[@id="otq1"]')
   assert otazka is not None
   data = {
      'znenie': '<znenie>Koľko je 2+2?</znenie>',
      'body': '1',
      'odpovede': [{'text': '4', 'spravna': '1'}, {'text': '3', 'spravna': '0'}],
   }
   assert zmenene_zamrznute_polia(otazka, data) is False

def test_zmenene_zamrznute_polia_zmena_znenia(questions_file):
   otazka = ET.parse(str(questions_file)).find('.//otazka[@id="otq1"]')
   assert otazka is not None
   data = {'znenie': '<znenie>Iné znenie</znenie>'}
   assert zmenene_zamrznute_polia(otazka, data) is True

def test_zmenene_zamrznute_polia_len_vzor_bez_zmeny_frozen(questions_file):
   otazka = ET.parse(str(questions_file)).find('.//otazka[@id="otq1"]')
   assert otazka is not None
   data = {'vzory': ['nový vzor']}
   assert zmenene_zamrznute_polia(otazka, data) is False


# --- xslt_to_pdf ---

def _pdf_stylesheet(tmp_path):
   xsl = tmp_path / 'minimal.xsl'
   xsl.write_text('<xsl:stylesheet version="3.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"><xsl:template match="/"><x/></xsl:template></xsl:stylesheet>', encoding='utf-8')
   zdroj = tmp_path / 'zdroj.xml'
   zdroj.write_text('<a/>', encoding='utf-8')
   return str(xsl), str(zdroj)

def test_xslt_to_pdf_fop_dostane_timeout_a_fo_sa_zmaze(tmp_path, monkeypatch):
   import os
   import tempfile
   import subprocess
   from saxonche import PySaxonProcessor
   from app import utils
   tmp = tmp_path / 'tmp'
   tmp.mkdir()
   monkeypatch.setattr(tempfile, 'tempdir', str(tmp))
   volania = []
   monkeypatch.setattr(utils.subprocess, 'run', lambda prikaz, **kw: volania.append(kw))
   xsl, zdroj = _pdf_stylesheet(tmp_path)
   with PySaxonProcessor(license=False) as proc:
      pdf = utils.xslt_to_pdf(proc, xsl, source_file=zdroj)
   assert volania[0]['timeout'] == utils.FOP_TIMEOUT
   assert [p.suffix for p in tmp.iterdir()] == ['.pdf'] and os.path.exists(pdf.name)

@pytest.mark.parametrize('chyba', ['CalledProcessError', 'TimeoutExpired'])
def test_xslt_to_pdf_pri_chybe_fop_nezostanu_docasne_subory(tmp_path, monkeypatch, chyba):
   import tempfile
   import subprocess
   from saxonche import PySaxonProcessor
   from app import utils
   tmp = tmp_path / 'tmp'
   tmp.mkdir()
   monkeypatch.setattr(tempfile, 'tempdir', str(tmp))

   def zlyhaj(prikaz, **kw):
      raise subprocess.CalledProcessError(1, prikaz) if chyba == 'CalledProcessError' else subprocess.TimeoutExpired(prikaz, 1)

   monkeypatch.setattr(utils.subprocess, 'run', zlyhaj)
   xsl, zdroj = _pdf_stylesheet(tmp_path)
   with PySaxonProcessor(license=False) as proc:
      with pytest.raises(subprocess.SubprocessError):
         utils.xslt_to_pdf(proc, xsl, source_file=zdroj)
   assert list(tmp.iterdir()) == []


# --- negativna cache hladania testov ---

class _ProcSpy:
   """Obali PySaxonProcessor a pamata, ktore subory sa naparsovali."""
   def __init__(self, proc):
      self._proc = proc
      self.parsovane: list[str] = []

   def parse_xml(self, **kwargs):
      self.parsovane.append(str(kwargs.get('xml_file_name')))
      return self._proc.parse_xml(**kwargs)

   def __getattr__(self, nazov):
      return getattr(self._proc, nazov)

def _dalsi_subor(tmp_path, kluc, nazov='MAT_1B_kap1.xml'):
   cesta = tmp_path / 'res/xml/tests' / PREDMET / nazov
   cesta.write_text(TESTS_XML.replace('ABC123', kluc), encoding='utf-8')
   return cesta

def test_find_test_nenajdeny_kluc_sa_pri_nezmenenych_suboroch_nehlada_znova(tests_file):
   from saxonche import PySaxonProcessor
   from app.utils import find_test
   with PySaxonProcessor(license=False) as proc:
      spy, cache = _ProcSpy(proc), {}
      assert find_test(spy, 'NIE', True, cache) is None  # type: ignore[arg-type]
      prvy = len(spy.parsovane)
      assert prvy > 0
      assert find_test(spy, 'NIE', True, cache) is None  # type: ignore[arg-type]
      assert find_test(spy, 'NIE', True, cache) is None  # type: ignore[arg-type]
      assert len(spy.parsovane) == prvy

def test_find_test_novy_subor_zrusi_negativnu_cache(tests_file, tmp_path):
   from saxonche import PySaxonProcessor
   from app.utils import find_test
   with PySaxonProcessor(license=False) as proc:
      cache: dict = {}
      assert find_test(proc, 'NOVY', True, cache) is None
      _dalsi_subor(tmp_path, 'NOVY')  # napr. ucitel prave vytvoril sadu testov
      assert find_test(proc, 'NOVY', True, cache) is not None

def test_find_test_zmena_existujuceho_suboru_zrusi_negativnu_cache(tests_file):
   from saxonche import PySaxonProcessor
   from app.utils import find_test
   with PySaxonProcessor(license=False) as proc:
      cache: dict = {}
      assert find_test(proc, 'NOVY', True, cache) is None
      tests_file.write_text(TESTS_XML.replace('</testy>', '   <test id="NOVY"><otazka id="otq2"/></test>\n</testy>'), encoding='utf-8')
      assert find_test(proc, 'NOVY', True, cache) is not None

def test_find_test_file_nenajdeny_kluc_sa_nehlada_znova(tests_file, tmp_path, monkeypatch):
   import app.utils as utils
   cache: dict = {}
   assert find_test_file('NIE', cache) is None
   parsovane: list = []
   povodny = utils.ET.parse
   monkeypatch.setattr(utils.ET, 'parse', lambda *a, **k: parsovane.append(a) or povodny(*a, **k))
   assert find_test_file('NIE', cache) is None
   assert parsovane == []
   _dalsi_subor(tmp_path, 'NIE')
   assert find_test_file('NIE', cache) is not None

@pytest.mark.parametrize('kluc', ['__hot__', '__chyba__'])
def test_rezervovany_kluc_cache_nie_je_kluc_testu(tests_file, kluc):
   from saxonche import PySaxonProcessor
   from app.utils import find_test
   cache = {'__hot__': str(tests_file), '__chyba__': {'x': 1}}
   assert find_test_file(kluc, cache) is None
   with PySaxonProcessor(license=False) as proc:
      assert find_test(proc, kluc, True, cache) is None
   assert cache['__chyba__'] == {'x': 1}  # lookup ju nesmie zmazat

def test_negativna_cache_je_obmedzena_a_dlhe_kluce_nepamata(tests_file, monkeypatch):
   import app.utils as utils
   monkeypatch.setattr(utils, '_NENAJDENE_MAX', 5)
   cache: dict = {}
   for i in range(12):
      find_test_file(f'NIE{i}', cache)
   assert 1 <= len(cache['__chyba__']) <= 5
   dlhe: dict = {}
   find_test_file('x' * 101, dlhe)
   assert dlhe.get('__chyba__', {}) == {}


# --- pouzite_otazky: jeden prechod ---

def test_pouzite_otazky_zjednoti_vsetky_subory(tests_file, tmp_path):
   from app.utils import pouzite_otazky
   (tmp_path / 'res/xml/tests' / PREDMET / 'MAT_1B_kap1.xml').write_text('<testy><test id="X"><otazka id="otq9"/><otazka id="otq1"/></test></testy>', encoding='utf-8')
   (tmp_path / 'res/xml/tests' / PREDMET / 'rozbite.xml').write_text('<testy><test', encoding='utf-8')
   assert pouzite_otazky() == {'otq1', 'otq9'}

def test_delete_chapter_cita_tests_len_raz_nie_pre_kazdu_otazku(questions_file, tmp_path, monkeypatch):
   import app.utils as utils
   for i in range(3):
      (tmp_path / 'res/xml/tests' / PREDMET / f'MAT_{i}_kap9.xml').write_text('<testy><test id="X"><otazka id="ina"/></test></testy>', encoding='utf-8')
   cesty: list[str] = []
   povodny = utils.ET.parse
   monkeypatch.setattr(utils.ET, 'parse', lambda zdroj, *a, **k: cesty.append(str(zdroj)) or povodny(zdroj, *a, **k))
   assert delete_chapter('kap1', PREDMET) is True
   assert len([c for c in cesty if '/tests/' in c]) == 3  # kapitola ma 2 otazky, ale kazdy tests subor sa precita raz


# --- find_test: nenacitatelny subor sa zaloguje ---

def test_find_test_nenacitatelny_subor_sa_zaloguje_cez_logger_nie_print(tests_file, tmp_path, caplog, capsys):
   from saxonche import PySaxonProcessor
   from app.utils import find_test
   (tmp_path / 'res/xml/tests' / PREDMET / 'rozbite.xml').write_text('<testy><test', encoding='utf-8')
   with PySaxonProcessor(license=False) as proc, caplog.at_level(logging.WARNING, logger='pisomky'):
      assert find_test(proc, 'NIE', True, {}) is None
   assert 'chyba parsexml' in caplog.text and 'rozbite.xml' in caplog.text
   assert 'chyba parsexml' not in capsys.readouterr().out


# --- miesto na dopisanie v tlacenom teste ---

MIESTO_OTAZKA = {'znenie': '<znenie>Napíš postup</znenie>', 'body': '2', 'odpovede': []}

def _otazka_v_banke(questions_file, otazka_id):
   el = ET.parse(str(questions_file)).find(f'.//otazka[@id="{otazka_id}"]')
   assert el is not None
   return el

@pytest.mark.parametrize('vstup, vysledok', [(None, None), ('', None), ('  ', None), ('1', '1'), (' 07 ', '7'), ('30', '30')])
def test_over_miesto_platne_hodnoty(vstup, vysledok):
   from app.utils import over_miesto
   assert over_miesto(vstup) == vysledok

@pytest.mark.parametrize('vstup', ['0', '31', '-2', '2.5', 'abc', '1_0', '٣', '1e1', '3\n3'])
def test_over_miesto_neplatne_hodnoty(vstup):
   from app.utils import over_miesto
   with pytest.raises(ValueError, match='1 do 30'):
      over_miesto(vstup)

def test_add_question_s_miestom(questions_file):
   nova_id, ok = add_question('kat1', {**MIESTO_OTAZKA, 'miesto': '4'})
   assert ok
   otazka = _otazka_v_banke(questions_file, nova_id)
   assert [c.tag for c in otazka][:2] == ['znenie', 'miesto']
   assert otazka.find('miesto').get('riadky') == '4'  # type: ignore[union-attr]

def test_add_question_bez_miesta_ho_nema(questions_file):
   nova_id, _ = add_question('kat1', {**MIESTO_OTAZKA, 'miesto': ''})
   assert _otazka_v_banke(questions_file, nova_id).find('miesto') is None

def test_update_question_prida_zmeni_a_odstrani_miesto(questions_file):
   update_question('otq1', {'miesto': '2'})
   assert [m.get('riadky') for m in _otazka_v_banke(questions_file, 'otq1').findall('miesto')] == ['2']
   update_question('otq1', {'miesto': '5'})
   assert [m.get('riadky') for m in _otazka_v_banke(questions_file, 'otq1').findall('miesto')] == ['5']     # nahradene, nie zdvojene
   update_question('otq1', {'miesto': ''})
   assert _otazka_v_banke(questions_file, 'otq1').find('miesto') is None

def test_update_question_bez_kluca_miesto_nemeni(questions_file):
   update_question('otq1', {'miesto': '2'})
   update_question('otq1', {'body': '5'})
   assert _otazka_v_banke(questions_file, 'otq1').find('miesto').get('riadky') == '2'  # type: ignore[union-attr]

def test_update_question_miesto_ide_za_tabulku(questions_file):
   tabulka = '<tabulka><riadok><bunka odpoved="1"/></riadok></tabulka>'
   update_question('otq1', {'odpovede': [], 'tabulka': tabulka, 'miesto': '2'})
   assert [c.tag for c in _otazka_v_banke(questions_file, 'otq1')][:3] == ['znenie', 'tabulka', 'miesto']

def test_update_question_neplatne_miesto_nic_nezapise(questions_file):
   povodny = questions_file.read_text(encoding='utf-8')
   with pytest.raises(ValueError):
      update_question('otq1', {'miesto': '99'})
   assert questions_file.read_text(encoding='utf-8') == povodny

def test_zmena_miesta_nie_je_zmena_zamrznutych_poli(questions_file):
   from app.utils import zmenene_zamrznute_polia
   update_question('otq1', {'miesto': '2'})
   assert zmenene_zamrznute_polia(_otazka_v_banke(questions_file, 'otq1'), {'miesto': '9'}) is False

def test_fork_question_prevezme_miesto_zo_starej_otazky_ak_formular_nema_pole(questions_file):
   update_question('otq1', {'miesto': '3'})
   nova_id = fork_question('otq1', {'znenie': '<znenie>Iné</znenie>', 'body': '1', 'odpovede': []})
   assert _otazka_v_banke(questions_file, nova_id).find('miesto').get('riadky') == '3'  # type: ignore[union-attr,index]

def test_fork_question_pouzije_miesto_z_formulara_aj_prazdne(questions_file):
   update_question('otq1', {'miesto': '3'})
   nova_id = fork_question('otq1', {'znenie': '<znenie>Iné</znenie>', 'body': '1', 'odpovede': [], 'miesto': '6'})
   assert _otazka_v_banke(questions_file, nova_id).find('miesto').get('riadky') == '6'  # type: ignore[union-attr,index]
   assert nova_id is not None
   dalsia = fork_question(nova_id, {'znenie': '<znenie>Iné 2</znenie>', 'body': '1', 'odpovede': [], 'miesto': ''})
   assert _otazka_v_banke(questions_file, dalsia).find('miesto') is None  # type: ignore[arg-type]

def test_riadky_miesta_chybajuci_atribut_je_jeden():
   from app.utils import riadky_miesta
   assert riadky_miesta(ET.fromstring('<otazka><miesto/></otazka>')) == '1'
   assert riadky_miesta(ET.fromstring('<otazka><miesto riadky="4"/></otazka>')) == '4'
   assert riadky_miesta(ET.fromstring('<otazka/>')) is None
