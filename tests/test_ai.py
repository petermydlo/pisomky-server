# -*- coding: utf-8 -*-

import logging
import os
import anyio
import pytest
import lxml.etree as ET

from app.routers import ai
from app.routers.ai import (
   _parsuj_hint_keys,
   _spocitaj_napovedy_testu,
   _nacitaj_predchadzajuce_keys,
   _aktualizuj_zapis,
   _uloz_zapis,
   _najdi_napovedu,
   _cache_kluc,
   _cache_ziskaj,
   _cache_uloz,
   _cache_ohodnot,
   _skore_hodnotenia,
   _hlas_cakanie,
   _generuj_napovedu,
   _zamok_napovede,
   _zamok_ziskaj,
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
   assert vysledok['vzory'] == ['3/4']
   assert vysledok['klucove'] == ['zlomky', 'menovateľ']

def test_najdi_napovedu_so_spravnou_odpovedou_zahrnie_naviazanu(questions_file):
   vysledok = _najdi_napovedu(OTAZKA_ID, spravna_odpoved='3/4')
   assert vysledok is not None
   assert set(vysledok['napovedy']) == {'Všeobecná nápoveda k otázke', 'Nápoveda k spoločnému menovateľu'}

def test_najdi_napovedu_bez_extra_udajov(questions_file):
   vysledok = _najdi_napovedu('q_bez_extra')
   assert vysledok == {'napovedy': None, 'vzory': [], 'klucove': []}


CS = './napovedy.json'

# --- cache napoved ---

def test_cache_kluc_stabilny_a_zavisly_od_promptu():
   assert _cache_kluc('sys', 'user') == _cache_kluc('sys', 'user')
   assert _cache_kluc('sys', 'user') != _cache_kluc('sys', 'iny user')
   assert _cache_kluc('sys', 'user') != _cache_kluc('iny sys', 'user')

def test_cache_ziskaj_bez_suboru():
   assert _cache_ziskaj(CS, OTAZKA_ID, 'k1') is None

def test_cache_uloz_a_ziskaj():
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'hint 1', 'a, b')
   _cache_uloz(CS, OTAZKA_ID, 'k2', 'hint 2', '')
   assert _cache_ziskaj(CS, OTAZKA_ID, 'k1') == {'hint': 'hint 1', 'keys': 'a, b', 'skore': 0}
   assert _cache_ziskaj(CS, OTAZKA_ID, 'k2') == {'hint': 'hint 2', 'keys': '', 'skore': 0}
   assert _cache_ziskaj(CS, 'q2', 'k1') is None

def test_cache_uloz_rovnaky_hint_neduplikuje():
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'hint 1', '')
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'hint 1', '')
   assert len(ai._cache_nacitaj(CS)[OTAZKA_ID]['k1']['napovedy']) == 1

def test_cache_ziskaj_vyberie_nahodne_z_poolu():
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'hint 1', '')
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'hint 2', '')
   videne = {_cache_ziskaj(CS, OTAZKA_ID, 'k1')['hint'] for _ in range(60)}  # type: ignore[index]
   assert videne == {'hint 1', 'hint 2'}

def test_cache_ohodnot_dobre_zvysi_skore_a_hint_ostane():
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'hint 1', '')
   _cache_uloz(CS, 'q2', 'k1', 'hint 1', '')
   _cache_ohodnot(CS, OTAZKA_ID, 'hint 1', 1)
   assert ai._cache_nacitaj(CS)[OTAZKA_ID]['k1']['napovedy'] == [{'hint': 'hint 1', 'keys': '', 'skore': 1}]
   assert ai._cache_nacitaj(CS)['q2']['k1']['napovedy'][0]['skore'] == 0

def test_cache_ohodnot_dobre_a_potom_zle_je_neutralne_a_hint_ostane():
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'hint 1', '')
   _cache_ohodnot(CS, OTAZKA_ID, 'hint 1', 1)
   _cache_ohodnot(CS, OTAZKA_ID, 'hint 1', -1)
   assert _cache_ziskaj(CS, OTAZKA_ID, 'k1') == {'hint': 'hint 1', 'keys': '', 'skore': 0}

def test_cache_ohodnot_zle_neohodnotenu_vyhodi_hint():
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'hint 1', '')
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'hint 2', '')
   _cache_ohodnot(CS, OTAZKA_ID, 'hint 1', -1)
   assert [n['hint'] for n in ai._cache_nacitaj(CS)[OTAZKA_ID]['k1']['napovedy']] == ['hint 2']

def test_cache_ohodnot_vyhodi_aj_posledny_hint_a_dalsi_poziadavok_generuje():
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'hint 1', '')
   _cache_ohodnot(CS, OTAZKA_ID, 'hint 1', -1)
   assert _cache_ziskaj(CS, OTAZKA_ID, 'k1') is None
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'hint 2', '')
   assert _cache_ziskaj(CS, OTAZKA_ID, 'k1') == {'hint': 'hint 2', 'keys': '', 'skore': 0}

