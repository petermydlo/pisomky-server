# -*- coding: utf-8 -*-

import os
import asyncio
import logging
from types import SimpleNamespace
import pytest
import lxml.etree as ET
from pathlib import Path
from filelock import FileLock
from fastapi.exceptions import HTTPException
from saxonche import PySaxonProcessor

from http_klient import http
from datetime import datetime
from app.routers.testrun import write_answers, nastav_stop, nastav_cas, ocisti_odpovede, MAX_DLZKA_ODPOVEDE
from app.routers.results import write_marks, write_odhalene, over_body
from app.routers.importanswers import write_answers_import, nacitaj_tests_xml, ziskaj_metadata
from app.routers.tests import vymaz_testy, ma_odpovede

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
   q1 = test.find('otazka[@id="q1"]')
   q2 = test.find('otazka[@id="q2"]')
   assert q1 is not None
   assert q2 is not None
   assert q1.text == 'a'
   assert q2.text == 'b'

def test_write_answers_aktualizuje_existujuci(answers_file):
   adresar = f'./res/xml/answers/{PREDMET}'
   lock = FileLock(f'{answers_file}.lock')
   write_answers(lock, answers_file, {'q1': 'c'}, adresar, PREDMET, TRIEDA, SKUPINA, KAPITOLA, FILEID, KLUC)
   tree = ET.parse(str(answers_file))
   testy = tree.findall(f'.//test[@id="{KLUC}"]')
   assert len(testy) == 1
   q1 = testy[0].find('otazka[@id="q1"]')
   assert q1 is not None
   assert q1.text == 'c'

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
   q2 = tree.find(f'.//test[@id="{KLUC}"]/otazka[@id="q2"]')
   assert q1 is not None
   assert q2 is not None
   assert q1.get('body') == '1'
   assert q2.get('body') == '0'

def test_write_marks_koment(answers_file):
   lock = FileLock(f'{answers_file}.lock')
   write_marks(lock, answers_file, {'k_q1': 'Správne'}, KLUC, DAT)
   tree = ET.parse(str(answers_file))
   q1 = tree.find(f'.//test[@id="{KLUC}"]/otazka[@id="q1"]')
   assert q1 is not None
   assert q1.get('koment') == 'Správne'

def test_write_marks_bh_typ(answers_file):
   lock = FileLock(f'{answers_file}.lock')
   write_marks(lock, answers_file, {'bh_q1': '2'}, KLUC, DAT)
   tree = ET.parse(str(answers_file))
   q1 = tree.find(f'.//test[@id="{KLUC}"]/otazka[@id="q1"]')
   assert q1 is not None
   assert q1.get('body') == '2'

def test_write_marks_neexistujuca_otazka_vytvori_element(answers_file):
   lock = FileLock(f'{answers_file}.lock')
   write_marks(lock, answers_file, {'h_q9': '3'}, KLUC, DAT)
   tree = ET.parse(str(answers_file))
   q9 = tree.find(f'.//test[@id="{KLUC}"]/otazka[@id="q9"]')
   assert q9 is not None
   assert q9.get('body') == '3'


def test_write_marks_desatinna_ciarka_sa_zapise_s_bodkou(answers_file):
   write_marks(FileLock(f'{answers_file}.lock'), answers_file, {'h_q1': '5,5', 'bh_q2': ' 2.25 '}, KLUC, DAT)
   tree = ET.parse(str(answers_file))
   assert tree.xpath(f'//test[@id="{KLUC}"]/otazka[@id="q1"]/@body') == ['5.5']  # type: ignore[union-attr]
   assert tree.xpath(f'//test[@id="{KLUC}"]/otazka[@id="q2"]/@body') == ['2.25']  # type: ignore[union-attr]

def test_write_marks_prazdne_body_odstrania_atribut(answers_file):
   write_marks(FileLock(f'{answers_file}.lock'), answers_file, {'h_q1': '3'}, KLUC, DAT)
   write_marks(FileLock(f'{answers_file}.lock'), answers_file, {'h_q1': ''}, KLUC, DAT)
   assert ET.parse(str(answers_file)).xpath(f'//test[@id="{KLUC}"]/otazka[@id="q1"]/@body') == []  # type: ignore[union-attr]

@pytest.mark.parametrize('hodnota', ['abc', '-1', 'NaN', 'Infinity', '1;2', '5 b'])
def test_write_marks_neplatne_body_nic_nezapisu(answers_file, hodnota):
   povodny = answers_file.read_text(encoding='utf-8')
   with pytest.raises(ValueError):
      write_marks(FileLock(f'{answers_file}.lock'), answers_file, {'h_q1': '1', 'h_q2': hodnota}, KLUC, DAT)
   assert answers_file.read_text(encoding='utf-8') == povodny

def test_over_body_normalizuje():
   assert over_body('7') == '7'
   assert over_body('1e2') == '100'
   assert over_body('-0') == '0'
   assert over_body('  ') is None


# --- changetime ---

def _strom(tests_file):
   return ET.parse(str(tests_file))

def _test_el(strom):
   test = strom.find(f'.//test[@id="{KLUC}"]')
   assert test is not None
   return test

def test_nastav_cas_sada_start_a_stop(tests_file):
   strom = _strom(tests_file)
   nastav_cas(strom, None, '2026-01-01T08:00', '2026-01-01T10:00')
   assert [strom.getroot().get('start'), strom.getroot().get('stop')] == ['2026-01-01T08:00', '2026-01-01T10:00']
   assert _test_el(strom).get('start') is None

def test_nastav_cas_none_nemeni_a_prazdny_retazec_zrusi(tests_file):
   strom = _strom(tests_file)
   nastav_cas(strom, None, '2026-01-01T08:00', '2026-01-01T10:00')
   nastav_cas(strom, None, None, '  ')
   assert [strom.getroot().get('start'), strom.getroot().get('stop')] == ['2026-01-01T08:00', None]

def test_nastav_cas_jeden_test_nechava_sadu(tests_file):
   strom = _strom(tests_file)
   nastav_cas(strom, KLUC, '2026-01-01T09:00', '2026-01-01T09:45')
   assert [_test_el(strom).get('start'), _test_el(strom).get('stop')] == ['2026-01-01T09:00', '2026-01-01T09:45']
   assert strom.getroot().get('start') is None and strom.getroot().get('stop') is None

def test_nastav_cas_test_nenajdeny(tests_file):
   with pytest.raises(HTTPException) as exc:
      nastav_cas(_strom(tests_file), 'NEEXISTUJE', '2026-01-01T09:00', None)
   assert exc.value.status_code == 404

