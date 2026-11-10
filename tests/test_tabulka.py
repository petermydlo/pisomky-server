# -*- coding: utf-8 -*-
"""
Tabuľka na vyplnenie (otazka/tabulka): kopírovanie do testu, formulár žiaka, automatické body
(res/xslt/grading.xsl, res/xquery/score.xq) a pohľad na vyhodnotený test.
"""

import asyncio
import logging
import re
import shutil
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import lxml.etree as ET
import pytest
import xmlschema
from fastapi.exceptions import HTTPException
from saxonche import PySaxonProcessor

from app.routers.questions import process_question
from app.utils import (
   add_question, body_tabulka, fork_question, format_body, format_percent, over_tabulku, serializuj_tabulku,
   store_mcq_scores, update_question, xslt_to_string, xquery_to_string, zmenene_zamrznute_polia,
)

PROJECT_ROOT = Path(__file__).parent.parent
PREDMET = 'TSTTAB'
QUESTIONS_FILE = PROJECT_ROOT / 'res/xml/questions' / PREDMET / f'{PREDMET}_01.xml'
TESTY_DIR = PROJECT_ROOT / 'res/xml/tests' / PREDMET
ANSWERS_DIR = PROJECT_ROOT / 'res/xml/answers' / PREDMET

# 2 vstupy, 1 vystup: 4 polia so spravnymi hodnotami 0, 1, 1, 0 (poradie v dokumente)
TABULKA_2X1 = """<tabulka povolene="01">
         <hlavicka><bunka>A</bunka><bunka>B</bunka><bunka>X</bunka></hlavicka>
         <riadok><bunka>0</bunka><bunka>0</bunka><bunka odpoved="0"/></riadok>
         <riadok><bunka>0</bunka><bunka>1</bunka><bunka odpoved="1"/></riadok>
         <riadok><bunka>1</bunka><bunka>0</bunka><bunka odpoved="1"/></riadok>
         <riadok><bunka>1</bunka><bunka>1</bunka><bunka odpoved="0"/></riadok>
      </tabulka>"""

# 4 vstupy, 1 vystup: 16 poli, vsetky so spravnou hodnotou 1
RIADKY_16 = ''.join(f'<riadok><bunka>{i}</bunka><bunka odpoved="1"/></riadok>' for i in range(16))
TABULKA_16 = f'<tabulka povolene="01"><hlavicka><bunka>I</bunka><bunka>X</bunka></hlavicka>{RIADKY_16}</tabulka>'

QUESTIONS_XML = f"""<?xml version='1.1' encoding='UTF-8'?>
<kapitola predmet="{PREDMET}" id="01" nazov="Tabulka">
   <kategoria pocet="1" id="kat1">
      <otazka id="q1" body="100">
         <znenie>Vyplnte tabulku</znenie>
         {TABULKA_2X1}
      </otazka>
   </kategoria>
</kapitola>
"""

TRIEDY_XML = """<?xml version='1.1' encoding='UTF-8'?>
<triedy>
   <trieda id="III.T">
      <student meno="Ján" priezvisko="Vzorný"/>
   </trieda>
</triedy>
"""

TESTY_XML = f"""<testy xml:lang="sk" predmet="{PREDMET}" trieda="X" skupina="" kapitola="01" fileid="1234" gendat="2026-01-01T00:00:00">
   <test id="k1">
      <otazka id="o1" body="100"><znenie>Tabulka 2x1</znenie>{TABULKA_2X1}</otazka>
      <otazka id="o2" body="100"><znenie>Tabulka 16</znenie>{TABULKA_16}</otazka>
      <otazka id="o3" body="100"><znenie>Neodpovedana</znenie>{TABULKA_2X1}</otazka>
   </test>
</testy>
"""

# o1: 2 z 4 poli spravne (0, 1; tretie zle; stvrte prazdne); o2: 15 zo 16 spravne; o3: bez odpovede
ANSWERS_XML = f"""<odpovede>
   <test id="k1" dat="2026-01-02T10:00:00" odhalene="1">
      <otazka id="o1">0|1|0|</otazka>
      <otazka id="o2">{'|'.join(['1'] * 15 + ['0'])}</otazka>
   </test>
</odpovede>
"""

