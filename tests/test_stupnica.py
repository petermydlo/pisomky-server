# -*- coding: utf-8 -*-
"""
Testy hodnotiacej stupnice (testy/@stupnica): score.xq berie hranice zo scales.xml podla stupnice testu,
chybajuci atribut = default.
"""

import shutil
from pathlib import Path

import pytest
from saxonche import PySaxonProcessor

from app.utils import xquery_to_string

PROJECT_ROOT = Path(__file__).parent.parent
PREDMET = 'TSTSTUP'
TESTY_DIR = PROJECT_ROOT / 'res/xml/tests' / PREDMET
ANSWERS_DIR = PROJECT_ROOT / 'res/xml/answers' / PREDMET


@pytest.fixture(scope='module')
def proc():
   with PySaxonProcessor(license=False) as p:
      yield p


@pytest.fixture(autouse=True)
def cistenie():
   yield
   shutil.rmtree(TESTY_DIR, ignore_errors=True)
   shutil.rmtree(ANSWERS_DIR, ignore_errors=True)


def _zapis(atribut: str) -> None:
   TESTY_DIR.mkdir(parents=True, exist_ok=True)
   ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
   (TESTY_DIR / 't.xml').write_text(
      f'<testy predmet="{PREDMET}" trieda="X" skupina="" kapitola="01" gendat="2026-01-01T00:00:00"{atribut}>'
      '<test id="k1"><otazka id="o1" body="75"><odpoved spravna="1"/></otazka>'
      '<otazka id="o2" body="25"><odpoved spravna="1"/></otazka></test></testy>'
   )
   # 75 z 100 bodov: o1 spravne, o2 nespravne
   (ANSWERS_DIR / 't.xml').write_text('<testy><test id="k1"><otazka id="o1">a</otazka><otazka id="o2">b</otazka></test></testy>')


def _znamka(proc, atribut: str) -> str:
   _zapis(atribut)
   params = {'kluc': 'k1', 'test_cesta': f'../xml/tests/{PREDMET}/t.xml', 'answer_cesta': f'../xml/answers/{PREDMET}/t.xml'}
   vysledok = xquery_to_string(proc, './res/xquery/score.xq', params=params)
   return vysledok.split('znamka="')[1].split('"')[0]


def test_default_bez_atributu(proc):
   assert _znamka(proc, '') == '2'


def test_default_explicitne(proc):
   assert _znamka(proc, ' stupnica="default"') == '2'


def test_prisna(proc):
   assert _znamka(proc, ' stupnica="prisna"') == '3'


def test_neznama_stupnica_je_default(proc):
   assert _znamka(proc, ' stupnica="neexistuje"') == '2'


def test_stupnicatext(proc):
   xsltproc = proc.new_xslt30_processor()
   xsltproc.set_cwd(str(PROJECT_ROOT))
   zdroj = proc.parse_xml(xml_text='<testy stupnica="prisna"><test id="k1"/></testy>')
   exe = xsltproc.compile_stylesheet(stylesheet_text='''<xsl:stylesheet version="3.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:my="http://www.spsjm.sk">
<xsl:import href="res/xslt/scale.xsl"/><xsl:output method="text"/>
<xsl:template match="test"><xsl:value-of select="my:stupnicatext(my:stupnica(.))"/></xsl:template></xsl:stylesheet>''')
   text = exe.transform_to_string(xdm_node=zdroj)
   assert text == '\xa0\xa0\xa0'.join(['100%-90%:1', '89%-80%:2', '79%-70%:3', '69%-60%:4', '59%-0%:5'])