def _changetime(**parametre):
   zaklad = {'predmet': PREDMET, 'trieda': TRIEDA, 'kapitola': KAPITOLA, 'fileid': FILEID, 'skupina': SKUPINA}
   with http() as klient:
      return klient.post('/admin/changetime', data={**zaklad, **parametre})

def test_changetime_trasa_zapise_cas_do_suboru(tests_file):
   odpoved = _changetime(start='2026-01-01T08:00', stop='2026-01-01T10:00')
   assert odpoved.status_code == 204
   root = ET.parse(str(tests_file)).getroot()
   assert [root.get('start'), root.get('stop')] == ['2026-01-01T08:00', '2026-01-01T10:00']

def test_changetime_trasa_jeden_test(tests_file):
   _changetime(kluc=KLUC, stop='2026-01-01T09:30')
   assert _test_el(ET.parse(str(tests_file))).get('stop') == '2026-01-01T09:30'

def test_changetime_trasa_neznamy_test_je_404(tests_file):
   assert _changetime(kluc='NEEXISTUJE', stop='2026-01-01T09:30').status_code == 404

def test_changetime_trasa_neplatna_cesta_je_400_a_nic_nezapise(tests_file, tmp_path):
   povodny = tests_file.read_text(encoding='utf-8')
   assert _changetime(trieda='../../x', stop='2026-01-01T09:30').status_code == 400
   assert tests_file.read_text(encoding='utf-8') == povodny
   assert {p.relative_to(tmp_path).parts[0] for p in tmp_path.rglob('*')} == {'res'}

def test_changetime_trasa_chybajuci_subor_je_404(tmp_path):
   assert _changetime(stop='2026-01-01T09:30').status_code == 404


# --- stoptime ---

def _stop_testu(cesta):
   test = ET.parse(str(cesta)).find(f'.//test[@id="{KLUC}"]')
   assert test is not None
   return test.get('stop')

def _stoptime_strom(tests_file, nahrada=None):
   if nahrada:
      tests_file.write_text(TESTS_XML.replace(*nahrada), encoding='utf-8')
   return ET.parse(str(tests_file))

def test_nastav_stop_pouzije_serverovy_cas(tests_file):
   strom = _stoptime_strom(tests_file)
   nastav_stop(strom, KLUC, datetime(2026, 1, 1, 10, 7, 41))
   assert strom.find(f'.//test[@id="{KLUC}"]').get('stop') == '2026-01-01T10:07'  # type: ignore[union-attr]

def test_nastav_stop_skracuje_buduci_koniec(tests_file):
   strom = _stoptime_strom(tests_file, (f'<test id="{KLUC}">', f'<test id="{KLUC}" stop="2026-01-01T11:00">'))
   nastav_stop(strom, KLUC, datetime(2026, 1, 1, 10, 7))
   assert strom.find(f'.//test[@id="{KLUC}"]').get('stop') == '2026-01-01T10:07'  # type: ignore[union-attr]

def test_nastav_stop_nepredlzi_skonceny_test(tests_file):
   strom = _stoptime_strom(tests_file, (f'<test id="{KLUC}">', f'<test id="{KLUC}" stop="2026-01-01T09:00">'))
   nastav_stop(strom, KLUC, datetime(2026, 1, 1, 10, 7))
   assert strom.find(f'.//test[@id="{KLUC}"]').get('stop') == '2026-01-01T09:00'  # type: ignore[union-attr]

def test_nastav_stop_nepredlzi_koniec_sady(tests_file):
   strom = _stoptime_strom(tests_file, ('<testy ', '<testy stop="2026-01-01T09:00" '))
   nastav_stop(strom, KLUC, datetime(2026, 1, 1, 10, 7))
   assert strom.find(f'.//test[@id="{KLUC}"]').get('stop') is None  # type: ignore[union-attr]

def test_nastav_stop_nenajdeny(tests_file):
   with pytest.raises(HTTPException) as exc:
      nastav_stop(_stoptime_strom(tests_file), 'NEEXISTUJE', datetime(2026, 1, 1, 10, 7))
   assert exc.value.status_code == 404

def test_stoptime_trasa_zapise_serverovy_cas_nie_cas_z_formulara(tests_file):
   pred = datetime.now().replace(second=0, microsecond=0)
   with http() as klient:
      assert klient.post(f'/stoptime/{KLUC}', data={'stop': '2000-01-01T00:00'}).status_code == 204   #cas z formulara sa ignoruje
   zapisany = datetime.fromisoformat(_stop_testu(tests_file) or '')
   assert pred <= zapisany <= datetime.now()


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


def _subory_testu(tmp_path, fileid=FILEID) -> list[Path]:
   stem = f'{PREDMET}_{TRIEDA}{SKUPINA}_{KAPITOLA}_{fileid}'
   subory = []
   for typ in ('tests', 'answers', 'feedback'):
      (tmp_path / 'res/xml' / typ / PREDMET).mkdir(parents=True, exist_ok=True)
      subory += [tmp_path / 'res/xml' / typ / PREDMET / f'{stem}.xml', tmp_path / 'res/xml' / typ / PREDMET / f'{stem}.xml.lock']
   subory += [tmp_path / 'res/xml/answers' / PREDMET / f'{stem}_{KLUC}-screenshot.png_subor',
              tmp_path / 'res/xml/answers' / PREDMET / f'{stem}_TEST02-a_b.txt_subor']
   for s in subory:
      s.write_text('x', encoding='utf-8')
   return subory

def test_vymaz_testy_vsetko_aj_locky_a_odovzdane_subory(tmp_path):
   subory = _subory_testu(tmp_path)
   ine = _subory_testu(tmp_path, fileid='cd34')
   vymaz_testy(Path(f'./res/xml/tests/{PREDMET}/{subory[0].name}'), True, True, True)
   assert [s for s in subory if s.exists()] == []
   assert all(s.exists() for s in ine)

def test_vymaz_testy_len_test_necha_odpovede_aj_odovzdane_subory(tmp_path):
   subory = _subory_testu(tmp_path)
   vymaz_testy(Path(f'./res/xml/tests/{PREDMET}/{subory[0].name}'), True, False, False)
   assert not subory[0].exists() and not subory[1].exists()
   assert all(s.exists() for s in subory[2:])


# --- importanswers: write_answers_import ---

def test_write_answers_import_vytvori_subor(tmp_path):
   cesta = tmp_path / 'res/xml/answers' / PREDMET / f'{PREDMET}_{TRIEDA}_{KAPITOLA}_{FILEID}.xml'
   lock = FileLock(f'{cesta}.lock')
   write_answers_import(lock, cesta, {'q1': 'a', 'q2': 'b'}, KLUC)
   assert cesta.exists()
   tree = ET.parse(str(cesta))
   test = tree.find(f'.//test[@id="{KLUC}"]')
   assert test is not None
   q1 = test.find('otazka[@id="q1"]')
   assert q1 is not None
   assert q1.text == 'a'