TEST_SUBOR = f'{PREDMET}_X_01_1234.xml'


@pytest.fixture(scope='module')
def proc():
   with PySaxonProcessor(license=False) as p:
      yield p


@pytest.fixture(autouse=True)
def subory():
   for adresar in (QUESTIONS_FILE.parent, TESTY_DIR, ANSWERS_DIR):
      adresar.mkdir(parents=True, exist_ok=True)
   QUESTIONS_FILE.write_text(QUESTIONS_XML, encoding='utf-8')
   (TESTY_DIR / TEST_SUBOR).write_text(TESTY_XML, encoding='utf-8')
   (ANSWERS_DIR / TEST_SUBOR).write_text(ANSWERS_XML, encoding='utf-8')
   yield
   for adresar in (QUESTIONS_FILE.parent, TESTY_DIR, ANSWERS_DIR):
      shutil.rmtree(adresar, ignore_errors=True)


def _test_node(proc):
   node = proc.parse_xml(xml_file_name=str(TESTY_DIR / TEST_SUBOR))
   xp = proc.new_xpath_processor()
   xp.set_context(xdm_item=node)
   return next(iter(xp.evaluate('/testy/test')))


def _html(proc, stylesheet, params=None):
   return xslt_to_string(proc, stylesheet_file=str(PROJECT_ROOT / 'res/xslt' / stylesheet), xdm_node=_test_node(proc), params=params)


def test_createtests_kopiruje_tabulku_aj_so_spravnymi_hodnotami(proc):
   xsltproc = proc.new_xslt30_processor()
   parametre = {'seed_ext': 'seed', 'predmet': PREDMET, 'trieda': 'III.T', 'skupina': '', 'kapitola': '01',
      'start': '', 'stop': '', 'fileid': 'test', 'autor': 'novak'}
   for nazov, hodnota in parametre.items():
      xsltproc.set_parameter(nazov, proc.make_string_value(hodnota))
   xsltproc.set_parameter('anonymne', proc.make_boolean_value(False))
   xsltproc.set_parameter('identita', proc.make_boolean_value(False))
   xsltproc.set_cwd(str(PROJECT_ROOT))
   executable = xsltproc.compile_stylesheet(stylesheet_file='./res/xslt/createtests.xsl')
   vysledok = executable.transform_to_string(xdm_node=proc.parse_xml(xml_text=TRIEDY_XML))
   strom = ET.fromstring(vysledok.encode())
   assert [b.get('odpoved') for b in strom.iterfind('.//otazka/tabulka//bunka[@odpoved]')] == ['0', '1', '1', '0']
   assert _xp(strom, './/otazka/tabulka/@povolene') == ['01']


def test_formular_ma_polia_skryte_pole_a_nema_napovedu(proc):
   html = _html(proc, 'writetest.xsl', {'admin': False, 'napovedy_zostatok': 3})
   assert html.count('class="bunka-vstup"') == 4 + 16 + 4
   assert 'tabulka-hodnota' in html
   assert 'ai-napoveda-btn' not in html
   assert 'data-povolene="01"' in html


def test_pole_bez_povolene_je_siroke(proc):
   html = _html(proc, 'writetest.xsl', {'admin': False, 'napovedy_zostatok': 3})
   assert html.count('bunka-siroka') == 0
   zdroj = (TESTY_DIR / TEST_SUBOR).read_text(encoding='utf-8').replace(' povolene="01"', '')
   (TESTY_DIR / TEST_SUBOR).write_text(zdroj, encoding='utf-8')
   html = _html(proc, 'writetest.xsl', {'admin': False, 'napovedy_zostatok': 3})
   assert html.count('bunka-vstup bunka-siroka') == 24
   assert 'data-povolene' not in html


def test_formular_predvyplni_ulozenu_odpoved(proc):
   html = _html(proc, 'writetest.xsl', {'admin': False, 'napovedy_zostatok': 3})
   assert 'value="0|1|0|"' in html


