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

# kat-spolocna-a: spoločná, Novák v nej nahrádza jednu otázku (nie celú kategóriu)
# kat-spolocna-b: spoločná, Novák ju nahrádza celou vlastnou kat-novak
# kat-novak: Novákova náhrada kat-spolocna-b
# kat-mydlo: Mydlova vlastná kategória (bez nahrada_za)
QUESTIONS_XML = """\
<?xml version='1.1' encoding='UTF-8'?>
<kapitola predmet="TST" id="01" nazov="Test">
   <kategoria id="kat-spolocna-a" pocet="1">
      <otazka id="q-a-1">
         <znenie>Spoločná A otázka 1</znenie>
         <odpoved spravna="1">A</odpoved>
         <odpoved spravna="0">B</odpoved>
      </otazka>
      <otazka id="q-a-2">
         <znenie>Spoločná A otázka 2 (nahradená Novákom)</znenie>
         <odpoved spravna="1">C</odpoved>
         <odpoved spravna="0">D</odpoved>
      </otazka>
      <otazka id="q-a-nahrada-novak" autor="novak" nahrada_za="q-a-2">
         <znenie>Novákova náhrada otázky q-a-2</znenie>
         <odpoved spravna="1">E</odpoved>
         <odpoved spravna="0">F</odpoved>
      </otazka>
   </kategoria>
   <kategoria id="kat-spolocna-b" pocet="1">
      <otazka id="q-b-1">
         <znenie>Spoločná B otázka 1</znenie>
         <odpoved spravna="1">G</odpoved>
         <odpoved spravna="0">H</odpoved>
      </otazka>
   </kategoria>
   <kategoria id="kat-novak" autor="novak" nahrada_za="kat-spolocna-b" pocet="1">
      <otazka id="q-novak-1">
         <znenie>Novákova náhrada celej kat-spolocna-b</znenie>
         <odpoved spravna="1">I</odpoved>
         <odpoved spravna="0">J</odpoved>
      </otazka>
   </kategoria>
   <kategoria id="kat-mydlo" autor="mydlo" pocet="1">
      <otazka id="q-mydlo-1">
         <znenie>Mydlova vlastná otázka</znenie>
         <odpoved spravna="1">K</odpoved>
         <odpoved spravna="0">L</odpoved>
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


def test_novak_dostane_kat_spolocna_b_nahradenu(proc):
   """Novák má kat-novak s nahrada_za=kat-spolocna-b — dostane kat-novak, nie kat-spolocna-b."""
   ids = run_xslt(proc, 'novak')
   assert 'q-novak-1' in ids
   assert 'q-b-1' not in ids


def test_novak_nedostane_mydlovu_kategoriu(proc):
   ids = run_xslt(proc, 'novak')
   assert 'q-mydlo-1' not in ids


def test_novak_dostane_kat_spolocna_a_s_nahradou_otazky(proc):
   """Novák zdedí kat-spolocna-a, ale q-a-2 mu nahrádza q-a-nahrada-novak."""
   ids = run_xslt(proc, 'novak')
   assert 'q-a-2' not in ids
   assert 'q-a-nahrada-novak' in ids or 'q-a-1' in ids  # pocet=1, jedna z dvoch


def test_novak_nedostane_povodnu_nahradenu_otazku(proc):
   """q-a-2 je nahradená Novákom — Novák ju nesmie dostať."""
   ids = run_xslt(proc, 'novak')
   assert 'q-a-2' not in ids


def test_mydlo_dostane_kat_spolocna_a_bez_nahrad(proc):
   """Mydlo nemá náhrady v kat-spolocna-a — dostane q-a-1 alebo q-a-2, nie Novákovu náhradu."""
   ids = run_xslt(proc, 'mydlo')
   assert 'q-a-nahrada-novak' not in ids
   assert 'q-a-1' in ids or 'q-a-2' in ids


def test_mydlo_dostane_kat_spolocna_b(proc):
   """Mydlo nemá náhradu kat-spolocna-b — dostane ju pôvodnú."""
   ids = run_xslt(proc, 'mydlo')
   assert 'q-b-1' in ids
   assert 'q-novak-1' not in ids


def test_mydlo_dostane_vlastnu_kategoriu(proc):
   ids = run_xslt(proc, 'mydlo')
   assert 'q-mydlo-1' in ids
