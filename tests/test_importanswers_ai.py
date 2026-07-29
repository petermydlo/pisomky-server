# -*- coding: utf-8 -*-

import asyncio
import io

import pytest
import qrcode
from qrcode.image.pil import PilImage
from PIL import Image
import lxml.etree as ET

from app.routers.importanswers import precitaj_qr_kody, _spracuj_subor

PREDMET = 'MAT'
TRIEDA = '1A'
KAPITOLA = 'kap1'
FILEID = 'ab12'
TEST_ID = 'TEST01'

TESTS_XML = f"""\
<?xml version='1.0' encoding='utf-8'?>
<testy predmet="{PREDMET}" trieda="{TRIEDA}" skupina="" kapitola="{KAPITOLA}" fileid="{FILEID}">
   <test id="{TEST_ID}">
      <otazka id="q1"/>
   </test>
</testy>
"""


def _run(coro):
   return asyncio.run(coro)


def _qr_png(text: str) -> bytes:
   img = qrcode.make(text, image_factory=PilImage)
   buf = io.BytesIO()
   img.save(buf, format='PNG')
   return buf.getvalue()


def _prazdny_png() -> bytes:
   buf = io.BytesIO()
   Image.new('RGB', (100, 100), color='white').save(buf, format='PNG')
   return buf.getvalue()


def _odpovede_subor():
   from pathlib import Path
   return Path(f'./res/xml/answers/{PREDMET}/{PREDMET}_{TRIEDA}_{KAPITOLA}_{FILEID}.xml')


class FakeUpload:
   def __init__(self, filename: str, content_type: str, obsah: bytes):
      self.filename = filename
      self.content_type = content_type
      self._obsah = obsah

   async def read(self) -> bytes:
      return self._obsah


class FakeProvider:
   def __init__(self, test_ids=None, answers=None, test_ids_exc=None, answers_exc=None):
      self._test_ids = test_ids or []
      self._answers = answers or {'tests': []}
      self._test_ids_exc = test_ids_exc
      self._answers_exc = answers_exc
      self.get_test_ids_calls = 0
      self.get_answers_calls = 0

   def get_test_ids(self, obsah, mime_type):
      self.get_test_ids_calls += 1
      if self._test_ids_exc:
         raise self._test_ids_exc
      return self._test_ids

   def get_answers(self, obsah, mime_type, xml_context):
      self.get_answers_calls += 1
      if self._answers_exc:
         raise self._answers_exc
      return self._answers


@pytest.fixture(autouse=True)
def workdir(tmp_path, monkeypatch):
   (tmp_path / 'res/xml/tests' / PREDMET).mkdir(parents=True)
   (tmp_path / 'res/xml/answers' / PREDMET).mkdir(parents=True)
   monkeypatch.chdir(tmp_path)


@pytest.fixture
def tests_file(tmp_path):
   cesta = tmp_path / 'res/xml/tests' / PREDMET / f'{PREDMET}_{TRIEDA}_{KAPITOLA}_{FILEID}.xml'
   cesta.write_text(TESTS_XML, encoding='utf-8')
   return cesta


# --- precitaj_qr_kody ---

def test_precitaj_qr_kody_najde_kod_v_obrazku():
   obsah = _qr_png(TEST_ID)
   assert precitaj_qr_kody(obsah, 'image/png') == [TEST_ID]

def test_precitaj_qr_kody_bez_kodu_vrati_prazdny_zoznam():
   obsah = _prazdny_png()
   assert precitaj_qr_kody(obsah, 'image/png') == []


# --- _spracuj_subor ---

def test_spracuj_subor_qr_najde_id_vynecha_ai_get_test_ids(tests_file):
   obsah = _qr_png(TEST_ID)
   subor = FakeUpload('scan.png', 'image/png', obsah)
   provider = FakeProvider(answers={'tests': [{'test_id': TEST_ID, 'odpovede': [{'id': 'q1', 'odpoved': 'a'}]}]})
   vysledky = []

   _run(_spracuj_subor(subor, {}, provider, vysledky))

   assert provider.get_test_ids_calls == 0
   assert provider.get_answers_calls == 1
   assert vysledky == [{
      'subor': 'scan.png', 'test_id': TEST_ID, 'predmet': PREDMET, 'trieda': TRIEDA,
      'skupina': '', 'kapitola': KAPITOLA, 'fileid': FILEID, 'zapisane': 1, 'nejasnosti': [],
   }]
   tree = ET.parse(str(_odpovede_subor()))
   otazka = tree.find(f'.//test[@id="{TEST_ID}"]/otazka[@id="q1"]')
   assert otazka is not None
   assert otazka.text == 'a'

def test_spracuj_subor_qr_nic_najde_ai_fallback(tests_file):
   obsah = _prazdny_png()
   subor = FakeUpload('scan.png', 'image/png', obsah)
   provider = FakeProvider(test_ids=[TEST_ID], answers={'tests': []})
   vysledky = []

   _run(_spracuj_subor(subor, {}, provider, vysledky))

   assert provider.get_test_ids_calls == 1
   assert provider.get_answers_calls == 1

def test_spracuj_subor_ziadne_id_najdene(tests_file):
   obsah = _prazdny_png()
   subor = FakeUpload('scan.png', 'image/png', obsah)
   provider = FakeProvider(test_ids=[])
   vysledky = []

   _run(_spracuj_subor(subor, {}, provider, vysledky))

   assert provider.get_answers_calls == 0
   assert vysledky == [{'subor': 'scan.png', 'chyba': 'Nenašli sa žiadne ID testov.'}]

def test_spracuj_subor_get_test_ids_vynimka(tests_file):
   obsah = _prazdny_png()
   subor = FakeUpload('scan.png', 'image/png', obsah)
   provider = FakeProvider(test_ids_exc=RuntimeError('AI nedostupné'))
   vysledky = []

   _run(_spracuj_subor(subor, {}, provider, vysledky))

   assert len(vysledky) == 1
   assert vysledky[0]['subor'] == 'scan.png'
   assert 'AI nedostupné' in vysledky[0]['chyba']

def test_spracuj_subor_zadanie_nenajdene_v_db_bez_dalsich_krokov():
   obsah = _qr_png('NEEXISTUJE')
   subor = FakeUpload('scan.png', 'image/png', obsah)
   provider = FakeProvider()
   vysledky = []

   _run(_spracuj_subor(subor, {}, provider, vysledky))

   assert provider.get_answers_calls == 0
   assert vysledky == [{'subor': 'scan.png', 'test_id': 'NEEXISTUJE', 'chyba': 'Zadanie nenájdené v DB'}]

def test_spracuj_subor_get_answers_vynimka(tests_file):
   obsah = _qr_png(TEST_ID)
   subor = FakeUpload('scan.png', 'image/png', obsah)
   provider = FakeProvider(answers_exc=ValueError('zlý JSON'))
   vysledky = []

   _run(_spracuj_subor(subor, {}, provider, vysledky))

   assert len(vysledky) == 1
   assert 'zlý JSON' in vysledky[0]['chyba']

def test_spracuj_subor_zapis_pre_neexistujuci_test_id_v_odpovedi(tests_file):
   obsah = _qr_png(TEST_ID)
   subor = FakeUpload('scan.png', 'image/png', obsah)
   provider = FakeProvider(answers={'tests': [{'test_id': 'INY_NEEXISTUJUCI', 'odpovede': []}]})
   vysledky = []

   _run(_spracuj_subor(subor, {}, provider, vysledky))

   assert vysledky == [{'subor': 'scan.png', 'test_id': 'INY_NEEXISTUJUCI', 'chyba': 'Zadanie nenájdené v DB'}]