def test_formular_neprezradza_spravne_hodnoty(proc):
   html = _html(proc, 'writetest.xsl', {'admin': False, 'napovedy_zostatok': 3})
   assert 'odpoved="' not in html.replace('class="odpoved', '')


def test_body_su_pomer_spravnych_poli_a_vypis_je_zaokruhleny(proc):
   html = _html(proc, 'showresult_student.xsl')
   assert '50/100' in html       # 2 zo 4 poli
   assert '93.75/100' in html    # 15 zo 16, bez zaokruhlenia na cele body
   assert '0/100' in html        # bez odpovede


def test_vyhodnotenie_farbi_polia_a_ukaze_spravnu_hodnotu(proc):
   html = _html(proc, 'showresult_student.xsl')
   assert 'class="bg-success"' in html
   assert 'class="bg-danger"' in html
   assert 'bunka-spravna' in html
   assert '–' in html


def test_score_xq_pocita_rovnako_ako_grading_xsl(proc):
   rel = f'../xml/%s/{PREDMET}/{TEST_SUBOR}'
   params = {'kluc': 'k1', 'test_cesta': rel % 'tests', 'answer_cesta': rel % 'answers'}
   vysledok = xquery_to_string(proc, str(PROJECT_ROOT / 'res/xquery/score.xq'), params=params)
   skore = ET.fromstring(vysledok.encode())
   assert skore.get('maximum') == '300'
   assert skore.get('ziskane') == '143.75'     # 50 + 93,75 + 0, nezaokruhlene
   assert skore.get('neuplne') == 'false'


def test_prazdna_odpoved_ziaka_nikdy_nedava_bod(proc):
   """Pole s prázdnou správnou hodnotou (neplatné podľa XSD) nesmie dať bod za nevyplnenie."""
   test = TESTY_XML.replace('<bunka odpoved="0"/></riadok>\n         <riadok><bunka>0</bunka><bunka>1</bunka>', '<bunka odpoved=""/></riadok>\n         <riadok><bunka>0</bunka><bunka>1</bunka>', 1)
   assert 'odpoved=""' in test
   (TESTY_DIR / TEST_SUBOR).write_text(test, encoding='utf-8')
   (ANSWERS_DIR / TEST_SUBOR).write_text('<odpovede><test id="k1" dat="2026-01-02T10:00:00" odhalene="1"><otazka id="o1">|1|1|0</otazka></test></odpovede>', encoding='utf-8')
   html = _html(proc, 'showresult_student.xsl')
   assert '75/100' in html     # 3 zo 4 poli, prve (prazdne vs prazdne) nie
   rel = f'../xml/%s/{PREDMET}/{TEST_SUBOR}'
   vysledok = xquery_to_string(proc, str(PROJECT_ROOT / 'res/xquery/score.xq'), params={'kluc': 'k1', 'test_cesta': rel % 'tests', 'answer_cesta': rel % 'answers'})
   assert ET.fromstring(vysledok.encode()).get('ziskane') == '75'     # ostatne otazky bez odpovede


def test_xsd_odmieta_prazdnu_odpoved_v_tabulke():
   for schema in ('questions.xsd', 'tests.xsd'):
      xsd = xmlschema.XMLSchema11(str(PROJECT_ROOT / 'res/xsd' / schema))
      assert xsd.types['TabulkaOdpoved'].is_valid('1')
      assert not xsd.types['TabulkaOdpoved'].is_valid('')
      assert not xsd.types['TabulkaOdpoved'].is_valid('   ')


def test_vysledok_pdf_obsahuje_tabulku(proc):
   fo = _html(proc, 'downloadresult.xsl', {'kluc': 'k1'})
   assert 'proportional-column-width(1)' in fo


