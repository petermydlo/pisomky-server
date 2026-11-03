# -*- coding: utf-8 -*-
"""
Pohlad zaka na vyhodnoteny test (res/xslt/showresult_student.xsl): MCQ ako u ucitela, otvorene otazky ako text
s komentarom, bez hodnotiaceho formulara a bez spravnej odpovede pri nezvolenych moznostiach inych testov.
"""

import shutil
from pathlib import Path

import pytest
from saxonche import PySaxonProcessor

from app.utils import xslt_to_string

PROJECT_ROOT = Path(__file__).parent.parent
PREDMET = 'TSTODHAL'
TESTY_DIR = PROJECT_ROOT / 'res/xml/tests' / PREDMET
ANSWERS_DIR = PROJECT_ROOT / 'res/xml/answers' / PREDMET

TESTY_XML = f"""<testy xml:lang="sk" predmet="{PREDMET}" trieda="X" skupina="" kapitola="01" fileid="1234" gendat="2026-01-01T00:00:00">
   <test id="k1">
      <otazka id="o1" body="2"><znenie>Zvolena spravne</znenie><odpoved spravna="1">prva</odpoved><odpoved spravna="0">druha</odpoved></otazka>
      <otazka id="o2" body="2"><znenie>Zvolena zle</znenie><odpoved spravna="1">tretia</odpoved><odpoved spravna="0">stvrta</odpoved></otazka>
      <otazka id="o3" body="4"><znenie>Otvorena</znenie></otazka>
      <otazka id="o4" body="4"><znenie>Otvorena neohodnotena</znenie></otazka>
   </test>
</testy>
"""

ANSWERS_XML = """<odpovede>
   <test id="k1" dat="2026-01-02T10:00:00" odhalene="1">
      <otazka id="o1" body="2">a</otazka>
      <otazka id="o2" body="0">b</otazka>
      <otazka id="o3" body="3" koment="Chyba pri prepinaci">ls -l</otazka>
      <otazka id="o4">cat</otazka>
   </test>
</odpovede>
"""


@pytest.fixture(scope='module')
def proc():
   with PySaxonProcessor(license=False) as p:
      yield p


@pytest.fixture(autouse=True)
def cistenie():
   TESTY_DIR.mkdir(parents=True, exist_ok=True)
   ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
   (TESTY_DIR / f'{PREDMET}_X_01_1234.xml').write_text(TESTY_XML, encoding='utf-8')
   (ANSWERS_DIR / f'{PREDMET}_X_01_1234.xml').write_text(ANSWERS_XML, encoding='utf-8')
   yield
   shutil.rmtree(TESTY_DIR, ignore_errors=True)
   shutil.rmtree(ANSWERS_DIR, ignore_errors=True)


@pytest.fixture
def html(proc):
   node = proc.parse_xml(xml_file_name=str(TESTY_DIR / f'{PREDMET}_X_01_1234.xml'))
   xp = proc.new_xpath_processor()
   xp.set_context(xdm_item=node)
   test = next(iter(xp.evaluate('/testy/test')))
   return xslt_to_string(proc, stylesheet_file=str(PROJECT_ROOT / 'res/xslt/showresult_student.xsl'), xdm_node=test)


def test_mcq_zvyraznuje_spravnu_a_zlu_odpoved(html):
   assert 'bold bg-success' in html   # o1: zvolena spravna
   assert 'bold bg-danger' in html    # o2: zvolena nespravna
   assert 'bold bg-warning' in html   # o2: spravna, ktoru zak nezvolil


def test_otvorena_otazka_ma_text_body_a_komentar(html):
   assert 'ls -l' in html
   assert '3/4' in html
   assert 'Chyba pri prepinaci' in html


def test_neohodnotena_otvorena_otazka(html):
   assert 'nehodnotené' in html
   assert 'ešte nie sú ohodnotené' in html


def test_bez_hodnotiaceho_formulara(html):
   assert '<form' not in html
   assert 'savemarks' not in html
   assert '<input' not in html


def test_ma_odkaz_domov(html):
   assert 'href="/"' in html
   assert 'bi-house' in html


def test_celkove_hodnotenie_zahrna_otvorene_otazky(html):
   # MCQ 2 + otvorena 3 = 5 z 12 (o4 nehodnotena); 5/12 = 41 %
   assert 'Hodnotenie: 5/12' in html
   assert '(41%)' in html