def test_cache_ohodnot_zmena_hodnotenia_o_dva_body():
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'hint 1', '')
   _cache_ohodnot(CS, OTAZKA_ID, 'hint 1', 1)
   _cache_ohodnot(CS, OTAZKA_ID, 'hint 1', -2)
   assert _cache_ziskaj(CS, OTAZKA_ID, 'k1') is None

def test_cache_ohodnot_neznamy_alebo_prazdny_hint_alebo_nulova_zmena_nic_nemeni():
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'hint 1', '')
   _cache_ohodnot(CS, OTAZKA_ID, 'iny hint', -1)
   _cache_ohodnot(CS, OTAZKA_ID, '', -1)
   _cache_ohodnot(CS, OTAZKA_ID, 'hint 1', 0)
   assert _cache_ziskaj(CS, OTAZKA_ID, 'k1') == {'hint': 'hint 1', 'keys': '', 'skore': 0}

def test_cache_ohodnot_bez_suboru_nespadne():
   _cache_ohodnot(CS, OTAZKA_ID, 'hint 1', -1)

def test_cache_ziskaj_vyberie_z_dobrych_aj_neutralnych():
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'dobry', '')
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'neutralny', '')
   _cache_ohodnot(CS, OTAZKA_ID, 'dobry', 1)
   videne = {_cache_ziskaj(CS, OTAZKA_ID, 'k1')['hint'] for _ in range(60)}  # type: ignore[index]
   assert videne == {'dobry', 'neutralny'}

def test_cache_plny_pool_vyhodi_hint_s_najnizsim_skore():
   for i in range(ai.CACHE_MAX_NAPOVEDI):
      _cache_uloz(CS, OTAZKA_ID, 'k1', f'hint {i}', '')
   _cache_ohodnot(CS, OTAZKA_ID, 'hint 0', 1)
   _cache_ohodnot(CS, OTAZKA_ID, 'hint 1', 1)
   _cache_ohodnot(CS, OTAZKA_ID, 'hint 4', 1)
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'novy', '')
   hinty = [n['hint'] for n in ai._cache_nacitaj(CS)[OTAZKA_ID]['k1']['napovedy']]
   assert len(hinty) == ai.CACHE_MAX_NAPOVEDI
   assert 'hint 2' not in hinty  # the oldest hint with the lowest score
   assert {'hint 0', 'hint 1', 'hint 4', 'hint 3', 'novy'} == set(hinty)

def test_skore_hodnotenia():
   assert [_skore_hodnotenia(v) for v in ('1', '0', '', None, '2')] == [1, -1, 0, 0, 0]

def test_cache_poskodeny_subor_je_prazdna_cache(tmp_path):
   (tmp_path / 'napovedy.json').write_text('{nie json', encoding='utf-8')
   assert _cache_ziskaj(CS, OTAZKA_ID, 'k1') is None
   _cache_uloz(CS, OTAZKA_ID, 'k1', 'hint', '')
   assert _cache_ziskaj(CS, OTAZKA_ID, 'k1') == {'hint': 'hint', 'keys': '', 'skore': 0}

def test_cache_subor_vytvori_sukromny_adresar_a_cestu_na_test(tmp_path, monkeypatch):
   monkeypatch.setattr(ai, 'CACHE_ADRESAR', str(tmp_path / 'cache'))
   cesta = ai._cache_subor('AUT3', 'AB', '', '01', '737f')
   assert cesta == str(tmp_path / 'cache' / 'AUT3_AB_01_737f.json')
   assert (tmp_path / 'cache').stat().st_mode & 0o777 == 0o700

def test_cache_subor_oddeli_testy_a_ocisti_nazov(tmp_path, monkeypatch):
   monkeypatch.setattr(ai, 'CACHE_ADRESAR', str(tmp_path / 'cache'))
   assert ai._cache_subor('AUT3', 'AB', '', '01', '737f') != ai._cache_subor('AUT3', 'AB', '', '01', '9952')
   cesta = ai._cache_subor('../x', 'AB', '/', '01', 'a b')
   assert cesta is not None and os.path.dirname(cesta) == str(tmp_path / 'cache')

def test_cache_subor_nesukromny_adresar_vypne_cache(tmp_path, monkeypatch):
   adresar = tmp_path / 'cache'
   adresar.mkdir()
   adresar.chmod(0o755)
   monkeypatch.setattr(ai, 'CACHE_ADRESAR', str(adresar))
   assert ai._cache_subor('AUT3', 'AB', '', '01', '737f') is None