def test_write_answers_import_aktualizuje_existujuci(answers_file):
   lock = FileLock(f'{answers_file}.lock')
   write_answers_import(lock, answers_file, {'q1': 'x'}, KLUC)
   tree = ET.parse(str(answers_file))
   testy = tree.findall(f'.//test[@id="{KLUC}"]')
   assert len(testy) == 1
   q1 = testy[0].find('otazka[@id="q1"]')
   assert q1 is not None
   assert q1.text == 'x'

def test_write_answers_import_prida_novu_otazku(answers_file):
   lock = FileLock(f'{answers_file}.lock')
   write_answers_import(lock, answers_file, {'q9': 'c'}, KLUC)
   tree = ET.parse(str(answers_file))
   q9 = tree.find(f'.//test[@id="{KLUC}"]/otazka[@id="q9"]')
   assert q9 is not None
   assert q9.text == 'c'

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

def test_nacitaj_tests_xml_bez_spravnych_odpovedi(tmp_path):
   cesta = tmp_path / 'tests.xml'
   cesta.write_text(
      '<testy><test id="T1"><otazka id="q1"><znenie>Z</znenie>'
      '<odpoved spravna="0">x</odpoved><odpoved spravna="1">y</odpoved>'
      '</otazka></test></testy>', encoding='utf-8'
   )
   result = nacitaj_tests_xml(str(cesta), 'T1')
   assert result.count('<odpoved>') == 2
   assert 'spravna' not in result

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


# --- regeneratetests: blokacia pri existujucich odpovediach ---

def test_ma_odpovede_bez_answers_suboru(tests_file):
   assert ma_odpovede(tests_file) is False

def test_ma_odpovede_s_odpovedami(tests_file, answers_file):
   assert ma_odpovede(tests_file) is True

def test_ma_odpovede_bez_test_dat(tests_file, answers_file):
   answers_file.write_text('<odpovede xml:lang="sk"></odpovede>', encoding='utf-8')
   assert ma_odpovede(tests_file) is False

def test_regeneratetests_odmietne_ak_su_odpovede(tests_file, answers_file):
   povodny = tests_file.read_text(encoding='utf-8')
   with http() as klient:
      odpoved = klient.post('/admin/regeneratetests', data={'predmet': PREDMET, 'trieda': TRIEDA, 'kapitola': KAPITOLA, 'fileid': FILEID, 'skupina': SKUPINA})
   assert odpoved.status_code == 409
   assert tests_file.read_text(encoding='utf-8') == povodny


# --- saveanswers ---

def _saveanswers(data, subory=None, kluc=KLUC):
   """POST /saveanswers/{kluc} so skutocnym Saxon procesorom; `subory` su dvojice (nazov, obsah)."""
   with PySaxonProcessor(license=False) as proc:
      with http(user=None, proc=proc) as klient:
         return klient.post(f'/saveanswers/{kluc}', data=data, files=[('subory', (nazov, obsah)) for nazov, obsah in subory or []] or None)

def _subor(filename, obsah):
   async def citaj():
      return obsah
   return SimpleNamespace(filename=filename, read=citaj)

def test_saveanswers_cesty_su_z_testu_nie_z_formulara(tests_file, tmp_path):
   podvrhnute = {'predmet': '../../../../utok', 'trieda': '/../../x', 'skupina': 'a', 'kapitola': '..', 'fileid': 'zz', 'q1': 'a'}
   okolie_pred = set(os.listdir(tmp_path.parent))
   assert _saveanswers(podvrhnute, [('../../dir/evil.txt', b'obsah')]).status_code == 201
   odpovede = tmp_path / 'res/xml/answers' / PREDMET
   stem = f'{PREDMET}_{TRIEDA}{SKUPINA}_{KAPITOLA}_{FILEID}'
   xml = ET.parse(str(odpovede / f'{stem}.xml')).getroot()
   assert [xml.get(a) for a in ('predmet', 'trieda', 'skupina', 'kapitola', 'fileid')] == [PREDMET, TRIEDA, SKUPINA, KAPITOLA, FILEID]
   assert xml.xpath('test[@id="TEST01"]/otazka[@id="q1"]/text()') == ['a']  # type: ignore[union-attr]
   assert (odpovede / f'{stem}_{KLUC}-evil.txt_subor').read_bytes() == b'obsah'
   zapisane = {p.relative_to(tmp_path).parts[0] for p in tmp_path.rglob('*')}
   assert zapisane == {'res'}  # nic mimo res/
   assert set(os.listdir(tmp_path.parent)) == okolie_pred  # ani nad nim (predmet='../../../../utok' by vytvoril tmp_path/../utok)
   assert not (tmp_path / 'res/xml/answers/zz').exists()
   assert sorted(p.name for p in (tmp_path / 'res/xml/answers').iterdir()) == [PREDMET]

def test_saveanswers_skonceny_test_je_403_a_nic_nezapise(tmp_path):
   cesta = tmp_path / 'res/xml/tests' / PREDMET / f'{PREDMET}_{TRIEDA}{SKUPINA}_{KAPITOLA}_{FILEID}.xml'
   cesta.write_text(TESTS_XML.replace('<testy ', '<testy stop="2020-01-01T08:00" '), encoding='utf-8')
   assert _saveanswers({'q1': 'a'}).status_code == 403
   assert list((tmp_path / 'res/xml/answers' / PREDMET).iterdir()) == []


def test_ocisti_odpovede_necha_len_otazky_testu():
   assert ocisti_odpovede({'q1': 'a', 'cudzie': 'x', 'predmet': 'y', 'subory': 'z'}, {'q1', 'q2'}) == {'q1': 'a'}

def test_ocisti_odpovede_odstrani_neplatne_xml_znaky_a_necha_diakritiku_aj_emoji():
   assert ocisti_odpovede({'q1': 'a\x00b\x0bc\x1fd\ufffee\tš\n😀'}, {'q1'}) == {'q1': 'abcde\tš\n😀'}

def test_ocisti_odpovede_orezie_dlhu_odpoved():
   assert len(ocisti_odpovede({'q1': 'x' * (MAX_DLZKA_ODPOVEDE + 5)}, {'q1'})['q1']) == MAX_DLZKA_ODPOVEDE

def test_ocisti_odpovede_ignoruje_subor_pod_klucom_otazky():
   assert ocisti_odpovede({'q1': _subor('a.txt', b'x')}, {'q1'}) == {}

