# -*- coding: utf-8 -*-
"""
Testy pre alter/@rozne v createtests.xsl: alter z rovnakej skupiny dostanu v jednom teste rozne hodnoty,
pricom sa beru do uvahy len otazky, ktore ziak naozaj dostal.
"""

import re

import pytest
import lxml.etree as ET
from pathlib import Path
from saxonche import PySaxonProcessor

STYLESHEET = './res/xslt/createtests.xsl'
PREDMET = 'TSTROZNE'

PROJECT_ROOT = Path(__file__).parent.parent
QUESTIONS_DIR = PROJECT_ROOT / 'res/xml/questions' / PREDMET

POCET_ZIAKOV = 24


def _roster(sedenie: bool) -> str:
   """Roster s POCET_ZIAKOV ziakmi, volitelne so sedenim v mriezke 4x6 (skupina g)."""
   ziaci = []
   for i in range(POCET_ZIAKOV):
      sed = f' sedenie="{i // 6 + 1}{"ABCDEF"[i % 6]}"' if sedenie else ''
      ziaci.append(f'      <student meno="Ziak{i}" priezvisko="Priezvisko{i}" skupina="g"{sed}/>')
   return (
      "<?xml version='1.1' encoding='UTF-8'?>\n<triedy>\n   <trieda id=\"III.T\">\n"
      + '\n'.join(ziaci)
      + '\n   </trieda>\n</triedy>\n'
   )


def _omega(n: int) -> str:
   return '<alter rozne="omega">' + ''.join(f'<choice>{i}</choice>' for i in range(1, n + 1)) + '</alter>'


# 01: dve staticke otazky v roznych kategoriach, 3 hodnoty
KAPITOLA_STATICKA = f"""\
<?xml version='1.1' encoding='UTF-8'?>
<kapitola predmet="{PREDMET}" id="01" nazov="Staticka">
   <kategoria id="kat-a" static="1" pocet="1">
      <otazka id="q-a" static="1"><znenie>A ω={_omega(3)}</znenie></otazka>
   </kategoria>
   <kategoria id="kat-b" static="1" pocet="1">
      <otazka id="q-b" static="1"><znenie>B ω={_omega(3)}</znenie></otazka>
   </kategoria>
</kapitola>
"""

# 02: staticka otazka + nestaticka kategoria (vyber 1 z 3), len 2 hodnoty - ak by sa vylucovali
# aj hodnoty z otazok, ktore ziak nedostal, hodnoty by sa vycerpali a mohli by sa zhodovat
KAPITOLA_DYNAMICKA = f"""\
<?xml version='1.1' encoding='UTF-8'?>
<kapitola predmet="{PREDMET}" id="02" nazov="Dynamicka">
   <kategoria id="kat-s" static="1" pocet="1">
      <otazka id="q-s" static="1"><znenie>S ω={_omega(2)}</znenie></otazka>
   </kategoria>
   <kategoria id="kat-d" pocet="1">
      <otazka id="q-d1"><znenie>D1 ω={_omega(2)}</znenie></otazka>
      <otazka id="q-d2"><znenie>D2 ω={_omega(2)}</znenie></otazka>
      <otazka id="q-d3"><znenie>D3 ω={_omega(2)}</znenie></otazka>
   </kategoria>
</kapitola>
"""

# 03: viac alter v skupine nez hodnot - vylucenie sa musi vzdat, nie spadnut
KAPITOLA_VYCERPANA = f"""\
<?xml version='1.1' encoding='UTF-8'?>
<kapitola predmet="{PREDMET}" id="03" nazov="Vycerpana">
   <kategoria id="kat-v" static="1" pocet="3">
      <otazka id="q-v1" static="1"><znenie>V1 ω={_omega(2)}</znenie></otazka>
      <otazka id="q-v2" static="1"><znenie>V2 ω={_omega(2)}</znenie></otazka>
      <otazka id="q-v3" static="1"><znenie>V3 ω={_omega(2)}</znenie></otazka>
   </kategoria>
</kapitola>
"""


@pytest.fixture(scope='module')
def proc():
   with PySaxonProcessor(license=False) as p:
      yield p


