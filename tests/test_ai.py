# -*- coding: utf-8 -*-

import pytest
import lxml.etree as ET

from app.routers.ai import (
   _parsuj_hint_keys,
   _spocitaj_napovedy_testu,
   _nacitaj_predchadzajuce_keys,
   _aktualizuj_zapis,
   _uloz_zapis,
   _najdi_napovedu,
)

PREDMET = 'MAT'
TEST_ID = 'TEST01'
OTAZKA_ID = 'q1'

FEEDBACK_XML = f"""\
<?xml version='1.0' encoding='utf-8'?>
<feedback predmet="{PREDMET}" trieda="1A" skupina="" kapitola="kap1" fileid="ab12">
   <zapis id="zap1" datum="2026-01-01T10:00:00" otazka_id="{OTAZKA_ID}" test_id="{TEST_ID}" val="1">
      <hint>Skús to inak</hint>
      <keys>zlomky, delenie</keys>
   </zapis>
   <zapis id="zap2" datum="2026-01-01T10:05:00" otazka_id="{OTAZKA_ID}" test_id="{TEST_ID}" val="0">
      <hint>Iná nápoveda</hint>
   </zapis>
   <zapis id="zap3" datum="2026-01-01T10:10:00" otazka_id="q2" test_id="{TEST_ID}" val=""/>
   <zapis id="zap4" datum="2026-01-01T10:15:00" otazka_id="{OTAZKA_ID}" test_id="{TEST_ID}" val="0">
      <keys>iny, zoznam</keys>
   </zapis>
</feedback>
"""

QUESTIONS_XML = f"""\
<?xml version='1.0' encoding='utf-8'?>
<kapitola predmet="{PREDMET}" id="kap1">
   <kategoria id="kat1" pocet="1">
      <otazka id="{OTAZKA_ID}">
         <znenie>Koľko je 1/2 + 1/4?</znenie>
         <odpoved spravna="0">1/6</odpoved>
         <odpoved spravna="1" napoveda_key="zlomky">3/4</odpoved>
         <napoveda>Všeobecná nápoveda k otázke</napoveda>
         <napoveda pre="zlomky">Nápoveda k spoločnému menovateľu</napoveda>
         <napoveda pre="iny_kluc">Nápoveda, ktorá sa nemá zobraziť</napoveda>
         <vzor>3/4</vzor>
         <klucove_slova>
            <slovo>zlomky</slovo>
            <slovo>menovateľ</slovo>
         </klucove_slova>
      </otazka>
      <otazka id="q_bez_extra">
         <znenie>Otázka bez nápovedy/vzoru</znenie>
         <odpoved spravna="1">a</odpoved>
      </otazka>
   </kategoria>
</kapitola>
"""


@pytest.fixture(autouse=True)
def workdir(tmp_path, monkeypatch):
   (tmp_path / 'res/xml/feedback' / PREDMET).mkdir(parents=True)
   (tmp_path / 'res/xml/questions' / PREDMET).mkdir(parents=True)
   (tmp_path / 'res/xml/tests' / PREDMET).mkdir(parents=True)
   monkeypatch.chdir(tmp_path)


@pytest.fixture
def feedback_file(tmp_path):
   cesta = tmp_path / 'res/xml/feedback' / PREDMET / f'{PREDMET}_1A_kap1_ab12.xml'
   cesta.write_text(FEEDBACK_XML, encoding='utf-8')
   return cesta


@pytest.fixture
def questions_file(tmp_path):
   cesta = tmp_path / 'res/xml/questions' / PREDMET / f'{PREDMET}_kap1.xml'
   cesta.write_text(QUESTIONS_XML, encoding='utf-8')
   return cesta


# --- _parsuj_hint_keys ---

def test_parsuj_hint_keys_len_hint():
   hint, keys = _parsuj_hint_keys('HINT: Skús to takto')
   assert hint == 'Skús to takto'
   assert keys == ''

def test_parsuj_hint_keys_hint_a_keys():
   hint, keys = _parsuj_hint_keys('HINT: Nápoveda\nKEYS: k1, k2')
   assert hint == 'Nápoveda'
   assert keys == 'k1, k2'

def test_parsuj_hint_keys_bez_znaciek():
   raw = 'Obyčajný text bez značiek'
   hint, keys = _parsuj_hint_keys(raw)
   assert hint == raw
   assert keys == ''

def test_parsuj_hint_keys_case_insensitive():
   hint, keys = _parsuj_hint_keys('hint: malé písmená\nkeys: a, b')
   assert hint == 'malé písmená'
   assert keys == 'a, b'


# --- _spocitaj_napovedy_testu ---

def test_spocitaj_napovedy_testu_neexistujuci_subor():
   assert _spocitaj_napovedy_testu('./neexistuje.xml', TEST_ID) == 0

def test_spocitaj_napovedy_testu_pocita_len_pre_dany_test(feedback_file):
   assert _spocitaj_napovedy_testu(str(feedback_file), TEST_ID) == 4

def test_spocitaj_napovedy_testu_iny_test(feedback_file):
   assert _spocitaj_napovedy_testu(str(feedback_file), 'INY_TEST') == 0