def test_saveanswers_zapise_len_otazky_testu_a_znak_nezhodi_ulozenie(tests_file, tmp_path):
   udaje = {'q1': 'a\x0bb', 'cudzia_otazka': 'x', 'q9': 'y'}
   assert _saveanswers(udaje).status_code == 201
   xml = ET.parse(str(tmp_path / 'res/xml/answers' / PREDMET / f'{PREDMET}_{TRIEDA}{SKUPINA}_{KAPITOLA}_{FILEID}.xml')).getroot()
   assert [(o.get('id'), o.text) for o in xml.findall('test/otazka')] == [('q1', 'ab')]


# --- process_chapter ---

def test_process_chapter_neplatne_id_je_400_a_len_varovanie(caplog):
   with caplog.at_level(logging.DEBUG, logger='pisomky'):
      odpoved = _kapitola('create', kapitola_id='../x', predmet='PIT3', user='nikto')
   assert odpoved.status_code == 400
   assert 'ID kapitoly' in odpoved.json()['detail']
   assert [r.levelno for r in caplog.records] == [logging.WARNING]


# --- trasy skladajuce cesty z parametrov: zle hodnoty sa odmietnu pred akymkolvek zapisom ---

#trasy, ktore pracuju s jednou sadou testov (dependency app/sada.py), ako (metoda, url, formular)
def _trasy_sady(predmet, trieda):
   zaklad = {'predmet': predmet, 'trieda': trieda, 'kapitola': KAPITOLA, 'fileid': FILEID}
   return {
      'savemarks': ('POST', f'/admin/savemarks/{KLUC}', {**zaklad, 'dat': DAT}),
      'importmanual': ('POST', f'/admin/ai/importmanual/{KLUC}', zaklad),
      'groupstatistics': ('POST', '/admin/groupstatistics', zaklad),
      'setrevealed': ('POST', '/admin/setrevealed', {**zaklad, 'odhalene': '1'}),
      'regeneratetests': ('POST', '/admin/regeneratetests', zaklad),
      'changetime': ('POST', '/admin/changetime', zaklad),
      'downloadtests': ('POST', '/admin/downloadtests', zaklad),
      'downloadresults': ('POST', '/admin/downloadresults', zaklad),
      'downloadcodes': ('POST', '/admin/downloadcodes', zaklad),
   }

@pytest.mark.parametrize('trasa', ['savemarks', 'importmanual', 'feedbackreport', 'groupstatistics', 'createtests', 'setrevealed', 'regeneratetests', 'changetime', 'downloadtests', 'downloadresults', 'downloadcodes', 'deletetests'])
@pytest.mark.parametrize('predmet, trieda', [('../../../../utok', TRIEDA), (PREDMET, '/../x'), (PREDMET + '\n', TRIEDA)])
def test_trasy_odmietnu_neplatne_parametre_pred_zapisom(trasa, predmet, trieda, tmp_path):
   zaklad = {'predmet': predmet, 'trieda': trieda, 'kapitola': KAPITOLA, 'fileid': FILEID}
   metoda, url, data = {
      **_trasy_sady(predmet, trieda),
      'deletetests': ('DELETE', '/admin/deletetests', zaklad),
      'feedbackreport': ('POST', '/admin/feedbackreport', zaklad),
      'createtests': ('POST', '/admin/createtests', {**zaklad, 'trieda': [trieda]}),
   }[trasa]
   okolie_pred = set(os.listdir(tmp_path.parent))
   strom_pred = sorted(tmp_path.rglob('*'))
   with http() as klient:
      odpoved = klient.request(metoda, url, data=data)
   assert odpoved.status_code == 400
   assert 'Neplatný parameter' in odpoved.json()['detail']
   assert set(os.listdir(tmp_path.parent)) == okolie_pred
   assert sorted(tmp_path.rglob('*')) == strom_pred

@pytest.mark.parametrize('trasa', ['savemarks', 'importmanual', 'groupstatistics', 'setrevealed', 'regeneratetests', 'changetime', 'downloadtests', 'downloadresults', 'downloadcodes'])
def test_trasy_sady_neexistujucu_sadu_odmietnu_404_a_nic_nevytvoria(trasa, tmp_path):
   metoda, url, data = _trasy_sady(PREDMET, TRIEDA)[trasa]
   strom_pred = sorted(tmp_path.rglob('*'))
   with http() as klient:
      odpoved = klient.request(metoda, url, data=data)
   assert odpoved.status_code == 404
   assert sorted(tmp_path.rglob('*')) == strom_pred

@pytest.mark.parametrize('predmet', ['../../../../utok', 'pit3', 'MAT\n', '*'])
def test_showquestions_odmietne_neplatny_predmet(predmet, tmp_path):
   okolie_pred = set(os.listdir(tmp_path.parent))
   with http(user='ucitel') as klient:
      odpoved = klient.post('/admin/showquestions', data={'predmet': predmet})
   assert odpoved.status_code == 400
   assert 'Skratka predmetu' in odpoved.json()['detail']
   assert set(os.listdir(tmp_path.parent)) == okolie_pred


# --- write_odhalene ---

ANSWERS_DVA_XML = """\
<?xml version='1.0' encoding='utf-8'?>
<odpovede xml:lang="sk">
   <test id="T1" dat="2026-01-01T10:00:00"/>
   <test id="T2" dat="2026-01-01T10:05:00" odhalene="1"/>
</odpovede>
"""


def _odhalene(cesta, kluc):
   test = ET.parse(str(cesta)).find(f'.//test[@id="{kluc}"]')
   assert test is not None
   return test.get('odhalene')


def test_write_odhalene_jeden_test(tmp_path):
   cesta = tmp_path / 'a.xml'
   cesta.write_text(ANSWERS_DVA_XML, encoding='utf-8')
   zmenene = write_odhalene(FileLock(f'{cesta}.lock'), cesta, True, {'T1', 'T2'}, 'T1')
   assert zmenene == ['T1']
   assert _odhalene(cesta, 'T1') == '1'


def test_write_odhalene_test_pred_koncom_vrati_409(tmp_path):
   cesta = tmp_path / 'a.xml'
   cesta.write_text(ANSWERS_DVA_XML, encoding='utf-8')
   with pytest.raises(HTTPException) as e:
      write_odhalene(FileLock(f'{cesta}.lock'), cesta, True, set(), 'T1')
   assert e.value.status_code == 409
   assert _odhalene(cesta, 'T1') is None


def test_write_odhalene_neznamy_kluc_vrati_404(tmp_path):
   cesta = tmp_path / 'a.xml'
   cesta.write_text(ANSWERS_DVA_XML, encoding='utf-8')
   with pytest.raises(HTTPException) as e:
      write_odhalene(FileLock(f'{cesta}.lock'), cesta, True, {'T1'}, 'X')
   assert e.value.status_code == 404