def test_cache_subor_symlink_vypne_cache(tmp_path, monkeypatch):
   ciel = tmp_path / 'ciel'
   ciel.mkdir(mode=0o700)
   odkaz = tmp_path / 'cache'
   odkaz.symlink_to(ciel)
   monkeypatch.setattr(ai, 'CACHE_ADRESAR', str(odkaz))
   assert ai._cache_subor('AUT3', 'AB', '', '01', '737f') is None

def test_cache_vypnuta_none_nic_nerobi():
   assert _cache_ziskaj(None, OTAZKA_ID, 'k1') is None
   _cache_uloz(None, OTAZKA_ID, 'k1', 'hint', '')
   _cache_ohodnot(None, OTAZKA_ID, 'hint', -1)


# --- _hlas_cakanie / _generuj_napovedu (anyio, oba backendy ako v produkcii) ---

@pytest.fixture(params=['asyncio', 'trio'])
def backend(request):
   return request.param

def test_hlas_cakanie_posiela_caka_do_prveho_chunku(backend):
   async def run():
      send, receive = anyio.create_memory_object_stream[tuple[str, dict]](max_buffer_size=float('inf'))
      prvy_chunk = anyio.Event()
      async with anyio.create_task_group() as tg:
         tg.start_soon(_hlas_cakanie, send, prvy_chunk, 0.05)
         await anyio.sleep(0.18)
         prvy_chunk.set()
      send.close()
      return [u async for u in receive]
   udalosti = anyio.run(run, backend=backend)
   assert len(udalosti) >= 2
   assert all(typ == 'caka' for typ, _ in udalosti)
   assert [d['sekundy'] for _, d in udalosti][:2] == [0, 0]  # int(0.05), int(0.10)

def test_hlas_cakanie_nic_neposle_ak_chunk_pride_hned(backend):
   async def run():
      send, receive = anyio.create_memory_object_stream[tuple[str, dict]](max_buffer_size=float('inf'))
      prvy_chunk = anyio.Event()
      prvy_chunk.set()
      await _hlas_cakanie(send, prvy_chunk, 0.05)
      send.close()
      return [u async for u in receive]
   assert anyio.run(run, backend=backend) == []

class _FalosnyKlient:
   def __init__(self, casti, chyba=None):
      self.casti = casti
      self.chyba = chyba

   async def chat(self, **_):
      if self.chyba:
         raise self.chyba
      casti = self.casti

      async def stream():
         for c in casti:
            yield {'message': {'content': c}}
      return stream()

def _spusti_generovanie(monkeypatch, klient, backend):
   monkeypatch.setattr(ai.ollama, 'AsyncClient', lambda: klient)
   subor = f'./res/xml/feedback/{PREDMET}/{PREDMET}_1A_kap1_ab12.xml'
   _uloz_zapis(subor, 'zapX', OTAZKA_ID, TEST_ID, PREDMET, '1A', '', 'kap1', 'ab12')

   async def run():
      send, receive = anyio.create_memory_object_stream[tuple[str, dict]](max_buffer_size=float('inf'))
      prvy_chunk = anyio.Event()
      await _generuj_napovedu([], subor, 'zapX', send, logging.getLogger('test'), prvy_chunk, CS, OTAZKA_ID, 'kluc1')
      assert prvy_chunk.is_set()
      return [u async for u in receive]
   return anyio.run(run, backend=backend), subor

def test_generuj_napovedu_ulozi_do_cache(monkeypatch, backend):
   klient = _FalosnyKlient(['HINT: Zamyslite sa ', 'nad menovateľom\n', 'KEYS: zlomky, delenie'])
   udalosti, subor = _spusti_generovanie(monkeypatch, klient, backend)
   assert [typ for typ, _ in udalosti] == ['chunk', 'chunk', 'done']
   assert _cache_ziskaj(CS, OTAZKA_ID, 'kluc1') == {'hint': 'Zamyslite sa nad menovateľom', 'keys': 'zlomky, delenie', 'skore': 0}
   zapis = ET.parse(subor).find('.//zapis[@id="zapX"]')
   assert zapis is not None
   assert zapis.findtext('hint') == 'Zamyslite sa nad menovateľom'
   assert zapis.findtext('keys') == 'zlomky, delenie'

def test_generuj_napovedu_chyba_neuklada_do_cache(monkeypatch, backend):
   klient = _FalosnyKlient([], chyba=ConnectionError('ollama nebezi'))
   udalosti, _ = _spusti_generovanie(monkeypatch, klient, backend)
   assert [typ for typ, _ in udalosti] == ['napoveda_error']
   assert _cache_ziskaj(CS, OTAZKA_ID, 'kluc1') is None


# --- zamok nápovedy testu a zrušenie generovania ---

@pytest.fixture
def zamok_adresar(tmp_path, monkeypatch):
   adresar = tmp_path / 'napovedy'
   adresar.mkdir(mode=0o700)
   monkeypatch.setattr(ai, 'CACHE_ADRESAR', str(adresar))