def test_python_body_su_rovnake_ako_v_xslt():
   testy = ET.fromstring(TESTY_XML.encode())
   o1, o2, o3 = testy.findall('test/otazka')
   assert body_tabulka(o1, '0|1|0|') == Decimal(50)
   assert body_tabulka(o2, '|'.join(['1'] * 15 + ['0'])) == Decimal('93.75')
   assert body_tabulka(o3, '') == 0
   assert body_tabulka(o1, ' 0 |1|1|0') == Decimal(100)


def test_format_body_zaokruhluje_len_vypis():
   assert format_body(Decimal('93.75')) == '93.75'
   assert format_body(Decimal(100)) == '100'
   assert format_body(Decimal('12.50')) == '12.5'
   assert format_body(Decimal('100') / 7) == '14.29'
   assert format_body(Decimal('0.005')) == '0.01'


def test_format_percent_orezava_aby_nebolo_nad_hranicou():
   assert format_percent(Decimal('69.75')) == '69.75'
   assert format_percent(Decimal('69.9899')) == '69.98'     # pod hranicou 69.99, nesmie sa zobrazit ako 69.99
   assert format_percent(Decimal('70')) == '70'
   assert format_percent(Decimal('100') / 3) == '33.33'


def test_znamka_sa_pocita_z_nezaokruhlenych_bodov(proc):
   """69,75 z 100 b nesmie vyjst ako 70 % (znamka 2), hranica je 70 %."""
   test = TESTY_XML.replace(f'<otazka id="o1" body="100"><znenie>Tabulka 2x1</znenie>{TABULKA_2X1}</otazka>', f'<otazka id="o1" body="93"><znenie>Tabulka 2x1</znenie>{TABULKA_2X1}</otazka><otazka id="o2" body="7"><znenie>Druha</znenie>{TABULKA_2X1}</otazka>', 1)
   test = test.replace(f'<otazka id="o2" body="100"><znenie>Tabulka 16</znenie>{TABULKA_16}</otazka>', '', 1).replace(f'<otazka id="o3" body="100"><znenie>Neodpovedana</znenie>{TABULKA_2X1}</otazka>', '', 1)
   (TESTY_DIR / TEST_SUBOR).write_text(test, encoding='utf-8')
   (ANSWERS_DIR / TEST_SUBOR).write_text('<odpovede><test id="k1" dat="2026-01-02T10:00:00" odhalene="1"><otazka id="o1">0|1|1|1</otazka><otazka id="o2">1|0|0|1</otazka></test></odpovede>', encoding='utf-8')
   rel = f'../xml/%s/{PREDMET}/{TEST_SUBOR}'
   vysledok = xquery_to_string(proc, str(PROJECT_ROOT / 'res/xquery/score.xq'), params={'kluc': 'k1', 'test_cesta': rel % 'tests', 'answer_cesta': rel % 'answers'})
   skore = ET.fromstring(vysledok.encode())
   assert skore.get('ziskane') == '69.75'     # o1: 3 zo 4 (93 * 3 / 4); o2: 0 zo 4
   assert skore.get('znamka') == '3'
   html = _html(proc, 'showresult_student.xsl')
   assert '69.75/100' in html
   assert '(69.75%)' in re.sub(r'\s+', '', html)
   assert 'Známka: 3' in html


def test_store_mcq_scores_zapise_body_tabulky():
   store_mcq_scores('k1')
   odpovede = ET.parse(ANSWERS_DIR / TEST_SUBOR).getroot()
   assert _xp(odpovede, 'string(test/otazka[@id="o1"]/@body)') == '50'
   assert _xp(odpovede, 'string(test/otazka[@id="o2"]/@body)') == '93.75'
   assert _xp(odpovede, 'test/otazka[@id="o3"]') == []     # bez odpovede sa nezapisuje


def test_fork_otazky_zachova_tabulku():
   nova_id = fork_question('q1', {'znenie': '<znenie>Upravene znenie</znenie>', 'body': '100', 'odpovede': []})
   kapitola = ET.parse(QUESTIONS_FILE).getroot()
   stara = _xp(kapitola, '//otazka[@id="q1"]')[0]
   nova = _xp(kapitola, '//otazka[@id=$id]', id=nova_id)[0]
   assert stara.get('deprecated') == '1'
   assert [b.get('odpoved') for b in nova.iterfind('.//tabulka//bunka[@odpoved]')] == ['0', '1', '1', '0']
   assert nova.find('tabulka').get('povolene') == '01'
   assert [c.tag for c in nova][:2] == ['znenie', 'tabulka']     # tabulka hned za znenim