def test_write_odhalene_cela_sada_odhali_len_skoncene(tmp_path):
   cesta = tmp_path / 'a.xml'
   cesta.write_text(ANSWERS_DVA_XML.replace(' odhalene="1"', ''), encoding='utf-8')
   zmenene = write_odhalene(FileLock(f'{cesta}.lock'), cesta, True, {'T2'})
   assert zmenene == ['T2']
   assert _odhalene(cesta, 'T1') is None
   assert _odhalene(cesta, 'T2') == '1'


def test_write_odhalene_skrytie_nepotrebuje_skoncene(tmp_path):
   cesta = tmp_path / 'a.xml'
   cesta.write_text(ANSWERS_DVA_XML, encoding='utf-8')
   zmenene = write_odhalene(FileLock(f'{cesta}.lock'), cesta, False, set())
   assert zmenene == ['T2']
   assert _odhalene(cesta, 'T2') is None


# --- oprávnenia na kategórie a pozastavenie ---

KAT_XML = """\
<?xml version='1.0' encoding='utf-8'?>
<kapitola predmet="{predmet}" id="01">
   <kategoria id="{kat}" pocet="1">
      <otazka id="{otazka}"><znenie>x</znenie></otazka>
   </kategoria>
</kapitola>
"""

@pytest.fixture
def banka(tmp_path):
   """Dva predmety (AUT3, MAT) a .perm: ucitel 'petrik' smie upravovat len AUT3."""
   for predmet, kat, otazka in (('AUT3', 'katA', 'otA'), ('MAT', 'katM', 'otM')):
      adresar = tmp_path / 'res/xml/questions' / predmet
      adresar.mkdir(parents=True, exist_ok=True)
      (adresar / f'{predmet}_01.xml').write_text(KAT_XML.format(predmet=predmet, kat=kat, otazka=otazka), encoding='utf-8')
   (tmp_path / '.perm').write_text('petrik: create:AUT3 edit:AUT3 delete:AUT3\n', encoding='utf-8')
   return tmp_path

def _post(url, user='sef', **polia):
   """POST formulara ako dany ucitel cez skutocnu aplikaciu; polia s hodnotou None sa neposlu (ako chybajuce pole)."""
   with http(user=user) as klient:
      return klient.post(url, data={k: v for k, v in polia.items() if v is not None})

def _kategoria_xml(banka, predmet):
   return (banka / f'res/xml/questions/{predmet}/{predmet}_01.xml').read_text(encoding='utf-8')

@pytest.mark.parametrize('operacia', ['update', 'delete', 'restore'])
def test_process_category_opravnenie_podla_predmetu_kategorie_nie_formulara(banka, operacia):
   povodny = _kategoria_xml(banka, 'MAT')
   odpoved = _post('/admin/process_category', user='petrik', predmet='AUT3', operacia=operacia, kategoria_id='katM', pocet='5')
   assert odpoved.status_code == 403
   assert _kategoria_xml(banka, 'MAT') == povodny

def test_process_category_vlastny_predmet_prejde(banka):
   assert _post('/admin/process_category', user='petrik', predmet='AUT3', operacia='update', kategoria_id='katA', pocet='5').status_code == 200
   assert 'pocet="5"' in _kategoria_xml(banka, 'AUT3')

def test_process_category_neexistujuca_kategoria_je_400(banka):
   assert _post('/admin/process_category', user='petrik', predmet='AUT3', operacia='update', kategoria_id='nie').status_code == 400

@pytest.mark.parametrize('typ, id_', [('kategoria', 'katM'), ('otazka', 'otM')])
def test_setpaused_bez_opravnenia_je_403_a_nic_nezmeni(banka, typ, id_):
   povodny = _kategoria_xml(banka, 'MAT')
   assert _post('/admin/setpaused', user='petrik', id=id_, typ=typ, paused='1').status_code == 403
   assert _kategoria_xml(banka, 'MAT') == povodny

@pytest.mark.parametrize('typ, id_', [('kategoria', 'katA'), ('otazka', 'otA')])
def test_setpaused_s_opravnenim_pozastavi(banka, typ, id_):
   assert _post('/admin/setpaused', user='petrik', id=id_, typ=typ, paused='1').status_code == 200
   assert 'paused="1"' in _kategoria_xml(banka, 'AUT3')

def test_setpaused_neexistujuce_je_404(banka):
   assert _post('/admin/setpaused', user='petrik', id='nie', typ='otazka', paused='1').status_code == 404


@pytest.mark.parametrize('typ, id_', [('kategoria', 'katM'), ('otazka', 'otM'), ('kapitola', '01')])
def test_setainapoveda_bez_opravnenia_je_403_a_nic_nezmeni(banka, typ, id_):
   povodny = _kategoria_xml(banka, 'MAT')
   assert _post('/admin/setainapoveda', user='petrik', id=id_, typ=typ, povolene='1', predmet='MAT').status_code == 403
   assert _kategoria_xml(banka, 'MAT') == povodny

@pytest.mark.parametrize('typ, id_', [('kategoria', 'katA'), ('otazka', 'otA'), ('kapitola', '01')])
def test_setainapoveda_s_opravnenim_zapne_a_vypne(banka, typ, id_):
   assert _post('/admin/setainapoveda', user='petrik', id=id_, typ=typ, povolene='1', predmet='AUT3').status_code == 200
   assert 's_napovedou="1"' in _kategoria_xml(banka, 'AUT3')
   assert _post('/admin/setainapoveda', user='petrik', id=id_, typ=typ, povolene='0', predmet='AUT3').status_code == 200
   assert 's_napovedou' not in _kategoria_xml(banka, 'AUT3')

@pytest.mark.parametrize('typ, id_, predmet, status', [
   ('otazka', 'nie', None, 404), ('kategoria', 'nie', None, 404), ('kapitola', 'nie', 'AUT3', 404),
   ('nieco', 'otA', None, 400), ('kapitola', '../x', 'AUT3', 400), ('kapitola', '01', '../x', 400), ('kapitola', '01', None, 400),
])
def test_setainapoveda_chybne_vstupy(banka, typ, id_, predmet, status):
   assert _post('/admin/setainapoveda', user='petrik', id=id_, typ=typ, povolene='1', predmet=predmet).status_code == status


# --- importmanual ---

def _importmanual(data, kluc=KLUC, **parametre):
   zaklad = {'predmet': PREDMET, 'trieda': TRIEDA, 'kapitola': KAPITOLA, 'fileid': FILEID, 'skupina': SKUPINA}
   return _post(f'/admin/ai/importmanual/{kluc}', **{**data, **zaklad, **parametre})