# --- _nacitaj_predchadzajuce_keys ---

def test_nacitaj_predchadzajuce_keys_neexistujuci_subor():
   assert _nacitaj_predchadzajuce_keys('./neexistuje.xml', OTAZKA_ID) == []

def test_nacitaj_predchadzajuce_keys_len_so_zapisanymi_keys(feedback_file):
   vysledok = _nacitaj_predchadzajuce_keys(str(feedback_file), OTAZKA_ID)
   assert vysledok == [
      {'keys': 'zlomky, delenie', 'val': '1'},
      {'keys': 'iny, zoznam', 'val': '0'},
   ]

def test_nacitaj_predchadzajuce_keys_ina_otazka(feedback_file):
   assert _nacitaj_predchadzajuce_keys(str(feedback_file), 'q2') == []

def test_nacitaj_predchadzajuce_keys_limit(feedback_file):
   vysledok = _nacitaj_predchadzajuce_keys(str(feedback_file), OTAZKA_ID, limit=1)
   assert vysledok == [{'keys': 'iny, zoznam', 'val': '0'}]


# --- _aktualizuj_zapis ---

def test_aktualizuj_zapis_neexistujuci_subor_nespadne():
   _aktualizuj_zapis('./neexistuje.xml', 'zap1', hint='x')

def test_aktualizuj_zapis_prida_hint(feedback_file):
   _aktualizuj_zapis(str(feedback_file), 'zap2', hint='Nová nápoveda')
   tree = ET.parse(str(feedback_file))
   zapis = tree.find('.//zapis[@id="zap2"]')
   assert zapis is not None
   hint = zapis.find('hint')
   assert hint is not None
   assert hint.text == 'Nová nápoveda'

def test_aktualizuj_zapis_aktualizuje_existujuci_hint(feedback_file):
   _aktualizuj_zapis(str(feedback_file), 'zap1', hint='Prepísaná nápoveda')
   tree = ET.parse(str(feedback_file))
   zapis = tree.find('.//zapis[@id="zap1"]')
   assert zapis is not None
   hint = zapis.find('hint')
   assert hint is not None
   assert hint.text == 'Prepísaná nápoveda'

def test_aktualizuj_zapis_prida_keys(feedback_file):
   _aktualizuj_zapis(str(feedback_file), 'zap2', keys='nove, kluce')
   tree = ET.parse(str(feedback_file))
   zapis = tree.find('.//zapis[@id="zap2"]')
   assert zapis is not None
   keys = zapis.find('keys')
   assert keys is not None
   assert keys.text == 'nove, kluce'

def test_aktualizuj_zapis_neexistujuci_zapis_id_nespadne(feedback_file):
   _aktualizuj_zapis(str(feedback_file), 'neexistuje', hint='x')
   tree = ET.parse(str(feedback_file))
   assert tree.find('.//zapis[@id="neexistuje"]') is None


# --- _uloz_zapis ---

def test_uloz_zapis_vytvori_novy_subor():
   subor = './res/xml/feedback/MAT/MAT_1A_kap1_ab12.xml'
   _uloz_zapis(subor, 'zapnovy', OTAZKA_ID, TEST_ID, predmet=PREDMET, trieda='1A', kapitola='kap1', fileid='ab12')
   tree = ET.parse(subor)
   root = tree.getroot()
   assert root.get('predmet') == PREDMET
   zapis = root.find('zapis[@id="zapnovy"]')
   assert zapis is not None
   assert zapis.get('otazka_id') == OTAZKA_ID
   assert zapis.get('test_id') == TEST_ID
   assert zapis.get('val') == ''

def test_uloz_zapis_prida_do_existujuceho(feedback_file):
   _uloz_zapis(str(feedback_file), 'zapnovy', OTAZKA_ID, TEST_ID)
   tree = ET.parse(str(feedback_file))
   zapisy = tree.findall('.//zapis')
   assert len(zapisy) == 5
   assert tree.find('.//zapis[@id="zap1"]') is not None


# --- _najdi_napovedu ---

def test_najdi_napovedu_otazka_neexistuje(questions_file):
   assert _najdi_napovedu('neexistuje') is None

def test_najdi_napovedu_bez_spravnej_odpovede_len_vseobecna(questions_file):
   vysledok = _najdi_napovedu(OTAZKA_ID)
   assert vysledok is not None
   assert vysledok['napovedy'] == ['Všeobecná nápoveda k otázke']
   assert vysledok['vzor'] == '3/4'
   assert vysledok['klucove'] == ['zlomky', 'menovateľ']

def test_najdi_napovedu_so_spravnou_odpovedou_zahrnie_naviazanu(questions_file):
   vysledok = _najdi_napovedu(OTAZKA_ID, spravna_odpoved='3/4')
   assert vysledok is not None
   assert set(vysledok['napovedy']) == {'Všeobecná nápoveda k otázke', 'Nápoveda k spoločnému menovateľu'}

def test_najdi_napovedu_bez_extra_udajov(questions_file):
   vysledok = _najdi_napovedu('q_bez_extra')
   assert vysledok == {'napovedy': None, 'vzor': None, 'klucove': []}
