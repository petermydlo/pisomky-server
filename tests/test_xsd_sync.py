"""Heuristicka kontrola: nazvy atributov/elementov zapisovane v kode musia
byt deklarovane v niektorom z XSD (res/xsd/*.xsd).

Nekontroluje sa presna typova prislusnost (napr. ktory atribut patri do
ktoreho XSD) - iba to, ci nazov vobec v niektorej schema existuje. Zachytava
presne ten typ chyby, ktory sa uz raz stal: kod zapise novy atribut/element
a nikto nedoplni XSD.

Obmedzenia (vedome, kvoli jednoduchosti):
- neriesi atributy vyberane cez premennu/ternarny operator (napr.
  `param = 'body' if ... else 'koment'; el.set(param, ...)`)
- z XSLT sa skenuje iba res/xslt/createtests.xsl (jediny XSLT subor, ktory
  reálne zapisuje tests.xsd data; ostatne generuju HTML/PDF)
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XSD_DIR = ROOT / 'res' / 'xsd'
XS_NS = '{http://www.w3.org/2001/XMLSchema}'

PY_FILES = [
   ROOT / 'app' / 'utils.py',
   ROOT / 'app' / 'routers' / 'testrun.py',
   ROOT / 'app' / 'routers' / 'results.py',
   ROOT / 'app' / 'routers' / 'importanswers.py',
   ROOT / 'app' / 'routers' / 'ai.py',
]

XSLT_FILES = [
   ROOT / 'res' / 'xslt' / 'createtests.xsl',
]

RE_SET_CALL = re.compile(r"\.set\(\s*['\"]([\w-]+)['\"]")
RE_ATTRIB_DICT = re.compile(r"attrib\s*=\s*\{([^}]*)\}")
RE_DICT_KEY = re.compile(r"['\"]([\w-]+)['\"]\s*:")
RE_ATTR_TUPLE_LOOP = re.compile(r"for\s+\w+\s+in\s+\(\s*((?:['\"][\w-]+['\"][,\s]*)+)\)\s*:")
RE_QUOTED = re.compile(r"['\"]([\w-]+)['\"]")
RE_SUBELEMENT = re.compile(r"ET\.(?:SubElement|Element)\(\s*[^,]+,\s*['\"]([\w-]+)['\"]")

RE_XSL_ATTRIBUTE = re.compile(r'xsl:attribute name="([\w-]+)"')
RE_XSL_SHORTHAND = re.compile(r'\b([a-zA-Z][\w-]*)="\{')


def nazvy_z_xsd() -> set[str]:
   nazvy = set()
   for cesta in sorted(XSD_DIR.glob('*.xsd')):
      root = ET.parse(cesta).getroot()
      for el in root.iter():
         if el.tag in (f'{XS_NS}attribute', f'{XS_NS}element'):
            nazov = el.get('name')
            if nazov:
               nazvy.add(nazov)
   return nazvy


def najdene_v_pythone(cesta: Path) -> set[tuple[str, int]]:
   najdene = set()
   riadky = cesta.read_text(encoding='utf-8').splitlines()
   for i, riadok in enumerate(riadky, start=1):
      for m in RE_SET_CALL.finditer(riadok):
         najdene.add((m.group(1), i))
      for m in RE_ATTRIB_DICT.finditer(riadok):
         for k in RE_DICT_KEY.finditer(m.group(1)):
            najdene.add((k.group(1), i))
      for m in RE_ATTR_TUPLE_LOOP.finditer(riadok):
         for q in RE_QUOTED.finditer(m.group(1)):
            najdene.add((q.group(1), i))
      for m in RE_SUBELEMENT.finditer(riadok):
         najdene.add((m.group(1), i))
   return najdene


def najdene_v_xslt(cesta: Path) -> set[tuple[str, int]]:
   najdene = set()
   riadky = cesta.read_text(encoding='utf-8').splitlines()
   for i, riadok in enumerate(riadky, start=1):
      for m in RE_XSL_ATTRIBUTE.finditer(riadok):
         najdene.add((m.group(1), i))
      for m in RE_XSL_SHORTHAND.finditer(riadok):
         najdene.add((m.group(1), i))
   return najdene


def test_xsd_sync():
   povolene = nazvy_z_xsd()
   chyby = []

   for cesta in PY_FILES:
      for nazov, riadok in sorted(najdene_v_pythone(cesta), key=lambda x: x[1]):
         if nazov not in povolene:
            chyby.append(f'{cesta.relative_to(ROOT)}:{riadok}: "{nazov}" nie je deklarovany v ziadnom res/xsd/*.xsd')

   for cesta in XSLT_FILES:
      for nazov, riadok in sorted(najdene_v_xslt(cesta), key=lambda x: x[1]):
         if nazov not in povolene:
            chyby.append(f'{cesta.relative_to(ROOT)}:{riadok}: "{nazov}" nie je deklarovany v ziadnom res/xsd/*.xsd')

   assert not chyby, (
      'Najdene nazvy atributov/elementov chybajuce v XSD schemach:\n'
      + '\n'.join(f'  {chyba}' for chyba in chyby)
      + '\n\nDoplň chýbajúci atribút/element do príslušného res/xsd/*.xsd, alebo ak ide o falošný poplach zúž/uprav regex v tests/test_xsd_sync.py.'
   )
