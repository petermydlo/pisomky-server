# -*- coding: utf-8 -*-

import os
import pytest
import lxml.etree as ET
from pathlib import Path
from filelock import FileLock
from fastapi.exceptions import HTTPException

from app.utils import modify_test_xml, test_xml_path as xml_path
from app.routers.saveanswers import write_answers
from app.routers.savemarks import write_marks
from app.routers.importanswers import write_answers_import, nacitaj_tests_xml, ziskaj_metadata

PREDMET = 'MAT'
TRIEDA = '1A'
SKUPINA = ''
KAPITOLA = 'kap1'
FILEID = 'ab12'
KLUC = 'TEST01'
DAT = '2026-01-01T10:00:00'

ANSWERS_XML = f"""\
<?xml version='1.0' encoding='utf-8'?>
<odpovede xml:lang="sk">
   <test id="{KLUC}" dat="{DAT}">
      <otazka id="q1">a</otazka>
      <otazka id="q2">b</otazka>
   </test>
</odpovede>
"""


TESTS_XML = f"""\
<?xml version='1.0' encoding='utf-8'?>
<testy predmet="{PREDMET}" trieda="{TRIEDA}" skupina="{SKUPINA}" kapitola="{KAPITOLA}" fileid="{FILEID}">
   <test id="{KLUC}">
      <otazka id="q1"/>
   </test>
</testy>
"""


@pytest.fixture(autouse=True)
def workdir(tmp_path, monkeypatch):
   (tmp_path / 'res/xml/answers' / PREDMET).mkdir(parents=True)
   (tmp_path / 'res/xml/tests' / PREDMET).mkdir(parents=True)
   monkeypatch.chdir(tmp_path)


@pytest.fixture
def tests_file(tmp_path):
   cesta = tmp_path / 'res/xml/tests' / PREDMET / f'{PREDMET}_{TRIEDA}{SKUPINA}_{KAPITOLA}_{FILEID}.xml'
   cesta.write_text(TESTS_XML, encoding='utf-8')
   return cesta


@pytest.fixture
def answers_file(tmp_path):
   cesta = tmp_path / 'res/xml/answers' / PREDMET / f'{PREDMET}_{TRIEDA}{SKUPINA}_{KAPITOLA}_{FILEID}.xml'
   cesta.write_text(ANSWERS_XML, encoding='utf-8')
   return cesta


# --- write_answers ---

def test_write_answers_vytvori_subor(tmp_path):
   adresar = f'./res/xml/answers/{PREDMET}'
   cesta = Path(f'{adresar}/{PREDMET}_{TRIEDA}{SKUPINA}_{KAPITOLA}_{FILEID}.xml')
   lock = FileLock(f'{cesta}.lock')
   write_answers(lock, cesta, {'q1': 'a', 'q2': 'b'}, adresar, PREDMET, TRIEDA, SKUPINA, KAPITOLA, FILEID, KLUC)
   assert cesta.exists()
   tree = ET.parse(str(cesta))
   test = tree.find(f'.//test[@id="{KLUC}"]')
   assert test is not None
   assert test.find('otazka[@id="q1"]').text == 'a'
   assert test.find('otazka[@id="q2"]').text == 'b'

def test_write_answers_aktualizuje_existujuci(answers_file):
   adresar = f'./res/xml/answers/{PREDMET}'
   lock = FileLock(f'{answers_file}.lock')
   write_answers(lock, answers_file, {'q1': 'c'}, adresar, PREDMET, TRIEDA, SKUPINA, KAPITOLA, FILEID, KLUC)
   tree = ET.parse(str(answers_file))
   testy = tree.findall(f'.//test[@id="{KLUC}"]')
   assert len(testy) == 1
   assert testy[0].find('otazka[@id="q1"]').text == 'c'

def test_write_answers_bez_odpovedi_aktualizuje_dat(answers_file):
   adresar = f'./res/xml/answers/{PREDMET}'
   lock = FileLock(f'{answers_file}.lock')
   write_answers(lock, answers_file, {}, adresar, PREDMET, TRIEDA, SKUPINA, KAPITOLA, FILEID, KLUC)
   tree = ET.parse(str(answers_file))
   test = tree.find(f'.//test[@id="{KLUC}"]')
   assert test is not None
   assert test.get('dat') != DAT

def test_write_answers_novy_kluc(answers_file):
   adresar = f'./res/xml/answers/{PREDMET}'
   novy_kluc = 'TEST02'
   lock = FileLock(f'{answers_file}.lock')
   write_answers(lock, answers_file, {'q1': 'x'}, adresar, PREDMET, TRIEDA, SKUPINA, KAPITOLA, FILEID, novy_kluc)
   tree = ET.parse(str(answers_file))
   assert tree.find(f'.//test[@id="{KLUC}"]') is not None
   assert tree.find(f'.//test[@id="{novy_kluc}"]') is not None