def _odpovede_cesta(tmp_path):
   return tmp_path / 'res/xml/answers' / PREDMET / f'{PREDMET}_{TRIEDA}{SKUPINA}_{KAPITOLA}_{FILEID}.xml'

def test_importmanual_vytvori_subor_odpovedi(tests_file, tmp_path):
   odpoved = _importmanual({'q1': 'a', 'q2': 'bc'})
   assert odpoved.status_code == 200
   xml = ET.parse(str(_odpovede_cesta(tmp_path))).getroot()
   assert [xml.get(a) for a in ('predmet', 'trieda', 'kapitola', 'fileid')] == [PREDMET, TRIEDA, KAPITOLA, FILEID]
   assert [(o.get('id'), o.text) for o in xml.findall(f'test[@id="{KLUC}"]/otazka')] == [('q1', 'a'), ('q2', 'bc')]
   assert xml.find(f'test[@id="{KLUC}"]').get('dat')  # type: ignore[union-attr]

def test_importmanual_aktualizuje_existujucu_odpoved_a_necha_ostatne(tests_file, answers_file, tmp_path):
   _importmanual({'q1': 'd'})
   xml = ET.parse(str(_odpovede_cesta(tmp_path))).getroot()
   assert [(o.get('id'), o.text) for o in xml.findall(f'test[@id="{KLUC}"]/otazka')] == [('q1', 'd'), ('q2', 'b')]

def test_importmanual_nezapisuje_polia_tykajuce_sa_cesty_do_odpovedi(tests_file, tmp_path):
   _importmanual({'predmet': 'x', 'trieda': 'x', 'q1': 'a'})
   xml = ET.parse(str(_odpovede_cesta(tmp_path))).getroot()
   assert [o.get('id') for o in xml.findall(f'test[@id="{KLUC}"]/otazka')] == ['q1']

def test_importmanual_neplatna_cesta_je_400_a_nic_nevytvori(tests_file, tmp_path):
   assert _importmanual({'q1': 'a'}, predmet='../x').status_code == 400
   assert not _odpovede_cesta(tmp_path).exists()


# --- write_answers: zapis na mieste ---

def _otazka(tmp_path_or_file, id_):
   test = ET.parse(str(tmp_path_or_file)).find(f'.//test[@id="{KLUC}"]')
   assert test is not None
   return test.find(f'otazka[@id="{id_}"]')

def _write_answers(cesta, data, kluc=KLUC):
   adresar = f'./res/xml/answers/{PREDMET}'
   write_answers(FileLock(f'{cesta}.lock'), cesta, data, adresar, PREDMET, TRIEDA, SKUPINA, KAPITOLA, FILEID, kluc)

def test_write_answers_necha_odhalene_a_hodnotenie_nezmenenych_odpovedi(answers_file):
   strom = ET.parse(str(answers_file))
   test = strom.find(f'.//test[@id="{KLUC}"]')
   assert test is not None
   test.set('odhalene', '1')
   q1 = test.find('otazka[@id="q1"]')
   assert q1 is not None
   q1.set('body', '3')
   q1.set('koment', 'dobre')
   strom.write(str(answers_file), encoding='utf-8', xml_declaration=True)
   _write_answers(answers_file, {'q1': 'a', 'q2': 'b'})
   test = ET.parse(str(answers_file)).find(f'.//test[@id="{KLUC}"]')
   assert test is not None and test.get('odhalene') == '1'
   q1 = _otazka(answers_file, 'q1')
   assert q1 is not None and [q1.get('body'), q1.get('koment'), q1.text] == ['3', 'dobre', 'a']
   assert test.get('dat') != DAT

def test_write_answers_zmenena_odpoved_zahodi_stare_body_a_komentar(answers_file):
   strom = ET.parse(str(answers_file))
   q1 = strom.find(f'.//test[@id="{KLUC}"]/otazka[@id="q1"]')
   assert q1 is not None
   q1.set('body', '3')
   q1.set('koment', 'dobre')
   strom.write(str(answers_file), encoding='utf-8', xml_declaration=True)
   _write_answers(answers_file, {'q1': 'zmenena'})
   q1 = _otazka(answers_file, 'q1')
   assert q1 is not None and dict(q1.attrib) == {'id': 'q1'} and q1.text == 'zmenena'

def test_write_answers_nezmaze_odpovede_na_otazky_mimo_odoslania(answers_file):
   _write_answers(answers_file, {'q1': 'c'})
   q2 = _otazka(answers_file, 'q2')
   assert q2 is not None and q2.text == 'b'

def test_write_answers_vyprazdnena_odpoved_sa_zapise(answers_file):
   _write_answers(answers_file, {'q1': ''})
   q1 = _otazka(answers_file, 'q1')
   assert q1 is not None and (q1.text or '') == ''

# --- hlavicka suboru odpovedi: hodnoty sa escapuju ---

@pytest.mark.parametrize('autor', ['ucitel', 'Peter "Pišta" <ucitel> & spol.', "o'neil"])
def test_novy_subor_odpovedi_ma_platnu_hlavicku_aj_s_nebezpecnym_autorom(tests_file, tmp_path, autor):
   strom = ET.parse(str(tests_file))
   strom.getroot().set('autor', autor)
   strom.write(str(tests_file), encoding='utf-8', xml_declaration=True)
   cesta = _odpovede_cesta(tmp_path)
   _write_answers(cesta, {'q1': 'a'})
   root = ET.parse(str(cesta)).getroot()
   assert [root.get(a) for a in ('predmet', 'trieda', 'skupina', 'kapitola', 'fileid', 'autor')] == [PREDMET, TRIEDA, SKUPINA, KAPITOLA, FILEID, autor]
   assert root.get('{http://www.w3.org/XML/1998/namespace}lang') == 'sk'

def test_importmanual_novy_subor_ma_platnu_hlavicku_aj_s_nebezpecnym_autorom(tests_file, tmp_path):
   strom = ET.parse(str(tests_file))
   strom.getroot().set('autor', 'A "B" <C> & D')
   strom.write(str(tests_file), encoding='utf-8', xml_declaration=True)
   cesta = _odpovede_cesta(tmp_path)
   write_answers_import(FileLock(f'{cesta}.lock'), cesta, {'q1': 'a'}, KLUC, PREDMET, TRIEDA, SKUPINA, KAPITOLA, FILEID)
   assert ET.parse(str(cesta)).getroot().get('autor') == 'A "B" <C> & D'


# --- chybove hlasky pre ziaka: bez vnutornych podrobnosti ---