# --- editor: tabulka ako XML text ---

NOVA_TABULKA = """<tabulka povolene="">
   <hlavicka>
      <bunka>Slovo</bunka>
      <bunka>Preklad</bunka>
   </hlavicka>
   <riadok>
      <bunka>dom</bunka>
      <bunka odpoved="house"/>
   </riadok>
</tabulka>"""


def _xp(uzol: Any, vyraz: str, **parametre: Any) -> list[Any]:
   """XPath vysledok ako zoznam (lxml-stubs vracaju zjednotenie typov, s ktorym si pyright neporadi)."""
   return uzol.xpath(vyraz, **parametre)


def _request() -> Any:
   return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(logger=logging.getLogger('test'))))


def _otazka(id_otazky):
   return _xp(ET.parse(QUESTIONS_FILE).getroot(), '//otazka[@id=$id]', id=id_otazky)[0]


def test_over_tabulku_normalizuje_prazdne_povolene():
   tabulka = over_tabulku(NOVA_TABULKA)
   assert tabulka.get('povolene') is None
   assert [b.get('odpoved') for b in tabulka.iterfind('.//bunka[@odpoved]')] == ['house']


@pytest.mark.parametrize('xml, chyba', [
   ('<tabulka>', 'platné XML'),
   ('<inak/>', 'Koreňový element'),
   ('<tabulka x="1"><riadok><bunka odpoved="1"/></riadok></tabulka>', 'nepozná atribút x'),
   ('<tabulka><hlavicka><bunka></bunka></hlavicka><riadok><bunka></bunka></riadok></tabulka>', 'aspoň jedno pole'),
   ('<tabulka><riadok><bunka odpoved=" "/></riadok></tabulka>', 'nesmie byť prázdny'),
   ('<tabulka povolene="01"><riadok><bunka odpoved="2"/></riadok></tabulka>', 'povolenými'),
   ('<tabulka><riadok><bunka odpoved="1"/><bunka>a</bunka></riadok><riadok><bunka odpoved="1"/></riadok></tabulka>', 'rovnaký počet buniek'),
   ('<tabulka><riadok><bunka odpoved="1"/></riadok><hlavicka><bunka>A</bunka></hlavicka></tabulka>', 'musí byť prvá'),
   ('<tabulka><hlavicka><bunka>A</bunka></hlavicka><hlavicka><bunka>B</bunka></hlavicka><riadok><bunka odpoved="1"/></riadok></tabulka>', 'najviac jedna'),
   ('<tabulka><riadok><bunka odpoved="1"/></riadok><nieco/></tabulka>', 'len <hlavicka> a <riadok>'),
   ('<tabulka><hlavicka><bunka>A</bunka></hlavicka></tabulka>', 'aspoň jeden <riadok>'),
   ('<tabulka><riadok><bunka odpoved="1">text</bunka></riadok></tabulka>', 'nemá mať text'),
   ('<tabulka><riadok><bunka odpoved="1"><b/></bunka></riadok></tabulka>', 'ďalšie elementy'),
])
def test_over_tabulku_odmieta_chyby(xml, chyba):
   with pytest.raises(ValueError, match=re.escape(chyba)):
      over_tabulku(xml)


def test_serializacia_tabulky_sa_da_vratit_bez_straty():
   text = serializuj_tabulku(_otazka('q1'))
   assert text.startswith('<tabulka povolene="01">') and '\n   <hlavicka>' in text
   assert not zmenene_zamrznute_polia(_otazka('q1'), {'tabulka': text})     # rovnaka tabulka, len odsadena inak
   assert serializuj_tabulku(ET.fromstring('<otazka/>')) == ''