# --- write_marks ---

def test_write_marks_body(answers_file):
   lock = FileLock(f'{answers_file}.lock')
   write_marks(lock, answers_file, {'h_q1': '1', 'h_q2': '0'}, KLUC, DAT)
   tree = ET.parse(str(answers_file))
   q1 = tree.find(f'.//test[@id="{KLUC}"]/otazka[@id="q1"]')
   assert q1.get('body') == '1'
   q2 = tree.find(f'.//test[@id="{KLUC}"]/otazka[@id="q2"]')
   assert q2.get('body') == '0'

def test_write_marks_koment(answers_file):
   lock = FileLock(f'{answers_file}.lock')
   write_marks(lock, answers_file, {'k_q1': 'Správne'}, KLUC, DAT)
   tree = ET.parse(str(answers_file))
   q1 = tree.find(f'.//test[@id="{KLUC}"]/otazka[@id="q1"]')
   assert q1.get('koment') == 'Správne'

def test_write_marks_bh_typ(answers_file):
   lock = FileLock(f'{answers_file}.lock')
   write_marks(lock, answers_file, {'bh_q1': '2'}, KLUC, DAT)
   tree = ET.parse(str(answers_file))
   q1 = tree.find(f'.//test[@id="{KLUC}"]/otazka[@id="q1"]')
   assert q1.get('body') == '2'

def test_write_marks_neexistujuca_otazka_vytvori_element(answers_file):
   lock = FileLock(f'{answers_file}.lock')
   write_marks(lock, answers_file, {'h_q9': '3'}, KLUC, DAT)
   tree = ET.parse(str(answers_file))
   q9 = tree.find(f'.//test[@id="{KLUC}"]/otazka[@id="q9"]')
   assert q9 is not None
   assert q9.get('body') == '3'


# --- changetime logika ---

def _changetime_modify(tree, kluc, start, stop):
   """Replika _modify closury z changetime.py na priame testovanie."""
   root = tree.getroot()

   def _set_attr(node, attr, value):
      if value is not None:
         if value.strip() != '':
            node.set(attr, value)
         else:
            node.attrib.pop(attr, None)

   if kluc is None:
      _set_attr(root, 'start', start)
      _set_attr(root, 'stop', stop)
   else:
      tests = [t for t in tree.findall('.//test') if t.get('id') == kluc]
      if not tests:
         raise HTTPException(status_code=404, detail='Test nenájdený')
      _set_attr(tests[0], 'start', start)
      _set_attr(tests[0], 'stop', stop)


def test_changetime_skupina_nastavi_start(tests_file):
   modify_test_xml(str(tests_file), lambda t: _changetime_modify(t, None, '2026-01-01T08:00', None))
   root = ET.parse(str(tests_file)).getroot()
   assert root.get('start') == '2026-01-01T08:00'

def test_changetime_skupina_nastavi_stop(tests_file):
   modify_test_xml(str(tests_file), lambda t: _changetime_modify(t, None, None, '2026-01-01T10:00'))
   root = ET.parse(str(tests_file)).getroot()
   assert root.get('stop') == '2026-01-01T10:00'

def test_changetime_skupina_vymaze_atribut(tests_file):
   modify_test_xml(str(tests_file), lambda t: _changetime_modify(t, None, '2026-01-01T08:00', None))
   modify_test_xml(str(tests_file), lambda t: _changetime_modify(t, None, '  ', None))
   root = ET.parse(str(tests_file)).getroot()
   assert root.get('start') is None

def test_changetime_test_nastavi_start(tests_file):
   modify_test_xml(str(tests_file), lambda t: _changetime_modify(t, KLUC, '2026-01-01T09:00', None))
   test = ET.parse(str(tests_file)).find(f'.//test[@id="{KLUC}"]')
   assert test.get('start') == '2026-01-01T09:00'

def test_changetime_test_nenajdeny(tests_file):
   with pytest.raises(HTTPException) as exc:
      modify_test_xml(str(tests_file), lambda t: _changetime_modify(t, 'NEEXISTUJE', '2026-01-01T09:00', None))
   assert exc.value.status_code == 404


# --- stoptime logika ---

