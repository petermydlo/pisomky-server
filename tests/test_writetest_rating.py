# -*- coding: utf-8 -*-
"""Formulár žiaka (writetest.xsl) pri hodnotiacich hviezdičkách: po obnovení stránky je zaškrtnutá len uložená odpoveď
práve tej otázky. Šablóny sa kopírujú do tmp, lebo ukladanú odpoveď hľadajú v ../xml/answers vedľa seba."""

import shutil
from pathlib import Path

import lxml.html
import pytest
from saxonche import PySaxonProcessor

from app.utils import xslt_to_string

PROJECT_ROOT = Path(__file__).parent.parent

TESTY_XML = """<?xml version='1.0' encoding='UTF-8'?>
<testy predmet="MAT" trieda="1A" skupina="" kapitola="ka" fileid="ab12">
   <test id="K1">
      <otazka id="r1" rating="1" body="0"><znenie>Prvá</znenie></otazka>
      <otazka id="r2" rating="1" body="0"><znenie>Druhá</znenie></otazka>
      <otazka id="r3" rating="1" body="0"><znenie>Tretia</znenie></otazka>
   </test>
</testy>
"""

ODPOVEDE_XML = """<?xml version='1.0' encoding='UTF-8'?>
<odpovede predmet="MAT" trieda="1A" skupina="" kapitola="ka" fileid="ab12">
   <test id="K1" dat="2026-01-01T10:00:00">
      <otazka id="r1">3</otazka>
      <otazka id="r2">5</otazka>
   </test>
</odpovede>
"""


@pytest.fixture
def html(tmp_path):
   shutil.copytree(PROJECT_ROOT / 'res/xslt', tmp_path / 'res/xslt')
   (tmp_path / 'res/xml/answers/MAT').mkdir(parents=True)
   (tmp_path / 'res/xml/answers/MAT/MAT_1A_ka_ab12.xml').write_text(ODPOVEDE_XML, encoding='utf-8')
   (tmp_path / 'res/xml/lists').mkdir(parents=True)
   shutil.copy(PROJECT_ROOT / 'res/xml/lists/scales.xml', tmp_path / 'res/xml/lists/scales.xml')
   testy = tmp_path / 't.xml'
   testy.write_text(TESTY_XML, encoding='utf-8')
   with PySaxonProcessor(license=False) as proc:
      xp = proc.new_xpath_processor()
      xp.set_context(xdm_item=proc.parse_xml(xml_file_name=str(testy)))
      vysledok = xslt_to_string(
         proc, stylesheet_file=str(tmp_path / 'res/xslt/writetest.xsl'), xdm_node=xp.evaluate_single('/testy/test'),
         params={'admin': False, 'napovedy_zostatok': 3},
      )
   return lxml.html.fromstring(vysledok)


def _zaskrtnute(dokument, otazka_id):
   """Hodnoty zaškrtnutých radií otázky bez skrytého predvoleného '-' (= nezodpovedané)."""
   return [str(v) for v in dokument.xpath('//input[@type="radio"][@name=$n][@checked]/@value', n=otazka_id) if v != '-']


def test_hviezdicky_su_zaskrtnute_podla_odpovede_svojej_otazky(html):
   assert _zaskrtnute(html, 'r1') == ['3']
   assert _zaskrtnute(html, 'r2') == ['5']


def test_nezodpovedana_hviezdickova_otazka_nema_nic_zaskrtnute(html):
   assert _zaskrtnute(html, 'r3') == []
