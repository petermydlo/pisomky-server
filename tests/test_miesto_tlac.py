# -*- coding: utf-8 -*-
"""Miesto na dopísanie odpovede v tlačenom teste: schéma (questions.xsd, tests.xsd) a výstup downloadtests.xsl,
vrátane skutočného PDF z FOP (vzdialenosť otázok na strane)."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import xmlschema
from saxonche import PySaxonProcessor

PROJECT_ROOT = Path(__file__).parent.parent
XSD_DIR = PROJECT_ROOT / 'res/xsd'

QUESTIONS = """<kapitola predmet="MAT" id="k">
   <kategoria id="c1" pocet="1">
      <otazka id="o1"><znenie>x</znenie>{miesto}</otazka>
   </kategoria>
</kapitola>"""

TESTS = """<testy predmet="MAT" trieda="1A" skupina="" kapitola="k" fileid="ab12" gendat="2026-01-01T00:00:00">
   <test id="K1">
      <otazka id="o1" body="1"><znenie>x</znenie>{obsah}</otazka>
   </test>
</testy>"""

# 4 otvorene otazky: 3 riadky miesta, ziadne miesto, miesto bez atributu (= 1 riadok), ziadne miesto
TLAC_XML = """<?xml version="1.0" encoding="UTF-8"?>
<testy predmet="MAT" trieda="1A" skupina="" kapitola="k" fileid="ab12">
   <test id="K1">
      <otazka id="o1" body="1"><znenie>AAA prva s miestom na tri riadky</znenie><miesto riadky="3"/></otazka>
      <otazka id="o2" body="1"><znenie>BBB druha bez miesta</znenie></otazka>
      <otazka id="o3" body="1"><znenie>CCC tretia s miestom bez atributu</znenie><miesto/></otazka>
      <otazka id="o4" body="1"><znenie>DDD stvrta bez miesta</znenie></otazka>
   </test>
</testy>
"""


@pytest.fixture(scope='module')
def schema_otazok():
   return xmlschema.XMLSchema11(str(XSD_DIR / 'questions.xsd'))


@pytest.fixture(scope='module')
def schema_testov():
   return xmlschema.XMLSchema11(str(XSD_DIR / 'tests.xsd'))


@pytest.mark.parametrize('miesto', ['<miesto/>', '<miesto riadky="1"/>', '<miesto riadky="30"/>'])
def test_schema_otazok_prijme_platne_miesto(schema_otazok, miesto):
   assert schema_otazok.is_valid(QUESTIONS.format(miesto=miesto))


@pytest.mark.parametrize('miesto', ['<miesto riadky="0"/>', '<miesto riadky="31"/>', '<miesto riadky="x"/>', '<miesto riadky="2.5"/>', '<miesto cislo="2"/>'])
def test_schema_otazok_odmietne_neplatne_miesto(schema_otazok, miesto):
   assert not schema_otazok.is_valid(QUESTIONS.format(miesto=miesto))


@pytest.mark.parametrize('obsah, platne', [
   ('<odpoved spravna="1">a</odpoved><miesto riadky="2"/>', True),
   ('<miesto riadky="2"/>', True),
   ('<miesto riadky="31"/>', False),
   ('<miesto riadky="2"/><odpoved spravna="1">a</odpoved>', False),     # poradie ako v ostatnych castiach testu: znenie, odpovede, tabulka, miesto
])
def test_schema_testov_miesto_za_odpovedami(schema_testov, obsah, platne):
   assert schema_testov.is_valid(TESTS.format(obsah=obsah)) is platne


def _fo(tmp_path):
   zdroj = tmp_path / 't.xml'
   zdroj.write_text(TLAC_XML, encoding='utf-8')
   (tmp_path / 'qr').mkdir()
   (tmp_path / 'qr/K1.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>', encoding='utf-8')
   fo = tmp_path / 't.fo'
   with PySaxonProcessor(license=False) as proc:
      xsl = proc.new_xslt30_processor().compile_stylesheet(stylesheet_file=str(PROJECT_ROOT / 'res/xslt/downloadtests.xsl'))
      xsl.set_parameter('qrdir', proc.make_string_value(f'file://{tmp_path}/qr'))
      xsl.transform_to_file(source_file=str(zdroj), output_file=str(fo))
   return fo


def test_downloadtests_vykresli_miesto_s_poctom_riadkov_po_30_pt(tmp_path):
   fo = _fo(tmp_path).read_text(encoding='utf-8')
   assert re.findall(r'<fo:table-row[^>]* height="(\d+)pt"', fo) == ['90', '30']     # o1 (3 riadky) a o3 (bez atributu = 1 riadok)
   assert fo.count('<fo:block margin-bottom="0.5cm"/>') == 2                          # bezny odstup maju len o2 a o4, nie otazky s miestom


@pytest.mark.skipif(shutil.which('fop') is None, reason='FOP nie je nainstalovany')
def test_miesto_sa_v_pdf_prejavi_ako_odstup_medzi_otazkami(tmp_path):
   pymupdf = pytest.importorskip('pymupdf')
   fo = _fo(tmp_path)
   pdf = tmp_path / 't.pdf'
   subprocess.run(['fop', '-nocs', '-c', str(PROJECT_ROOT / 'res/config.xml'), '-fo', str(fo), '-pdf', str(pdf)], check=True, capture_output=True, cwd=PROJECT_ROOT)
   y = {w[4]: w[1] for w in pymupdf.open(str(pdf))[0].get_text('words') if w[4] in ('AAA', 'BBB', 'CCC', 'DDD')}
   zaklad = y['CCC'] - y['BBB']              # otazka bez miesta: riadok + odstup 0,5 cm
   assert y['BBB'] - y['AAA'] - zaklad == pytest.approx(90 - 14.2, abs=2)      # 3 riadky miesta namiesto odstupu
   assert y['DDD'] - y['CCC'] - zaklad == pytest.approx(30 - 14.2, abs=2)      # 1 riadok