def _stoptime_modify(tree, kluc, stop):
   """Replika _modify closury z stoptime.py na priame testovanie."""
   tests = [t for t in tree.findall('.//test') if t.get('id') == kluc]
   if not tests:
      raise HTTPException(status_code=404, detail='Test nenájdený')
   tests[0].set('stop', stop)


def test_stoptime_nastavi_stop(tests_file):
   modify_test_xml(str(tests_file), lambda t: _stoptime_modify(t, KLUC, '2026-01-01T10:00'))
   test = ET.parse(str(tests_file)).find(f'.//test[@id="{KLUC}"]')
   assert test.get('stop') == '2026-01-01T10:00'

def test_stoptime_nenajdeny(tests_file):
   with pytest.raises(HTTPException) as exc:
      modify_test_xml(str(tests_file), lambda t: _stoptime_modify(t, 'NEEXISTUJE', '2026-01-01T10:00'))
   assert exc.value.status_code == 404


# --- deletetests logika ---

def test_deletetests_vymaze_subor(tests_file):
   cesta = str(tests_file)
   assert os.path.exists(cesta)
   os.remove(cesta)
   assert not os.path.exists(cesta)

def test_deletetests_adresar_prazdny_po_vymazani(tests_file):
   adresar = str(tests_file.parent)
   os.remove(str(tests_file))
   assert os.listdir(adresar) == []

def test_deletetests_adresar_neprazdny_po_vymazani(tests_file, tmp_path):
   druhy = tmp_path / 'res/xml/tests' / PREDMET / f'{PREDMET}_1B_kap1_cd34.xml'
   druhy.write_text(TESTS_XML, encoding='utf-8')
   os.remove(str(tests_file))
   assert os.listdir(str(tests_file.parent)) != []


# --- importanswers: write_answers_import ---

def test_write_answers_import_vytvori_subor(tmp_path):
   cesta = tmp_path / 'res/xml/answers' / PREDMET / f'{PREDMET}_{TRIEDA}_{KAPITOLA}_{FILEID}.xml'
   lock = FileLock(f'{cesta}.lock')
   write_answers_import(lock, cesta, {'q1': 'a', 'q2': 'b'}, KLUC)
   assert cesta.exists()
   tree = ET.parse(str(cesta))
   test = tree.find(f'.//test[@id="{KLUC}"]')
   assert test is not None
   assert test.find('otazka[@id="q1"]').text == 'a'

def test_write_answers_import_aktualizuje_existujuci(answers_file):
   lock = FileLock(f'{answers_file}.lock')
   write_answers_import(lock, answers_file, {'q1': 'x'}, KLUC)
   tree = ET.parse(str(answers_file))
   testy = tree.findall(f'.//test[@id="{KLUC}"]')
   assert len(testy) == 1
   assert testy[0].find('otazka[@id="q1"]').text == 'x'

def test_write_answers_import_prida_novu_otazku(answers_file):
   lock = FileLock(f'{answers_file}.lock')
   write_answers_import(lock, answers_file, {'q9': 'c'}, KLUC)
   tree = ET.parse(str(answers_file))
   assert tree.find(f'.//test[@id="{KLUC}"]/otazka[@id="q9"]').text == 'c'

def test_write_answers_import_novy_kluc(answers_file):
   lock = FileLock(f'{answers_file}.lock')
   write_answers_import(lock, answers_file, {'q1': 'a'}, 'TEST99')
   tree = ET.parse(str(answers_file))
   assert tree.find('.//test[@id="TEST99"]') is not None
   assert tree.find(f'.//test[@id="{KLUC}"]') is not None


# --- importanswers: nacitaj_tests_xml ---

def test_nacitaj_tests_xml_najde(tests_file):
   result = nacitaj_tests_xml(str(tests_file), KLUC)
   assert KLUC in result
   assert '<test' in result

def test_nacitaj_tests_xml_nenajde(tests_file):
   result = nacitaj_tests_xml(str(tests_file), 'NEEXISTUJE')
   assert result == ''


# --- importanswers: ziskaj_metadata ---

def test_ziskaj_metadata(tests_file):
   predmet, trieda, skupina, kapitola, fileid = ziskaj_metadata(str(tests_file))
   assert predmet == PREDMET
   assert trieda == TRIEDA
   assert skupina == SKUPINA
   assert kapitola == KAPITOLA
   assert fileid == FILEID

def test_ziskaj_metadata_chybajuce_atributy(tmp_path):
   cesta = tmp_path / 'prazdny.xml'
   cesta.write_text('<?xml version="1.0"?><testy/>', encoding='utf-8')
   predmet, trieda, skupina, kapitola, fileid = ziskaj_metadata(str(cesta))
   assert predmet == ''
   assert fileid == ''