def test_zamok_napovede_je_per_test(zamok_adresar):
   a, b = _zamok_napovede('test_a'), _zamok_napovede('test_b')
   assert a is not None and b is not None
   assert a.lock_file != b.lock_file
   assert a.lock_file == _zamok_napovede('test_a').lock_file  # type: ignore[union-attr]

def test_zamok_napovede_bez_sukromneho_adresara_je_vypnuty(tmp_path, monkeypatch):
   adresar = tmp_path / 'verejny'
   adresar.mkdir(mode=0o755)
   monkeypatch.setattr(ai, 'CACHE_ADRESAR', str(adresar))
   assert _zamok_napovede('test_a') is None

def test_zamok_ziskaj_obsadeny_po_case_vrati_false(zamok_adresar, backend):
   drzitel = _zamok_napovede('test_a')
   assert drzitel is not None
   drzitel.acquire()
   try:
      cakajuci = _zamok_napovede('test_a')
      assert cakajuci is not None
      assert anyio.run(_zamok_ziskaj, cakajuci, 0.1, 0.02, backend=backend) is False
   finally:
      drzitel.release()

def test_zamok_ziskaj_pocka_na_uvolnenie(zamok_adresar, backend):
   drzitel = _zamok_napovede('test_a')
   cakajuci = _zamok_napovede('test_a')
   assert drzitel is not None and cakajuci is not None
   drzitel.acquire()

   async def run():
      async def uvolni():
         await anyio.sleep(0.1)
         drzitel.release()
      async with anyio.create_task_group() as tg:
         tg.start_soon(uvolni)
         return await _zamok_ziskaj(cakajuci, 2, 0.02)
   assert anyio.run(run, backend=backend) is True
   cakajuci.release()

class _VisiacyKlient:
   """Model that never produces any output (a request waiting in the queue of Ollama)."""
   async def chat(self, **_):
      async def stream():
         await anyio.sleep_forever()
         yield {}
      return stream()

def test_generuj_napovedu_zrusenie_pred_prvym_chunkom(monkeypatch, zamok_adresar, backend):
   monkeypatch.setattr(ai.ollama, 'AsyncClient', lambda: _VisiacyKlient())
   subor = f'./res/xml/feedback/{PREDMET}/{PREDMET}_1A_kap1_ab12.xml'
   _uloz_zapis(subor, 'zapX', OTAZKA_ID, TEST_ID, PREDMET, '1A', '', 'kap1', 'ab12')
   zamok = _zamok_napovede(TEST_ID)
   assert zamok is not None
   zamok.acquire()

   async def run():
      send, receive = anyio.create_memory_object_stream[tuple[str, dict]](max_buffer_size=float('inf'))
      zrusenie = anyio.CancelScope()
      async with anyio.create_task_group() as tg:
         tg.start_soon(_generuj_napovedu, [], subor, 'zapX', send, logging.getLogger('test'), anyio.Event(), CS, OTAZKA_ID,
                       'kluc1', zrusenie, zamok)
         await anyio.sleep(0.05)
         zrusenie.cancel()
      return [u async for u in receive]
   assert anyio.run(run, backend=backend) == []
   assert _cache_ziskaj(CS, OTAZKA_ID, 'kluc1') is None
   zapis = ET.parse(subor).find('.//zapis[@id="zapX"]')
   assert zapis is not None  # the hint stays counted for the student
   assert zapis.find('hint') is None
   znovu = _zamok_napovede(TEST_ID)
   assert znovu is not None
   znovu.acquire(timeout=0)  # the lock was released by the cancelled call
   znovu.release()

def test_generuj_napovedu_uvolni_zamok_po_dokonceni(monkeypatch, zamok_adresar, backend):
   zamok = _zamok_napovede(TEST_ID)
   assert zamok is not None
   zamok.acquire()
   klient = _FalosnyKlient(['HINT: Skús to\n', 'KEYS: a'])
   monkeypatch.setattr(ai.ollama, 'AsyncClient', lambda: klient)
   subor = f'./res/xml/feedback/{PREDMET}/{PREDMET}_1A_kap1_ab12.xml'
   _uloz_zapis(subor, 'zapX', OTAZKA_ID, TEST_ID, PREDMET, '1A', '', 'kap1', 'ab12')

   async def run():
      send, _ = anyio.create_memory_object_stream[tuple[str, dict]](max_buffer_size=float('inf'))
      await _generuj_napovedu([], subor, 'zapX', send, logging.getLogger('test'), anyio.Event(), CS, OTAZKA_ID,
                              'kluc1', None, zamok)
   anyio.run(run, backend=backend)
   znovu = _zamok_napovede(TEST_ID)
   assert znovu is not None
   znovu.acquire(timeout=0)
   znovu.release()