TAJNE = '/srv/web/pisomky/res/xml/tajna-cesta.xml'

def test_saveanswers_chyba_zapisu_vrati_obecnu_hlasku(tests_file, monkeypatch):
   import app.routers.testrun as testrun

   def zlyhaj(*args, **kwargs):
      raise OSError(TAJNE)

   monkeypatch.setattr(testrun, 'write_answers', zlyhaj)
   odpoved = _saveanswers({'q1': 'a'})
   assert odpoved.status_code == 400
   assert odpoved.json()['detail'] == 'Odpovede sa nepodarilo uložiť.' and TAJNE not in odpoved.text

def test_saveanswers_chyba_suboru_vrati_obecnu_hlasku(tests_file, monkeypatch):
   from starlette.datastructures import UploadFile

   async def zle_citanie(self, size=-1):
      raise OSError(TAJNE)

   monkeypatch.setattr(UploadFile, 'read', zle_citanie)
   odpoved = _saveanswers({}, [('x.txt', b'obsah')])
   assert odpoved.status_code == 400
   assert odpoved.json()['detail'] == 'Súbor sa nepodarilo uložiť.' and TAJNE not in odpoved.text

def test_stoptime_chyba_vrati_obecnu_hlasku_a_zaloguje_podrobnosti(tests_file, monkeypatch, caplog):
   import app.routers.testrun as testrun

   def zlyhaj(*args, **kwargs):
      raise OSError(TAJNE)

   monkeypatch.setattr(testrun, 'modify_test_xml', zlyhaj)
   with caplog.at_level(logging.ERROR, logger='pisomky'):
      with http() as klient:
         odpoved = klient.post(f'/stoptime/{KLUC}')
   assert odpoved.status_code == 400
   assert odpoved.json()['detail'] == 'Test sa nepodarilo ukončiť.' and TAJNE not in odpoved.text
   assert TAJNE in caplog.text


# --- process_predmet ---

@pytest.fixture
def ucitelia(tmp_path):
   """.perm: 'sef' smie zakladat predmety a mazat MAT; 'petrik' ma len edit:AUT3."""
   (tmp_path / '.perm').write_text('sef: createp:ALL deletep:MAT create:MAT edit:MAT delete:MAT\npetrik: edit:AUT3\n', encoding='utf-8')

def _predmet(operacia, predmet, user='sef'):
   return _post('/admin/process_predmet', user=user, predmet=predmet, operacia=operacia)

def _kod(odpoved):
   return odpoved.status_code

def test_process_predmet_vytvori_adresar(ucitelia, tmp_path):
   assert _kod(_predmet('create', 'NOV4')) == 200
   assert (tmp_path / 'res/xml/questions/NOV4').is_dir()

@pytest.mark.parametrize('user', ['petrik', 'neznamy'])
def test_process_predmet_vytvorenie_bez_opravnenia_je_403(ucitelia, tmp_path, user):
   assert _predmet('create', 'NOV4', user).status_code == 403
   assert not (tmp_path / 'res/xml/questions/NOV4').exists()

@pytest.mark.parametrize('predmet', ['../x', 'a', 'NOV4\n', 'ABCDEFGHIJK'])
def test_process_predmet_neplatna_skratka_je_400(ucitelia, tmp_path, predmet):
   assert _predmet('create', predmet).status_code == 400
   assert not (tmp_path / 'res/xml/questions').exists()

def test_process_predmet_existujuci_je_400(ucitelia, tmp_path):
   _predmet('create', 'NOV4')
   assert _predmet('create', 'NOV4').status_code == 400

def test_process_predmet_zmaze_a_zalohuje(ucitelia, banka_mat):
   assert _kod(_predmet('delete', 'MAT')) == 200
   assert not (banka_mat / 'res/xml/questions/MAT').exists()
   assert list((banka_mat / 'res/xml/archiv').rglob('MAT_*_otazky.tar.xz'))

def test_process_predmet_zmazanie_len_s_pravom_deletep_pre_dany_predmet(ucitelia, banka_mat):
   (banka_mat / 'res/xml/questions/AUT3').mkdir()
   assert _predmet('delete', 'AUT3').status_code == 403     # sef ma deletep len pre MAT
   assert (banka_mat / 'res/xml/questions/AUT3').exists()

def test_process_predmet_pouzity_v_testoch_sa_nezmaze(ucitelia, banka_mat):
   (banka_mat / 'res/xml/tests/MAT').mkdir(parents=True, exist_ok=True)
   (banka_mat / 'res/xml/tests/MAT/MAT_1A_01_ab12.xml').write_text('<testy><test id="K"><otazka id="otM"/></test></testy>', encoding='utf-8')
   assert _predmet('delete', 'MAT').status_code == 400
   assert (banka_mat / 'res/xml/questions/MAT').exists()

def test_process_predmet_neznama_operacia_je_400(ucitelia):
   assert _predmet('premenuj', 'MAT').status_code == 400

@pytest.fixture
def banka_mat(tmp_path):
   adresar = tmp_path / 'res/xml/questions/MAT'
   adresar.mkdir(parents=True)
   (adresar / 'MAT_01.xml').write_text(KAT_XML.format(predmet='MAT', kat='katM', otazka='otM'), encoding='utf-8')
   return tmp_path


# --- process_chapter ---

def _kapitola(operacia, kapitola_id='02', predmet='MAT', user='sef', nazov=None):
   return _post('/admin/process_chapter', user=user, predmet=predmet, kapitola_id=kapitola_id, operacia=operacia, nazov=nazov)

def test_process_chapter_vytvori_premenuje_a_zmaze(ucitelia, banka_mat):
   cesta = banka_mat / 'res/xml/questions/MAT/MAT_02.xml'
   assert _kapitola('create', nazov='Druha').status_code == 200
   assert ET.parse(str(cesta)).getroot().get('nazov') == 'Druha'
   _kapitola('update', nazov='Tretia')
   assert ET.parse(str(cesta)).getroot().get('nazov') == 'Tretia'
   _kapitola('delete')
   assert not cesta.exists()

@pytest.mark.parametrize('operacia', ['create', 'update', 'delete'])
def test_process_chapter_bez_opravnenia_je_403_a_nic_nezmeni(ucitelia, banka_mat, operacia):
   povodny = _kategoria_xml(banka_mat, 'MAT')
   assert _kapitola(operacia, kapitola_id='01' if operacia != 'create' else '07', user='petrik').status_code == 403     # petrik ma edit len pre AUT3
   assert _kategoria_xml(banka_mat, 'MAT') == povodny
   assert not (banka_mat / 'res/xml/questions/MAT/MAT_07.xml').exists()

