# -*- coding: utf-8 -*-
"""Zvyraznena poznamka <poznamka typ="..."> v head/tail a v zneni otazky: schema, HTML (common_html.xsl) a FO (downloadtests.xsl)."""

import re
from pathlib import Path

import pytest
import xmlschema
from saxonche import PySaxonProcessor

PROJECT_ROOT = Path(__file__).parent.parent
XSD_DIR = PROJECT_ROOT / 'res/xsd'

KAPITOLA = """<kapitola predmet="MAT" id="k">
   <pokyny>
      <head>{head}</head>
      <tail>{tail}</tail>
   </pokyny>
   <kategoria id="c1" pocet="1">
      <otazka id="o1"><znenie>{znenie}</znenie></otazka>
   </kategoria>
</kapitola>"""

TESTY = """<testy predmet="MAT" trieda="1A" skupina="" kapitola="k" fileid="ab12" gendat="2026-01-01T00:00:00">
   <test id="K1">
      <pokyny><head>{head}</head><tail>{tail}</tail></pokyny>
      <otazka id="o1" body="2"><znenie>{znenie}</znenie></otazka>
   </test>
</testy>"""

P = '<poznamka typ="warning">Vždy pracujte v konte <bold>student</bold></poznamka>'


def _kapitola(head='x', tail='y', znenie='z'):
   return KAPITOLA.format(head=head, tail=tail, znenie=znenie)


def _testy(head='x', tail='y', znenie='z'):
   return TESTY.format(head=head, tail=tail, znenie=znenie)


@pytest.fixture(scope='module')
def schema_otazok():
   return xmlschema.XMLSchema11(str(XSD_DIR / 'questions.xsd'))


@pytest.fixture(scope='module')
def schema_testov():
   return xmlschema.XMLSchema11(str(XSD_DIR / 'tests.xsd'))


@pytest.mark.parametrize('typ', ['info', 'warning', 'danger', 'success'])
def test_schema_prijme_vsetky_styri_typy_v_head_tail_aj_zneni(schema_otazok, schema_testov, typ):
   p = f'<poznamka typ="{typ}">text</poznamka>'
   assert schema_otazok.is_valid(_kapitola(head=p, tail=p, znenie=f'a {p}'))
   assert schema_testov.is_valid(_testy(head=p, tail=p, znenie=f'a {p}'))


@pytest.mark.parametrize('p', ['<poznamka typ="nieco">x</poznamka>', '<poznamka>x</poznamka>'])
def test_schema_odmietne_neplatny_alebo_chybajuci_typ(schema_otazok, schema_testov, p):
   assert not schema_otazok.is_valid(_kapitola(head=p))
   assert not schema_testov.is_valid(_testy(znenie=p))


def test_schema_odpoved_poznamku_nepovoluje(schema_otazok):
   zdroj = '<kapitola predmet="MAT" id="k"><kategoria id="c1" pocet="1"><otazka id="o1"><znenie>z</znenie><odpoved spravna="1">a ' + P + '</odpoved></otazka></kategoria></kapitola>'
   assert not schema_otazok.is_valid(zdroj)


def test_html_poznamka_je_div_s_triedou_podla_typu(tmp_path):
   xsl = tmp_path / 'h.xsl'
   xsl.write_text(f"""<xsl:stylesheet version="3.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
   <xsl:import href="{PROJECT_ROOT}/res/xslt/common_html.xsl"/>
   <xsl:output method="html"/>
   <xsl:template match="/"><div><xsl:apply-templates/></div></xsl:template>
</xsl:stylesheet>""", encoding='utf-8')
   with PySaxonProcessor(license=False) as proc:
      vystup = proc.new_xslt30_processor().compile_stylesheet(stylesheet_file=str(xsl)).transform_to_string(xdm_node=proc.parse_xml(xml_text=f'<znenie>{P}</znenie>'))
   assert re.search(r'<div [^>]*class="poznamka poznamka-warning">\s*<div class="poznamka-nadpis"><i class="bi bi-exclamation-triangle"></i> Upozornenie</div>\s*Vždy pracujte v konte <span class="bold">student</span>\s*</div>', vystup)


def test_fo_poznamka_ma_farebny_pas_a_ostane_na_svojom_mieste(tmp_path):
   zdroj = tmp_path / 't.xml'
   zdroj.write_text(_testy(znenie=f'Pred {P} Po'), encoding='utf-8')
   (tmp_path / 'qr').mkdir()
   (tmp_path / 'qr/K1.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>', encoding='utf-8')
   fo = tmp_path / 't.fo'
   with PySaxonProcessor(license=False) as proc:
      xsl = proc.new_xslt30_processor().compile_stylesheet(stylesheet_file=str(PROJECT_ROOT / 'res/xslt/downloadtests.xsl'))
      xsl.set_parameter('qrdir', proc.make_string_value(f'file://{tmp_path}/qr'))
      xsl.set_parameter('vodoznak', proc.make_boolean_value(False))
      xsl.transform_to_file(source_file=str(zdroj), output_file=str(fo))
   text = fo.read_text(encoding='utf-8')
   assert 'border-left="solid 3pt #ffc107"' in text and 'color="#ffc107"' in text and '>Upozornenie</fo:block>' in text
   assert text.index('Pred') < text.index('Vždy pracujte') < text.index('Po (2b)')      # body az na konci znenia


def test_createtests_zachova_poznamku_v_head_tail_aj_zneni():
   predmet = 'TSTPOZN'
   adresar = PROJECT_ROOT / 'res/xml/questions' / predmet
   adresar.mkdir(parents=True, exist_ok=True)
   try:
      (adresar / f'{predmet}_01.xml').write_text(
         _kapitola(head='<poznamka typ="info">H</poznamka>', tail='<poznamka typ="danger">T</poznamka>',
                   znenie='Otazka <poznamka typ="success">Z <alter><choice>a</choice><choice>b</choice></alter></poznamka>'),
         encoding='utf-8')
      roster = '<triedy><trieda id="III.T"><student meno="Jan" priezvisko="Novak" skupina="g"/></trieda></triedy>'
      with PySaxonProcessor(license=False) as proc:
         xsl = proc.new_xslt30_processor()
         for k, v in {'seed_ext': 's', 'predmet': predmet, 'trieda': 'III.T', 'skupina': 'g', 'kapitola': '01', 'start': '', 'stop': '',
                      'fileid': 'ab12', 'autor': ''}.items():
            xsl.set_parameter(k, proc.make_string_value(v))
         for k in ('anonymne', 'identita'):
            xsl.set_parameter(k, proc.make_boolean_value(k == 'identita'))
         xsl.set_cwd(str(PROJECT_ROOT))
         vystup = xsl.compile_stylesheet(stylesheet_file='./res/xslt/createtests.xsl').transform_to_string(xdm_node=proc.parse_xml(xml_text=roster))
   finally:
      for f in adresar.glob('*.xml'):
         f.unlink()
      adresar.rmdir()
   for typ, text in (('info', 'H'), ('danger', 'T'), ('success', 'Z')):
      assert re.search(rf'<poznamka typ="{typ}">{text}', vystup), typ
   assert re.search(r'<poznamka typ="success">Z (a|b)</poznamka>', vystup)    # alter vo vnutri sa vyriesil