def test_update_question_nahradi_a_odstrani_tabulku():
   assert update_question('q1', {'tabulka': NOVA_TABULKA})
   otazka = _otazka('q1')
   assert [c.tag for c in otazka][:2] == ['znenie', 'tabulka']
   assert [b.get('odpoved') for b in otazka.iterfind('.//bunka[@odpoved]')] == ['house']
   assert update_question('q1', {'body': '50'})           # bez kluca tabulka sa nemeni
   assert _otazka('q1').find('tabulka') is not None
   assert update_question('q1', {'tabulka': ''})
   assert _otazka('q1').find('tabulka') is None


def test_update_question_s_neplatnou_tabulkou_nic_nezapise():
   pred = QUESTIONS_FILE.read_text(encoding='utf-8')
   with pytest.raises(ValueError):
      update_question('q1', {'tabulka': '<tabulka><riadok><bunka></bunka></riadok></tabulka>'})
   assert QUESTIONS_FILE.read_text(encoding='utf-8') == pred


def test_add_question_prida_otazku_s_tabulkou():
   nova_id, ok = add_question('kat1', {'znenie': '<znenie>Preklad</znenie>', 'body': '10', 'tabulka': NOVA_TABULKA})
   assert ok
   nova = _otazka(nova_id)
   assert [c.tag for c in nova] == ['znenie', 'tabulka']
   assert nova.find('tabulka').get('povolene') is None


def test_zmena_tabulky_je_zmena_zamrznuteho_pola():
   otazka = _otazka('q1')
   assert zmenene_zamrznute_polia(otazka, {'tabulka': NOVA_TABULKA})
   assert zmenene_zamrznute_polia(otazka, {'tabulka': ''})        # odstranenie tabulky
   assert not zmenene_zamrznute_polia(otazka, {})                   # bez pola sa tabulka nemeni


def test_fork_s_novou_tabulkou_pouzije_novu():
   nova_id = fork_question('q1', {'znenie': '<znenie>Nove</znenie>', 'body': '100', 'tabulka': NOVA_TABULKA})
   assert [b.get('odpoved') for b in _otazka(nova_id).iterfind('.//bunka[@odpoved]')] == ['house']
   assert [b.get('odpoved') for b in _otazka('q1').iterfind('.//bunka[@odpoved]')] == ['0', '1', '1', '0']


def test_process_question_odmieta_mcq_aj_tabulku_naraz():
   with pytest.raises(HTTPException) as chyba:
      asyncio.run(process_question(_request(), operacia='create', X_Remote_User='x', kategoria_id='kat1',
                                   znenie='<znenie>a</znenie>', odpovede='[{"text": "a", "spravna": "1"}]', tabulka=NOVA_TABULKA))
   assert chyba.value.status_code == 400 and 'MCQ' in chyba.value.detail


def test_process_question_vrati_chybu_neplatnej_tabulky():
   with pytest.raises(HTTPException) as chyba:
      asyncio.run(process_question(_request(), operacia='create', X_Remote_User='x', kategoria_id='kat1',
                                   znenie='<znenie>a</znenie>', tabulka='<tabulka><riadok><bunka></bunka></riadok></tabulka>'))
   assert chyba.value.status_code == 400 and 'aspoň jedno pole' in chyba.value.detail