@pytest.fixture(autouse=True, scope='module')
def questions_files():
   QUESTIONS_DIR.mkdir(parents=True, exist_ok=True)
   for kapitola, obsah in (('01', KAPITOLA_STATICKA), ('02', KAPITOLA_DYNAMICKA), ('03', KAPITOLA_VYCERPANA)):
      (QUESTIONS_DIR / f'{PREDMET}_{kapitola}.xml').write_text(obsah, encoding='utf-8')
   yield
   for f in QUESTIONS_DIR.glob('*.xml'):
      f.unlink()
   QUESTIONS_DIR.rmdir()


def _transform(proc, zdroj: str, params: dict) -> str:
   xsltproc = proc.new_xslt30_processor()
   for k, v in params.items():
      hodnota = proc.make_boolean_value(v) if isinstance(v, bool) else proc.make_string_value(v)
      xsltproc.set_parameter(k, hodnota)
   xsltproc.set_cwd(str(PROJECT_ROOT))
   executable = xsltproc.compile_stylesheet(stylesheet_file=STYLESHEET)
   return executable.transform_to_string(xdm_node=proc.parse_xml(xml_text=zdroj))


def vytvor(proc, kapitola: str, sedenie: bool, seed: str) -> str:
   return _transform(proc, _roster(sedenie), {
      'seed_ext': seed, 'predmet': PREDMET, 'trieda': 'III.T', 'skupina': 'g', 'kapitola': kapitola,
      'start': '', 'stop': '', 'anonymne': False, 'identita': True, 'fileid': 'test', 'autor': '',
   })


def regeneruj(proc, testy_xml: str, kapitola: str, seed: str) -> str:
   return _transform(proc, testy_xml, {
      'seed_ext': seed, 'predmet': PREDMET, 'kapitola': kapitola, 'fileid': 'test', 'autor': '',
   })


def omegy(testy_xml: str) -> list[tuple[list[str], list[str]]]:
   """Pre kazdy test vrati (id otazok, hodnoty ω v poradi otazok)."""
   koren = ET.fromstring(testy_xml.encode())
   vysledok = []
   for test in koren.iter('test'):
      ids, hodnoty = [], []
      for o in test.findall('otazka'):
         znenie = o.find('znenie')
         assert znenie is not None
         m = re.search(r'ω=(\d+)', ''.join(str(t) for t in znenie.itertext()))
         assert m is not None
         ids.append(o.get('id'))
         hodnoty.append(m.group(1))
      vysledok.append((ids, hodnoty))
   return vysledok


SEEDY = [f'seed{i}' for i in range(5)]


@pytest.mark.parametrize('sedenie', [False, True])
@pytest.mark.parametrize('seed', SEEDY)
def test_staticke_otazky_maju_rozne_omega(proc, sedenie, seed):
   testy = omegy(vytvor(proc, '01', sedenie, seed))
   assert len(testy) == POCET_ZIAKOV
   for ids, hodnoty in testy:
      assert sorted(ids) == ['q-a', 'q-b']
      assert len(set(hodnoty)) == 2, hodnoty


@pytest.mark.parametrize('sedenie', [False, True])
@pytest.mark.parametrize('seed', SEEDY)
def test_nestaticka_kategoria_berie_len_dostane_otazky(proc, sedenie, seed):
   testy = omegy(vytvor(proc, '02', sedenie, seed))
   dostane = set()
   for ids, hodnoty in testy:
      assert len(ids) == 2
      dostane.update(ids)
      assert len(set(hodnoty)) == 2, (ids, hodnoty)
   # nestaticka otazka sa naozaj losuje (inak by test neoveril nic o nedostanych otazkach)
   assert len(dostane - {'q-s'}) > 1


@pytest.mark.parametrize('seed', SEEDY)
def test_regeneracia_zachova_rozne_omega(proc, seed):
   povodne = vytvor(proc, '02', True, seed)
   for ids, hodnoty in omegy(regeneruj(proc, povodne, '02', seed + 'r')):
      assert len(set(hodnoty)) == 2, (ids, hodnoty)


def test_vycerpana_skupina_nespadne(proc):
   testy = omegy(vytvor(proc, '03', True, 'seed'))
   assert len(testy) == POCET_ZIAKOV
   for ids, hodnoty in testy:
      assert ids == ['q-v1', 'q-v2', 'q-v3']
      # prve dve sa este daju odlisit, tretia uz musi zopakovat jednu z hodnot
      assert hodnoty[0] != hodnoty[1]
      assert set(hodnoty) <= {'1', '2'}