def test_process_chapter_existujuca_sa_nevytvori_znova(ucitelia, banka_mat):
   assert _kapitola('create', kapitola_id='01').status_code == 400

def test_process_chapter_pouzita_v_testoch_sa_nezmaze(ucitelia, banka_mat):
   (banka_mat / 'res/xml/tests/MAT').mkdir(parents=True, exist_ok=True)
   (banka_mat / 'res/xml/tests/MAT/MAT_1A_01_ab12.xml').write_text('<testy><test id="K"><otazka id="otM"/></test></testy>', encoding='utf-8')
   assert _kapitola('delete', kapitola_id='01').status_code == 400
   assert (banka_mat / 'res/xml/questions/MAT/MAT_01.xml').exists()

def test_process_chapter_neznama_operacia_je_400(ucitelia, banka_mat):
   assert _kapitola('premenuj').status_code == 400


# --- importanswers (AI import, trasa) ---

def test_importanswers_bez_suborov_je_400():
   with http() as klient:
      assert klient.post('/admin/ai/importanswers').status_code == 400

def test_importanswers_spracuje_kazdy_subor_a_vrati_vysledky(monkeypatch):
   import app.routers.importanswers as modul
   poskytovatel = object()
   volania = []

   async def falosne_spracovanie(subor, cache, provider, vysledky):
      volania.append(provider)
      vysledky.append({'subor': subor.filename, 'zapisane': 1})

   monkeypatch.setattr(modul, '_spracuj_subor', falosne_spracovanie)
   with http(ai_provider=poskytovatel) as klient:
      odpoved = klient.post('/admin/ai/importanswers', files=[('obrazky', ('a.png', b'x')), ('obrazky', ('b.pdf', b'y'))])
   assert odpoved.status_code == 200
   assert sorted(v['subor'] for v in odpoved.json()['vysledky']) == ['a.png', 'b.pdf']
   assert volania == [poskytovatel, poskytovatel]


# --- editor otazky: miesto na dopisanie ---

def _process_question(**parametre):
   """POST ako z editora: pole s hodnotou None sa neposle (chybajuce pole), prazdny retazec sa posle ako prazdne pole."""
   zaklad = {'operacia': 'update', 'otazka_id': 'otM', 'znenie': '<znenie>Napíš postup</znenie>', 'body': '1'}
   return _post('/admin/process_question', **{**zaklad, **parametre})

def _get_question(otazka_id='otM'):
   import json
   from app.routers.questions import get_question
   return json.loads(bytes(asyncio.run(get_question(otazka_id)).body))

def test_process_question_ulozi_miesto_a_get_question_ho_vrati(ucitelia, banka_mat):
   _process_question(miesto='4')
   assert _get_question()['miesto'] == '4'
   assert 'riadky="4"' in _kategoria_xml(banka_mat, 'MAT')

def test_process_question_prazdne_miesto_ho_odstrani_a_chybajuce_pole_nemeni(ucitelia, banka_mat):
   _process_question(miesto='4')
   _process_question()                       # stary JS bez pola miesto
   assert _get_question()['miesto'] == '4'
   _process_question(miesto='')
   assert _get_question()['miesto'] is None

@pytest.mark.parametrize('hodnota', ['0', '31', 'abc', '2.5'])
def test_process_question_neplatne_miesto_je_400_a_nic_nezapise(ucitelia, banka_mat, hodnota):
   povodny = _kategoria_xml(banka_mat, 'MAT')
   odpoved = _process_question(miesto=hodnota)
   assert odpoved.status_code == 400 and '1 do 30' in odpoved.json()['detail']
   assert _kategoria_xml(banka_mat, 'MAT') == povodny

def test_process_question_vytvori_otazku_s_miestom(ucitelia, banka_mat):
   odpoved = _process_question(operacia='create', otazka_id=None, kategoria_id='katM', miesto='2')
   nova_id = odpoved.json()['id']
   assert _get_question(nova_id)['miesto'] == '2'

def test_process_question_pouzita_otazka_sa_pri_zmene_len_miesta_nerozvetvi(ucitelia, banka_mat):
   (banka_mat / 'res/xml/tests/MAT').mkdir(parents=True, exist_ok=True)
   (banka_mat / 'res/xml/tests/MAT/MAT_1A_01_ab12.xml').write_text('<testy><test id="K"><otazka id="otM"/></test></testy>', encoding='utf-8')
   odpoved = _process_question(znenie='<znenie>x</znenie>', body='', miesto='5')    # znenie a body ostavaju ako v banke, meni sa len miesto
   assert odpoved.json()['forked'] is False
   assert _get_question()['miesto'] == '5'


# --- process_question cez skutocne HTTP: prazdne pole znamena "odstran", chybajuce "nemen" ---

TABULKA_XML = '<tabulka><riadok><bunka odpoved="1"/></riadok></tabulka>'

@pytest.fixture
def klient(ucitelia, banka_mat):
   with http(user='sef') as k:
      yield k

def _post_otazka(klient, **polia):
   return klient.post('/admin/process_question', data={'operacia': 'update', 'otazka_id': 'otM', 'znenie': '<znenie>x</znenie>', 'body': '1', **polia})

def test_http_prazdne_pole_miesto_odstrani_miesto(klient, banka_mat):
   assert _post_otazka(klient, miesto='3').status_code == 200
   assert 'riadky="3"' in _kategoria_xml(banka_mat, 'MAT')
   assert _post_otazka(klient, miesto='').status_code == 200
   assert '<miesto' not in _kategoria_xml(banka_mat, 'MAT')

def test_http_chybajuce_pole_miesto_ho_nemeni(klient, banka_mat):
   _post_otazka(klient, miesto='3')
   assert _post_otazka(klient).status_code == 200      # stary JS bez pola
   assert 'riadky="3"' in _kategoria_xml(banka_mat, 'MAT')

def test_http_prazdne_pole_tabulka_odstrani_tabulku(klient, banka_mat):
   assert _post_otazka(klient, tabulka=TABULKA_XML, odpovede='[]').status_code == 200
   assert '<tabulka' in _kategoria_xml(banka_mat, 'MAT')
   assert _post_otazka(klient, tabulka='', odpovede='[{"text": "a", "spravna": "1", "napovedy": []}]').status_code == 200
   xml = _kategoria_xml(banka_mat, 'MAT')
   assert '<tabulka' not in xml and '<odpoved' in xml

def test_http_chybajuce_pole_tabulka_ju_nemeni(klient, banka_mat):
   _post_otazka(klient, tabulka=TABULKA_XML, odpovede='[]')
   assert _post_otazka(klient, odpovede='[]').status_code == 200
   assert '<tabulka' in _kategoria_xml(banka_mat, 'MAT')
