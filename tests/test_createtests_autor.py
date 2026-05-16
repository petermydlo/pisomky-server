# -*- coding: utf-8 -*-
"""
Testy pre filtrovanie kategórií a otázok podľa @autor v createtests.xsl.
"""

import pytest
import lxml.etree as ET
from pathlib import Path
from saxonche import PySaxonProcessor

STYLESHEET = './res/xslt/createtests.xsl'

# Roster so jedným žiakom
TRIEDY_XML = """\
<?xml version='1.1' encoding='UTF-8'?>
<triedy>
   <trieda id="III.T">
      <student meno="Ján" priezvisko="Vzorný"/>
   </trieda>
</triedy>
"""

# Otázky: spoločná kategória kat-spolocna, Novákova náhrada kat-novak,
# Mydlova vlastná kat-mydlo, a v spoločnej kategórii aj náhrada jednej otázky.
QUESTIONS_XML = """\
<?xml version='1.1' encoding='UTF-8'?>
<kapitola predmet="TST" id="01" nazov="Test">
   <kategoria id="kat-spolocna" pocet="1">
      <otazka id="q-spolocna-1">
         <znenie>Spoločná otázka 1</znenie>
         <odpoved spravna="1">A</odpoved>
         <odpoved spravna="0">B</odpoved>
      </otazka>
      <otazka id="q-spolocna-2">
         <znenie>Spoločná otázka 2 (nahradená Novákom)</znenie>
         <odpoved spravna="1">C</odpoved>
         <odpoved spravna="0">D</odpoved>
      </otazka>
      <otazka id="q-nahrada-novak" autor="novak" nahrada_za="q-spolocna-2">
         <znenie>Novákova náhrada otázky 2</znenie>
         <odpoved spravna="1">E</odpoved>
         <odpoved spravna="0">F</odpoved>
      </otazka>
   </kategoria>
   <kategoria id="kat-novak" autor="novak" nahrada_za="kat-spolocna" pocet="1">
      <otazka id="q-novak-1">
         <znenie>Novákova kategória, otázka 1</znenie>
         <odpoved spravna="1">G</odpoved>
         <odpoved spravna="0">H</odpoved>
      </otazka>
   </kategoria>
   <kategoria id="kat-mydlo" autor="mydlo" pocet="1">
      <otazka id="q-mydlo-1">
         <znenie>Mydlova vlastná otázka</znenie>
         <odpoved spravna="1">I</odpoved>
         <odpoved spravna="0">J</odpoved>
      </otazka>
   </kategoria>
</kapitola>
"""


PROJECT_ROOT = Path(__file__).parent.parent
QUESTIONS_FILE = PROJECT_ROOT / 'res/xml/questions/TST/TST_01.xml'


@pytest.fixture(scope='module')
def proc():
   with PySaxonProcessor(license=False) as p:
      yield p


@pytest.fixture(autouse=True)
def questions_file():
   QUESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
   QUESTIONS_FILE.write_text(QUESTIONS_XML, encoding='utf-8')
   yield
   QUESTIONS_FILE.unlink(missing_ok=True)
   try:
      QUESTIONS_FILE.parent.rmdir()
   except OSError:
      pass


def run_xslt(proc, autor):
   """Spustí createtests.xsl a vráti zoznam id otázok vygenerovaného testu."""
   xsltproc = proc.new_xslt30_processor()
   xsltproc.set_parameter('seed_ext', proc.make_string_value('testseed'))
   xsltproc.set_parameter('predmet', proc.make_string_value('TST'))
   xsltproc.set_parameter('trieda', proc.make_string_value('III.T'))
   xsltproc.set_parameter('skupina', proc.make_string_value(''))
   xsltproc.set_parameter('kapitola', proc.make_string_value('01'))
   xsltproc.set_parameter('start', proc.make_string_value(''))
   xsltproc.set_parameter('stop', proc.make_string_value(''))
   xsltproc.set_parameter('anonymne', proc.make_boolean_value(False))
   xsltproc.set_parameter('identita', proc.make_boolean_value(False))
   xsltproc.set_parameter('fileid', proc.make_string_value('test'))
   xsltproc.set_parameter('autor', proc.make_string_value(autor))

   xsltproc.set_cwd(str(PROJECT_ROOT))
   executable = xsltproc.compile_stylesheet(stylesheet_file=STYLESHEET)
   node = proc.parse_xml(xml_text=TRIEDY_XML)
   result_str = executable.transform_to_string(xdm_node=node)
   tree = ET.fromstring(result_str.encode())
   return [o.get('id') for o in tree.findall('.//otazka')]


def test_novak_dostane_svoju_kategoriu_namiesto_spolocnej(proc):
   """Novák má @nahrada_za na kat-spolocna — dostane kat-novak, nie kat-spolocna."""
   ids = run_xslt(proc, 'novak')
   assert 'q-novak-1' in ids
   assert 'q-spolocna-1' not in ids
   assert 'q-spolocna-2' not in ids


def test_novak_nedostane_mydlovu_kategoriu(proc):
   ids = run_xslt(proc, 'novak')
   assert 'q-mydlo-1' not in ids


def test_mydlo_dostane_spolocnu_kategoriu(proc):
   """Mydlo nemá náhradu kat-spolocna — dostane ju pôvodnú."""
   ids = run_xslt(proc, 'mydlo')
   assert 'q-spolocna-1' in ids or 'q-spolocna-2' in ids


def test_mydlo_nedostane_novakovu_kategoriu(proc):
   ids = run_xslt(proc, 'mydlo')
   assert 'q-novak-1' not in ids


def test_mydlo_dostane_vlastnu_kategoriu(proc):
   ids = run_xslt(proc, 'mydlo')
   assert 'q-mydlo-1' in ids


def test_mydlo_nedostane_novakovu_nahradnu_otazku(proc):
   """q-nahrada-novak patrí Novákovi — Mydlo ju nesmie dostať."""
   ids = run_xslt(proc, 'mydlo')
   assert 'q-nahrada-novak' not in ids


def test_novak_dostane_nahradnu_otazku_namiesto_spolocnej_2(proc):
   """
   Novák má náhradu q-spolocna-2 → dostane q-nahrada-novak namiesto nej.
   Keďže kat-spolocna je celá nahradená kat-novak, tento test overuje
   že Novák nedostane q-spolocna-2 ani cez náhradnú kategóriu.
   """
   ids = run_xslt(proc, 'novak')
   assert 'q-spolocna-2' not in ids
   assert 'q-nahrada-novak' not in ids  # je v kat-spolocna ktorú novak nezdedí