def test_test_moze_mixovat_mcq_a_tabulku(proc):
   test = f"""<testy xml:lang="sk" predmet="{PREDMET}" trieda="X" skupina="" kapitola="01" fileid="1234" gendat="2026-01-01T00:00:00">
   <test id="k1">
      <otazka id="o1" body="2"><znenie>MCQ</znenie><odpoved spravna="1">prva</odpoved><odpoved spravna="0">druha</odpoved></otazka>
      <otazka id="o2" body="4"><znenie>Tabulka</znenie>{TABULKA_2X1}</otazka>
   </test>
</testy>
"""
   (TESTY_DIR / TEST_SUBOR).write_text(test, encoding='utf-8')
   (ANSWERS_DIR / TEST_SUBOR).write_text('<odpovede><test id="k1" dat="2026-01-02T10:00:00" odhalene="1"><otazka id="o1">a</otazka><otazka id="o2">0|1|1|1</otazka></test></odpovede>', encoding='utf-8')
   rel = f'../xml/%s/{PREDMET}/{TEST_SUBOR}'
   vysledok = xquery_to_string(proc, str(PROJECT_ROOT / 'res/xquery/score.xq'), params={'kluc': 'k1', 'test_cesta': rel % 'tests', 'answer_cesta': rel % 'answers'})
   skore = ET.fromstring(vysledok.encode())
   assert (skore.get('ziskane'), skore.get('maximum'), skore.get('neuplne')) == ('5', '6', 'false')     # MCQ 2 + tabulka 3 zo 4 poli
   assert 'Hodnotenie: 5/6' in _html(proc, 'showresult_student.xsl')
   assert 'id="pocetbodov">5</span>/6' in _html(proc, 'showresult.xsl')     # pohlad ucitela
   assert 'ai-napoveda-btn' in _html(proc, 'writetest.xsl', {'admin': False, 'napovedy_zostatok': 3})      # nápoveda ostáva pri MCQ


def test_vyhodnotenie_odovzda_skriptu_body_automatickych_otazok(proc):
   """Zivy sucet v showresult.js pripocitava k rucnym bodom MCQ a tabulku (tie nemaju pole na body)."""
   test = f"""<testy xml:lang="sk" predmet="{PREDMET}" trieda="X" skupina="" kapitola="01" fileid="1234" gendat="2026-01-01T00:00:00">
   <test id="k1">
      <otazka id="o1" body="2"><znenie>MCQ</znenie><odpoved spravna="1">prva</odpoved><odpoved spravna="0">druha</odpoved></otazka>
      <otazka id="o2" body="4"><znenie>Tabulka</znenie>{TABULKA_2X1}</otazka>
      <otazka id="o3" body="10"><znenie>Otvorena</znenie></otazka>
      <otazka id="o4" body="1" bonus="1"><znenie>Bonus MCQ</znenie><odpoved spravna="1">prva</odpoved><odpoved spravna="0">druha</odpoved></otazka>
   </test>
</testy>
"""
   (TESTY_DIR / TEST_SUBOR).write_text(test, encoding='utf-8')
   (ANSWERS_DIR / TEST_SUBOR).write_text('<odpovede><test id="k1" dat="2026-01-02T10:00:00"><otazka id="o1">a</otazka><otazka id="o2">0|1|1|1</otazka><otazka id="o3" body="6.5">x</otazka><otazka id="o4">a</otazka></test></odpovede>', encoding='utf-8')
   html = _html(proc, 'showresult.xsl')
   assert 'data-auto-body="6"' in html      # MCQ 2 + tabulka 3 + bonus 1
   assert 'data-auto-max="6"' in html       # bonus sa do maxima nepocita


def test_hlavicka_otazky_vypisuje_body_naformatovane(proc):
   """'(6.5b)' namiesto surovej hodnoty body="6.50" vo vsetkych vystupoch."""
   (TESTY_DIR / TEST_SUBOR).write_text(f"""<testy xml:lang="sk" predmet="{PREDMET}" trieda="X" skupina="" kapitola="01" fileid="1234" gendat="2026-01-01T00:00:00">
   <test id="k1"><otazka id="o1" body="6.50"><znenie>Tabulka</znenie>{TABULKA_2X1}</otazka></test></testy>
""", encoding='utf-8')
   (ANSWERS_DIR / TEST_SUBOR).write_text('<odpovede><test id="k1" dat="2026-01-02T10:00:00"/></odpovede>', encoding='utf-8')
   for xsl, parametre in (('writetest.xsl', {'admin': False, 'napovedy_zostatok': 3}), ('showtest.xsl', {'admin': False, 'napovedy_zostatok': 3}),
                          ('showresult.xsl', None), ('downloadresult.xsl', {'kluc': 'k1'})):
      vystup = _html(proc, xsl, parametre)
      assert '(6.5b)' in vystup and '6.50b' not in vystup, xsl

