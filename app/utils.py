# -*- coding: utf-8 -*-

import os
import re
import logging
import copy
import glob
import shutil
import hashlib
import tarfile
import tempfile
import textwrap
import subprocess
import datetime as dat
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
import lxml.etree as ET
from pathlib import Path
from queue import Queue, Empty
from filelock import FileLock
from contextlib import contextmanager
from typing import TYPE_CHECKING
from collections.abc import Mapping
if TYPE_CHECKING:
   from collections.abc import Callable, Generator
   from saxonche import PySaxonProcessor, PyXdmNode, PyXsltExecutable

def _xfind(node: ET._Element | ET._ElementTree, expr: str, **kw) -> ET._Element | None:
   """Bezpecny XPath lookup — vracia prvy vysledok alebo None."""
   result = node.xpath(expr, **kw)
   return result[0] if result else None  # type: ignore[return-value,index]

def get_test_metadata(proc: 'PySaxonProcessor', test_node: 'PyXdmNode') -> tuple[str, str, str, str, str]:
   """Vrati predmet, trieda, skupina, kapitola, fileid z rodica test nodu."""
   xp = proc.new_xpath_processor()
   xp.set_context(xdm_item=test_node.get_parent())
   return (
      xp.evaluate_single('string(@predmet)').string_value,
      xp.evaluate_single('string(@trieda)').string_value,
      xp.evaluate_single('string(@skupina)').string_value,
      xp.evaluate_single('string(@kapitola)').string_value,
      xp.evaluate_single('string(@fileid)').string_value,
   )

# --- Konverzie do inych formatov ---

@contextmanager
def _xslt_executable(proc: 'PySaxonProcessor', stylesheet_file: str, xslt_pools: dict) -> 'Generator[PyXsltExecutable, None, None]':
   """Poskytne skompilovanú XSLT šablónu z poolu (alebo skompiluje novú)."""
   pool = xslt_pools.setdefault(stylesheet_file, Queue())
   try:
      executable = pool.get_nowait()
   except Empty:
      xsltproc = proc.new_xslt30_processor()
      executable = xsltproc.compile_stylesheet(stylesheet_file=stylesheet_file)
   try:
      yield executable
   finally:
      executable.clear_parameters()
      pool.put(executable)

def _set_params(proc: 'PySaxonProcessor', executable: 'PyXsltExecutable', params: dict) -> None:
   """Nastavi parametre na skompilovanej XSLT šablóne."""
   for k, v in params.items():
      if isinstance(v, bool):
         executable.set_parameter(k, proc.make_boolean_value(v))
      elif isinstance(v, int):
         executable.set_parameter(k, proc.make_integer_value(v))
      else:
         executable.set_parameter(k, proc.make_string_value(v))

#najdlhsie povolene trvanie jedneho spustenia FOP (s)
FOP_TIMEOUT = 120

def xslt_to_pdf(proc: 'PySaxonProcessor', stylesheet: str, source_file: str | None = None, xdm_node: 'PyXdmNode | None' = None, params: dict | None = None, xslt_pools: dict | None = None) -> 'tempfile._TemporaryFileWrapper':
   """Transformuje xml zdroj s xslt sablonou na pdf subor."""
   if xslt_pools is not None:
      with _xslt_executable(proc, stylesheet, xslt_pools) as executable:
         if params:
            _set_params(proc, executable, params)
         fofile = tempfile.NamedTemporaryFile(suffix='.fo', delete=False)
         if source_file:
            executable.transform_to_file(source_file=source_file, output_file=fofile.name)
         elif xdm_node:
            executable.transform_to_file(xdm_node=xdm_node, output_file=fofile.name)
   else:
      xsltproc = proc.new_xslt30_processor()
      if params:
         for k, v in params.items():
            if isinstance(v, bool):
               xsltproc.set_parameter(k, proc.make_boolean_value(v))
            else:
               xsltproc.set_parameter(k, proc.make_string_value(v))
      executable = xsltproc.compile_stylesheet(stylesheet_file=stylesheet)
      fofile = tempfile.NamedTemporaryFile(suffix='.fo', delete=False)
      if source_file:
         executable.transform_to_file(source_file=source_file, output_file=fofile.name)
      elif xdm_node:
         executable.transform_to_file(xdm_node=xdm_node, output_file=fofile.name)
   pdffile = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
   try:
      subprocess.run(['fop', '-nocs', '-c', './res/config.xml', '-fo', fofile.name, '-pdf', pdffile.name], check=True, timeout=FOP_TIMEOUT)
   except BaseException:
      os.remove(pdffile.name)
      raise
   finally:
      os.remove(fofile.name)
   return pdffile

def xslt_to_string(proc: 'PySaxonProcessor', stylesheet_file: str, source_file: str | None = None, xdm_node: 'PyXdmNode | None' = None, params: dict | None = None, xslt_pools: dict | None = None) -> str:
   """Transformuje xml zdroj s xslt sablonou na retazec."""
   if xslt_pools is not None:
      with _xslt_executable(proc, stylesheet_file, xslt_pools) as executable:
         if params:
            _set_params(proc, executable, params)
         if source_file:
            return executable.transform_to_string(source_file=source_file)
         elif xdm_node:
            return executable.transform_to_string(xdm_node=xdm_node)
         else:
            return executable.call_template_returning_string(None)
   else:
      xsltproc = proc.new_xslt30_processor()
      if params:
         for k, v in params.items():
            if isinstance(v, bool):
               xsltproc.set_parameter(k, proc.make_boolean_value(v))
            elif isinstance(v, int):
               xsltproc.set_parameter(k, proc.make_integer_value(v))
            else:
               xsltproc.set_parameter(k, proc.make_string_value(v))
      executable = xsltproc.compile_stylesheet(stylesheet_file=stylesheet_file)
      if source_file:
         return executable.transform_to_string(source_file=source_file)
      elif xdm_node:
         return executable.transform_to_string(xdm_node=xdm_node)
      else:
         return executable.call_template_returning_string(None)

def xquery_to_string(proc: 'PySaxonProcessor', query_file: str, params: dict | None = None) -> str:
   """Transformuje xquery subor na retazec."""
   xqproc = proc.new_xquery_processor()
   if params:
      for k, v in params.items():
         xqproc.set_parameter(k, proc.make_string_value(v))
   xqproc.set_query_file(query_file)
   result = xqproc.run_query_to_string()
   return result

def normalizuj_vzor(text: str) -> str:
   """Odstrani z vzoru odsadenie pochadzajuce z formatovania XML; relativne
   odsadenie medzi riadkami zostane. Ak vzor zacina na novom riadku za <vzor>,
   odsadenie sa pocita zo vsetkych riadkov, inak len z pokracovacich (prvy je
   hned za tagom).
   """
   zacina_novym_riadkom = re.match(r'[ \t]*\n', text) is not None
   text = re.sub(r'^\s*\n', '', text).rstrip()
   if zacina_novym_riadkom:
      return textwrap.dedent(text)
   prvy, _, zvysok = text.lstrip().partition('\n')
   return prvy + '\n' + textwrap.dedent(zvysok) if zvysok else prvy

# --- Zabezpecenie ID ---
def _hash_category(kategoria: ET._Element, subor_id: str = '') -> str:
   """Vypocita hash kategorie z hashu suboru a hashov jej otazok."""
   hashe = [o.get('id', '') for o in kategoria.findall('otazka')]
   obsah = subor_id + '|' + '|'.join(hashe)
   return hashlib.sha256(obsah.encode('utf-8')).hexdigest()[:8]

def _hash_question(otazka: ET._Element, predmet: str) -> str:
   """Vypocita hash obsahu otazky."""
   parts = [predmet]
   znenie = otazka.find('znenie')
   if znenie is not None:
      parts.append(ET.tostring(znenie, encoding='unicode', method='text'))
   for odpoved in otazka.findall('odpoved'):
      parts.append(odpoved.text or '')
      parts.append(odpoved.get('spravna', '0'))
   parts.append(otazka.get('body', ''))
   parts.append(otazka.get('static', ''))
   parts.append(otazka.get('bonus', ''))
   obsah = '|'.join(parts)
   return hashlib.sha256(obsah.encode('utf-8')).hexdigest()[:8]

def ensure_ids(cesta: str | Path) -> None:
   """Doplni @id do otazok v questions XML ak este nemaju. Bezpecne aj pri subehu."""
   cesta = Path(cesta)
   if not cesta.exists():
      return
   lock = FileLock(str(cesta) + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(str(cesta), xmlParser)
      root = tree.getroot()
      predmet = root.get('predmet','')
      otazky = root.findall('.//otazka')
      kategorie = root.findall('.//kategoria')
      # skontroluj ci vsetky uz maju @id
      if all(o.get('id') for o in otazky) and all(k.get('id') for k in kategorie):
         return
      # vygeneruj hashe, zabezpec unikatnost
      pouzite = set(o.get('id') for o in otazky if o.get('id'))
      for otazka in otazky:
         if otazka.get('id'):
            continue
         h = _hash_question(otazka, predmet)
         # pri kolizii pridaj suffix
         kandidat = h
         counter = 1
         while kandidat in pouzite:
            kandidat = hashlib.sha256(f'{h}{counter}'.encode()).hexdigest()[:8]
            counter += 1
         otazka.set('id', kandidat)
         pouzite.add(kandidat)
      pouzite_kat = set(k.get('id') for k in root.findall('.//kategoria') if k.get('id'))
      for kategoria in root.findall('.//kategoria'):
         if kategoria.get('id'):
            continue
         h = _hash_category(kategoria, cesta.stem)
         kandidat = h
         counter = 1
         while kandidat in pouzite_kat:
            kandidat = hashlib.sha256(f'{h}{counter}'.encode()).hexdigest()[:8]
            counter += 1
         kategoria.set('id', kandidat)
         pouzite_kat.add(kandidat)
      ET.indent(tree, space='   ')
      tree.write(str(cesta), encoding='utf-8', xml_declaration=True, pretty_print=True)

# --- Vyhladavanie a uprava casti testu podla ID ---
def find_chapter(kapitola_id: str, predmet: str | None = None, cache: dict | None = None) -> tuple[ET._Element, str] | tuple[None, None]:
   """Najde koren kapitoly v questions XML podla @id.
   predmet je volitelny filter (napr. 'SXT4') — odporuca sa pouzit,
   pretoze kapitola_id je unikatne len v ramci predmetu.
   Vracia (element, cesta) alebo (None, None).
   """
   if cache is None:
      cache = {}

   cache_key = f'{predmet}:{kapitola_id}' if predmet else kapitola_id

   def _try_file(cesta):
      try:
         tree = ET.parse(cesta)
         root = tree.getroot()
         if root.get('id') == kapitola_id:
            if predmet is None or root.get('predmet') == predmet:
               return (root, cesta)
         return None
      except Exception:
         return None

   # 1. cache
   if cache_key in cache:
      result = _try_file(cache[cache_key])
      if result is not None:
         return result
      del cache[cache_key]

   # 2. hot file
   if cache.get('__hot__'):
      result = _try_file(cache['__hot__'])
      if result is not None:
         cache[cache_key] = cache['__hot__']
         return result

   # 3. full scan — ak mame predmet, skenujeme len jeho adresar
   vzor = f'./res/xml/questions/{predmet}/*.xml' if predmet else './res/xml/questions/**/*.xml'
   # for cesta in glob.iglob(vzor, recursive=not bool(predmet)):
   for cesta in glob.iglob(vzor, recursive=True):
      result = _try_file(cesta)
      if result is not None:
         cache[cache_key] = cesta
         cache['__hot__'] = cesta
         return result

   return None, None

def delete_chapter(kapitola_id: str, predmet: str, cache: dict | None = None) -> bool:
   """Vymaze XML subor kapitoly ak nie je pouzita v tests suboroch.
   Vracia True ak uspech, False ak pouzita alebo nenajdena.
   """
   kapitola, cesta = find_chapter(kapitola_id, predmet, cache)
   if kapitola is None or cesta is None:
      return False
   pouzite = pouzite_otazky()
   if any(o.get('id') in pouzite for o in kapitola.findall('.//otazka[@id]')):
      return False
   Path(cesta).unlink()
   if cache is not None:
      cache.pop(f'{predmet}:{kapitola_id}', None)
   return True

def create_chapter(predmet: str, kapitola_id: str, nazov: str | None = None) -> tuple[str, bool] | tuple[None, bool]:
   """Vytvori novy XML subor kapitoly pre dany predmet.
   Subor bude obsahovat prazdny element pokyny a jednu kategoriu s jednou otazkou.
   Vracia (kapitola_id, True) ak uspech, (None, False) ak subor uz existuje alebo chyba.
   """
   cesta = f'./res/xml/questions/{predmet}/{predmet}_{kapitola_id}.xml'
   if Path(cesta).exists():
      return None, False
   root = ET.Element('kapitola', predmet=predmet, id=kapitola_id)
   if nazov:
      root.set('nazov', nazov)
   tree = ET.ElementTree(root)
   ET.indent(tree, space='   ')
   tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
   return kapitola_id, True

def update_chapter(kapitola_id: str, predmet: str, nazov: str | None, cache: dict | None = None) -> bool:
   """Upravi nazov kapitoly v questions XML.
   Vracia True ak uspech, False ak kapitola nenajdena.
   """
   kapitola, cesta = find_chapter(kapitola_id, predmet, cache)
   if kapitola is None or cesta is None:
      return False
   xmlParser = ET.XMLParser(remove_blank_text=True)
   tree = ET.parse(cesta, xmlParser)
   root = tree.getroot()
   if nazov:
      root.set('nazov', nazov)
   elif 'nazov' in root.attrib:
      del root.attrib['nazov']
   ET.indent(tree, space='   ')
   tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
   return True

_SAFE_PREDMET = re.compile(r'^[A-Z0-9]{2,10}$')
_SAFE_KAPITOLA = re.compile(r'^[A-Za-z0-9_.-]+$')

def over_predmet(predmet: str) -> None:
   """Skontroluje skratku predmetu pred skladanim ciest (fullmatch, lebo `$` by prepustilo koncovy novy riadok). Pri chybe vyhodi ValueError."""
   if not _SAFE_PREDMET.fullmatch(predmet):
      raise ValueError('Skratka predmetu má mať 2 až 10 veľkých písmen alebo číslic.')

def over_id_kapitoly(predmet: str, kapitola_id: str) -> None:
   """Skontroluje skratku predmetu a ID kapitoly, ktore sa skladaju do cesty k suboru (res/xml/questions/...).
   Pri chybe vyhodi ValueError so spravou pre ucitela (fullmatch, lebo `$` by prepustilo koncovy novy riadok). ID smie obsahovat bodku (existuje kapitola 02.5)."""
   over_predmet(predmet)
   if not _SAFE_KAPITOLA.fullmatch(kapitola_id):
      raise ValueError('ID kapitoly smie obsahovať len písmená, číslice, _, - a bodku.')

def create_predmet(predmet: str) -> bool:
   """Vytvori novy adresar pre predmet v res/xml/questions/.
   Vracia True ak uspech, False ak zly format skratky alebo uz existuje.
   """
   if not _SAFE_PREDMET.fullmatch(predmet):
      return False
   cesta = Path(f'./res/xml/questions/{predmet}')
   if cesta.exists():
      return False
   cesta.mkdir(parents=True)
   return True

def _skolsky_rok() -> str:
   """Vrati skolsky rok v tvare 'YYYY-YYYY' (september = zaciatok noveho roka)."""
   dnes = dat.date.today()
   if dnes.month >= 9:
      return f'{dnes.year}-{dnes.year + 1}'
   return f'{dnes.year - 1}-{dnes.year}'

def delete_predmet(predmet: str) -> tuple[bool, str | None]:
   """Zalohuje cely adresar predmetu do res/xml/archiv/ a nasledne ho vymaze.
   Odmietne, ak je akakolvek otazka predmetu pouzita v niektorom tests subore.
   Vracia (True, None) ak uspech, (False, dovod) ak zlyhalo.
   """
   if not _SAFE_PREDMET.fullmatch(predmet):
      return False, 'Neplatný formát skratky predmetu'
   cesta = Path(f'./res/xml/questions/{predmet}')
   if not cesta.is_dir():
      return False, 'Predmet neexistuje'
   pouzite = pouzite_otazky()
   pouzita = any(
      o.get('id') in pouzite
      for subor in cesta.glob('*.xml')
      for o in ET.parse(str(subor)).findall('.//otazka[@id]')
   )
   if pouzita:
      return False, 'Predmet obsahuje otázky použité v testoch, nedá sa vymazať'
   rok = _skolsky_rok()
   archiv_dir = Path(f'./res/xml/archiv/{rok}')
   archiv_dir.mkdir(parents=True, exist_ok=True)
   archiv_subor = archiv_dir / f'{predmet}_{rok}_otazky.tar.xz'
   if archiv_subor.exists():
      return False, 'Záloha otázok pre tento predmet už existuje'
   with tarfile.open(archiv_subor, 'w:xz') as tar:
      tar.add(cesta, arcname=cesta.name)
   shutil.rmtree(cesta)
   return True, None

def find_category(kategoria_id: str, cache: dict | None = None) -> tuple[ET._Element, str] | tuple[None, None]:
   """Najde kategoriu v questions XML podla @id.
   Prehladava vsetky subory v res/xml/questions/, vyuziva cache
   pre rychlejsie opakovane vyhladavanie.
   Vracia (element, cesta) alebo (None, None) ak nenajdena.
   """
   if cache is None:
      cache = {}

   def _try_file(cesta):
      try:
         tree = ET.parse(cesta)
         kategoria = _xfind(tree, ".//kategoria[@id=$id]", id=kategoria_id)
         return (kategoria, cesta) if kategoria is not None else None
      except Exception:
         return None

   # 1. cache
   if kategoria_id in cache:
      result = _try_file(cache[kategoria_id])
      if result is not None:
         return result
      del cache[kategoria_id]

   # 2. hot file
   if cache.get('__hot__'):
      result = _try_file(cache['__hot__'])
      if result is not None:
         cache[kategoria_id] = cache['__hot__']
         return result

   # 3. full scan
   for cesta in glob.iglob('./res/xml/questions/**/*.xml', recursive=True):
      result = _try_file(cesta)
      if result is not None:
         cache[kategoria_id] = cesta
         cache['__hot__'] = cesta
         return result

   return None, None

def update_category(kategoria_id: str, nove_data: Mapping[str, str | None], cache: dict | None = None) -> bool:
   """Upravi atributy kategorie v questions XML. Vsetky polia su volitelne;
   ktorekolvek z nich sa da poslat aj ako None, cim sa existujuci atribut odstrani.
   nove_data je dict, moze obsahovat:
     'pocet'  - string s poctom otazok na vyber, alebo None (odstranit atribut)
     'body'   - string s poctom bodov, alebo None (odstranit atribut)
     'static' - '1', alebo None (odstranit atribut)
     'bonus'  - '1', alebo None (odstranit atribut)
     'nazov'  - string s nazvom kategorie, alebo None (odstranit atribut)
     'deprecated' - '1' (rucne archivovat), alebo None (odstranit atribut)
   Vracia True ak uspech, False ak kategoria nenajdena.
   """
   kategoria, cesta = find_category(kategoria_id, cache)
   if kategoria is None or cesta is None:
      return False
   lock = FileLock(cesta + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      kategoria = _xfind(tree, ".//kategoria[@id=$id]", id=kategoria_id)
      if kategoria is None:
         return False
      for attr in ('pocet', 'body', 'static', 'bonus', 'nazov', 'paused', 'deprecated'):
         if attr in nove_data:
            if nove_data[attr] is None:
               if attr in kategoria.attrib:
                  del kategoria.attrib[attr]
            else:
               kategoria.set(attr, str(nove_data[attr]))
      ET.indent(tree, space='   ')
      tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
   return True

def delete_category(kategoria_id: str, cache: dict | None = None) -> bool:
   """Vymaze kategoriu z questions XML podla @id.
   Ak je ktora otazka pouzita v tests, nastavi @deprecated='1' len na kategorii
   (nie na jej otazkach) namiesto vymazania.
   Vracia True ak uspech, False ak kategoria nenajdena.
   """
   kategoria, cesta = find_category(kategoria_id, cache)
   if kategoria is None or cesta is None:
      return False
   lock = FileLock(cesta + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      kategoria = _xfind(tree, ".//kategoria[@id=$id]", id=kategoria_id)
      if kategoria is None:
         return False
      pouzite = pouzite_otazky()
      pouzita = any(o.get('id') in pouzite for o in kategoria.findall('.//otazka[@id]'))
      if pouzita:
         kategoria.set('deprecated', '1')
      else:
         rodic = kategoria.getparent()
         if rodic is None:
            return False
         rodic.remove(kategoria)
         if cache is not None:
            cache.pop(kategoria_id, None)
      ET.indent(tree, space='   ')
      tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
   return True

def restore_category(kategoria_id: str, cache: dict | None = None) -> bool:
   """Obnovi (odstrani @deprecated) kategoriu v questions XML podla @id.
   Nerobi nic s jej otazkami.
   Vracia True ak uspech, False ak kategoria nenajdena.
   """
   kategoria, cesta = find_category(kategoria_id, cache)
   if kategoria is None or cesta is None:
      return False
   lock = FileLock(cesta + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      kategoria = _xfind(tree, ".//kategoria[@id=$id]", id=kategoria_id)
      if kategoria is None:
         return False
      if 'deprecated' in kategoria.attrib:
         del kategoria.attrib['deprecated']
      ET.indent(tree, space='   ')
      tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
   return True

def add_category(kapitola_id: str, nova_kategoria: dict, za_kategoria_id: str | None = None, predmet: str | None = None, cache: dict | None = None) -> tuple[str | None, bool]:
   """Prida novu kategoriu do kapitoly v questions XML.
   nova_kategoria je dict, moze obsahovat:
     'pocet'    - string s poctom otazok na vyber (povinny)
     'body'     - string s poctom bodov, volitelne
     'static'   - '1', volitelne
     'bonus'    - '1', volitelne
     'nazov'    - string s nazvom kategorie, volitelne
   za_kategoria_id - volitelne, vlozi kategoriu za kategoriu s danym id, inak na koniec.
   Vracia (kategoria_id, True) ak uspech, (None, False) pri chybe.
   """
   kapitola, cesta = find_chapter(kapitola_id, predmet, cache)
   if kapitola is None or cesta is None:
      return None, False
   lock = FileLock(cesta + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      root = tree.getroot()
      el = ET.Element('kategoria')
      for attr in ('pocet', 'body', 'static', 'bonus', 'nazov', 'deprecated'):
         if nova_kategoria.get(attr):
            el.set(attr, nova_kategoria[attr])
      if za_kategoria_id:
         ref = _xfind(root, "kategoria[@id=$id]", id=za_kategoria_id)
         if ref is not None:
            ref.addnext(el)
         else:
            root.append(el)
      else:
         root.append(el)
      ET.indent(tree, space='   ')
      tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
   ensure_ids(cesta)
   tree2 = ET.parse(cesta)
   kategorie = tree2.findall('.//kategoria')
   nova_id = kategorie[-1].get('id') if kategorie else None
   return nova_id, True

#kluce v cache, ktore nie su kluce testov; kluc s tymto menom sa povazuje za nenajdeny
_REZERVOVANE_KLUCE = frozenset({'__hot__', '__chyba__'})
#negativna cache: najviac tolko pamatanych nenajdenych klucov, dlhsie kluce sa nepamataju (utocnik by ich mohol zasypat)
_NENAJDENE_MAX = 1000
_NENAJDENE_MAX_DLZKA_KLUCA = 100

def _otlacok_testov() -> int:
   """Otlacok vsetkych tests XML (cesta, cas zmeny, velkost); zmeni sa, ked subor pribudne, zmizne alebo sa zmeni."""
   polozky = []
   for cesta in glob.iglob('./res/xml/tests/**/*.xml', recursive=True):
      try:
         st = os.stat(cesta)
      except OSError:
         continue
      polozky.append((cesta, st.st_mtime_ns, st.st_size))
   return hash(tuple(sorted(polozky)))

def _nenajdeny_znamy(cache: dict, kluc: str, otlacok: int) -> bool:
   """True, ak sa kluc uz hladal pri tom istom stave tests XML a nenasiel sa (plne prehladavanie by dopadlo rovnako)."""
   return cache.get('__chyba__', {}).get(kluc) == otlacok

def _zapamataj_nenajdeny(cache: dict, kluc: str, otlacok: int) -> None:
   """Otlacok treba vziat PRED prehladavanim: subor, ktory pribudne uprostred, ho pri dalsom hladani zmeni."""
   if len(kluc) > _NENAJDENE_MAX_DLZKA_KLUCA:
      return
   nenajdene = cache.setdefault('__chyba__', {})
   if len(nenajdene) >= _NENAJDENE_MAX:
      nenajdene.clear()
   nenajdene[kluc] = otlacok

def find_test_file(kluc: str, cache: dict | None = None) -> str | None:
   """Najde cestu k tests XML suboru podla kluca testu, vyuziva cache (aj negativnu: kluc, ktory sa nenasiel,
   sa pri nezmenenych tests XML znova neprehladava)."""
   if cache is None:
      cache = {}
   if kluc in _REZERVOVANE_KLUCE:
      return None

   if kluc in cache:
      cesta = cache[kluc]
      if os.path.exists(cesta):
         return cesta
      else:
         del cache[kluc]

   if cache.get('__hot__'):
      cesta = cache['__hot__']
      if os.path.exists(cesta):
         try:
            tree = ET.parse(cesta)
            if tree.xpath(".//test[@id=$id]", id=kluc):
               cache[kluc] = cesta
               return cesta
         except Exception:
            pass

   otlacok = _otlacok_testov()
   if _nenajdeny_znamy(cache, kluc, otlacok):
      return None
   for cesta in glob.iglob(os.path.join('./res/xml/tests/', '**/*.xml'), recursive=True):
      try:
         tree = ET.parse(cesta)
         if tree.xpath(".//test[@id=$id]", id=kluc):
            cache[kluc] = cesta
            cache['__hot__'] = cesta
            return cesta
      except Exception:
         continue

   _zapamataj_nenajdeny(cache, kluc, otlacok)
   return None

def is_used(otazka_id: str) -> bool:
   """Skontroluje ci je otazka pouzita v niektorom tests subore.
   Vracia True ak pouzita, False ak nie.
   """
   for cesta in glob.iglob('./res/xml/tests/**/*.xml', recursive=True):
      try:
         tree = ET.parse(cesta)
         if tree.xpath(".//otazka[@id=$id]", id=otazka_id):
            return True
      except Exception:
         pass
   return False

def pouzite_otazky() -> set[str]:
   """Id vsetkych otazok pouzitych v tests XML, v jednom prechode (is_used v cykle cez otazky by cital vsetky
   subory pre kazdu otazku zvlast)."""
   pouzite: set[str] = set()
   for cesta in glob.iglob('./res/xml/tests/**/*.xml', recursive=True):
      try:
         pouzite.update(str(i) for i in ET.parse(cesta).xpath('//otazka/@id'))  # type: ignore[union-attr]
      except Exception:
         pass
   return pouzite

def find_question(otazka_id: str, cache: dict | None = None) -> tuple[ET._Element, str] | tuple[None, None]:
   """Najde otazku v questions XML podla @id."""
   if cache is None:
      cache = {}

   def _try_file(cesta):
      try:
         tree = ET.parse(cesta)
         otazka = _xfind(tree, ".//otazka[@id=$id]", id=otazka_id)
         return (otazka, cesta) if otazka is not None else None
      except Exception:
         return None

   # 1. cache
   if otazka_id in cache:
      result = _try_file(cache[otazka_id])
      if result is not None:
         return result
      del cache[otazka_id]

   # 2. hot file
   if cache.get('__hot__'):
      result = _try_file(cache['__hot__'])
      if result is not None:
         cache[otazka_id] = cache['__hot__']
         return result

   # 3. full scan
   for cesta in glob.iglob('./res/xml/questions/**/*.xml', recursive=True):
      result = _try_file(cesta)
      if result is not None:
         cache[otazka_id] = cesta
         cache['__hot__'] = cesta
         return result

   return None, None

def _priprav_odpoved_element(text: str, spravna: str | None) -> ET._Element:
   """Vytvori <odpoved> element z textu, ktory moze obsahovat markup tagy
   (bold/italic/underline), rovnaka konvencia ako znenie.
   """
   try:
      el = ET.fromstring(f'<odpoved>{text}</odpoved>')
   except ET.XMLSyntaxError:
      el = ET.Element('odpoved')
      el.text = text
   el.set('spravna', '1' if spravna == '1' else '0')
   return el

def _pridaj_odpovede(otazka: ET._Element, odpovede: list[dict]) -> None:
   """Prida <odpoved> elementy (s markupom) a k nim viazane <napoveda pre="..."> do otazka.
   Kazda odpoved je dict {'text': ..., 'spravna': '1'/'0', 'napovedy': [text, ...]}.
   Odpoved s neprazdnym 'napovedy' dostane vygenerovany napoveda_key ('o1', 'o2', ...
   podla poradia) a kazdy text z 'napovedy' vlastny <napoveda pre="tento kluc"> element
   (viac elementov s rovnakym @pre, ak ma odpoved viac nápovedi).
   """
   for i, odp in enumerate(odpovede, start=1):
      el = _priprav_odpoved_element(odp.get('text', ''), odp.get('spravna'))
      napovedy = odp.get('napovedy') or []
      kluc = f'o{i}'
      if napovedy:
         el.set('napoveda_key', kluc)
      otazka.append(el)
      for text_np in napovedy:
         np_el = ET.SubElement(otazka, 'napoveda')
         np_el.set('pre', kluc)
         np_el.text = text_np

def _pridaj_napovede(otazka: ET._Element, napovede: list[str]) -> None:
   """Prida celoplosne <napoveda> elementy (bez @pre) do otazka."""
   for text in napovede:
      el = ET.SubElement(otazka, 'napoveda')
      el.text = text

def over_tabulku(text: str) -> ET._Element:
   """Skontroluje a normalizuje XML <tabulka> z editora (pozri Tabulka v questions.xsd). Pri chybe vyhodi
   ValueError so spravou pre ucitela; prazdny atribut povolene sa vynecha."""
   try:
      tabulka = ET.fromstring(text.strip(), ET.XMLParser(remove_blank_text=True, remove_comments=True, remove_pis=True))
   except ET.XMLSyntaxError as e:
      raise ValueError(f'Tabuľka nie je platné XML: {e}')
   if tabulka.tag != 'tabulka':
      raise ValueError('Koreňový element musí byť <tabulka>.')
   neznamy = [str(nazov) for nazov in tabulka.attrib if nazov != 'povolene']
   if neznamy:
      raise ValueError(f'Tabuľka nepozná atribút {neznamy[0]}.')
   povolene = tabulka.get('povolene', '')
   if povolene == '' and 'povolene' in tabulka.attrib:
      del tabulka.attrib['povolene']
   hlavicky = [d for d in tabulka if d.tag == 'hlavicka']
   riadky = [d for d in tabulka if d.tag == 'riadok']
   if len(hlavicky) + len(riadky) != len(tabulka):
      raise ValueError('Tabuľka smie obsahovať len <hlavicka> a <riadok>.')
   if len(hlavicky) > 1 or (hlavicky and tabulka[0] is not hlavicky[0]):
      raise ValueError('Hlavička môže byť najviac jedna a musí byť prvá.')
   if not riadky:
      raise ValueError('Tabuľka musí mať aspoň jeden <riadok>.')
   pocty = set()
   pocet_poli = 0
   for riadok in tabulka:
      bunky = list(riadok)
      if not bunky or any(b.tag != 'bunka' for b in bunky):
         raise ValueError(f'<{riadok.tag}> smie obsahovať len <bunka> (aspoň jednu).')
      pocty.add(len(bunky))
      for bunka in bunky:
         if len(bunka):
            raise ValueError('<bunka> nesmie obsahovať ďalšie elementy.')
         neznamy = [str(nazov) for nazov in bunka.attrib if nazov != 'odpoved']
         if neznamy:
            raise ValueError(f'Bunka nepozná atribút {neznamy[0]}.')
         if 'odpoved' in bunka.attrib:
            odpoved = bunka.get('odpoved', '').strip()
            if not odpoved:
               raise ValueError('Atribút odpoved nesmie byť prázdny.')
            if povolene and any(znak not in povolene for znak in odpoved):
               raise ValueError(f'Odpoveď "{odpoved}" obsahuje znak, ktorý nie je medzi povolenými ({povolene}).')
            if (bunka.text or '').strip():
               raise ValueError('Bunka s atribútom odpoved (pole na vyplnenie) nemá mať text.')
            bunka.set('odpoved', odpoved)
            pocet_poli += 1
   if len(pocty) > 1:
      raise ValueError('Všetky riadky (aj hlavička) musia mať rovnaký počet buniek.')
   if pocet_poli == 0:
      raise ValueError('Tabuľka musí mať aspoň jedno pole na vyplnenie (bunka s atribútom odpoved).')
   return tabulka

def serializuj_tabulku(otazka: ET._Element) -> str:
   """Tabulka otazky ako odsadeny XML text pre editor, alebo '' ak ju otazka nema."""
   tabulka = otazka.find('tabulka')
   if tabulka is None:
      return ''
   kopia = copy.deepcopy(tabulka)
   ET.indent(kopia, space='   ')
   return ET.tostring(kopia, encoding='unicode', with_tail=False)

def _vloz_tabulku(otazka: ET._Element, tabulka: ET._Element) -> None:
   """Vlozi <tabulka> hned za <znenie> (alebo na zaciatok otazky)."""
   znenie = otazka.find('znenie')
   otazka.insert(otazka.index(znenie) + 1 if znenie is not None else 0, tabulka)

def _normalizovana_tabulka(tabulka: ET._Element | None) -> str:
   """Tabulka bez odsadenia a bielych znakov, na porovnanie starej a novej verzie."""
   if tabulka is None:
      return ''
   kopia = copy.deepcopy(tabulka)
   if kopia.get('povolene') == '':
      del kopia.attrib['povolene']
   for el in kopia.iter():
      el.tail = None
      el.text = (el.text or '').strip() or None if el.tag == 'bunka' else None
   return ET.tostring(kopia, encoding='unicode')

def _zostav_otazka_element(data: dict) -> ET._Element:
   """Zostavi novy <otazka> element z data dictu (rovnaky tvar ako add_question's
   nova_otazka), bez @id (ten prideli az ensure_ids). Pouziva sa v add_question
   aj fork_question.
   """
   el = ET.Element('otazka')
   for attr in ('body', 'static', 'bonus', 'rating', 'nazov', 'deprecated'):
      if data.get(attr):
         el.set(attr, data[attr])
   if 'znenie' in data:
      znenie_el = ET.fromstring(data['znenie'])
      el.append(znenie_el)
   if data.get('tabulka'):
      _vloz_tabulku(el, over_tabulku(data['tabulka']))
   _pridaj_odpovede(el, data.get('odpovede', []))
   if data.get('napovede'):
      _pridaj_napovede(el, data['napovede'])
   for vzor in data.get('vzory', []):
      vzor_el = ET.SubElement(el, 'vzor')
      vzor_el.text = vzor
   if data.get('klucove_slova'):
      ks_el = ET.SubElement(el, 'klucove_slova')
      for slovo in data['klucove_slova']:
         s_el = ET.SubElement(ks_el, 'slovo')
         s_el.text = slovo
   return el

def _serializuj_obsah(el: ET._Element | None) -> str:
   """Serializuje vnutorny obsah elementu (text + child elementy vratane markupu),
   bez vlastneho tagu/atributov elementu."""
   if el is None:
      return ''
   casti = [el.text or '']
   for dieta in el:
      casti.append(ET.tostring(dieta, encoding='unicode'))
   return ''.join(casti)

def zmenene_zamrznute_polia(otazka_el: ET._Element, data: dict) -> bool:
   """Vrati True, ak by zapis data (z process_question operacia='update') zmenil
   niektore z poli, ktore createtests.xsl kopiruje/zamrazi do vygenerovaneho testu
   (znenie, tabulka, text/spravna odpovedi, body, static, bonus) oproti aktualnemu stavu
   otazka_el. Zmena len vzory/klucove_slova/napoveda (citaju sa zivo pri AI
   napovede, nekopiruju sa do testu) sa nepocita.
   """
   if 'znenie' in data:
      nove_znenie = ET.fromstring(data['znenie']) if data.get('znenie') else None
      if _serializuj_obsah(otazka_el.find('znenie')) != _serializuj_obsah(nove_znenie):
         return True
   for attr in ('body', 'static', 'bonus'):
      if attr in data and (otazka_el.get(attr) or None) != (data[attr] or None):
         return True
   if 'tabulka' in data:
      nova_tabulka = over_tabulku(data['tabulka']) if data['tabulka'] else None
      if _normalizovana_tabulka(otazka_el.find('tabulka')) != _normalizovana_tabulka(nova_tabulka):
         return True
   if 'odpovede' in data:
      stare = tuple((_serializuj_obsah(o), o.get('spravna') or '0') for o in otazka_el.findall('odpoved'))
      nove = tuple((odp.get('text') or '', odp.get('spravna') or '0') for odp in data['odpovede'])
      if stare != nove:
         return True
   return False

def update_question(otazka_id: str, nove_data: dict, cache: dict | None = None) -> bool:
   """Upravi atributy a obsah otazky v questions XML. Atributy body/static/bonus/nazov
   su volitelne; ktorykolvek z nich sa da poslat aj ako None, cim sa existujuci atribut
   odstrani.
   nove_data je dict, moze obsahovat:
     'znenie'    - novy XML string obsahu znenia (napr. '<znenie>text</znenie>')
     'body'      - string s poctom bodov, alebo None (odstranit atribut)
     'static'    - '1', alebo None (odstranit atribut)
     'bonus'     - '1', alebo None (odstranit atribut)
     'rating'    - '1' (hodnotenie hviezdickami), alebo None (odstranit atribut)
     'nazov'     - string s nazvom otazky, alebo None (odstranit atribut)
     'deprecated' - '1' (rucne archivovat), alebo None (odstranit atribut)
     'odpovede'  - list dictov [{'text': ..., 'spravna': '1'/'0', 'napovedy': [text, ...]}, ...]
     'tabulka'   - XML string <tabulka>, alebo '' (tabulku odstranit); bez kluca sa tabulka nemeni
     'napovede'  - list textov celoplosnych napovedi (bez @pre)
     'vzory'     - list vzorovych odpovedi (alternativy, kazda moze byt viacriadkova)
   Vracia True ak uspech, False ak otazka nenajdena.
   """
   otazka, cesta = find_question(otazka_id, cache)
   if otazka is None or cesta is None:
      return False
   lock = FileLock(cesta + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      otazka = _xfind(tree, ".//otazka[@id=$id]", id=otazka_id)
      if otazka is None:
         return False
      # atributy
      for attr in ('body', 'static', 'bonus', 'rating', 'nazov', 'paused', 'deprecated'):
         if attr in nove_data:
            if nove_data[attr] is None:
               if attr in otazka.attrib:
                  del otazka.attrib[attr]
            else:
               otazka.set(attr, nove_data[attr])
      # znenie
      if 'znenie' in nove_data:
         stare = otazka.find('znenie')
         if stare is not None:
            otazka.remove(stare)
         nove_znenie = ET.fromstring(nove_data['znenie'])
         otazka.insert(0, nove_znenie)
      # tabulka
      if 'tabulka' in nove_data:
         for stara_tabulka in otazka.findall('tabulka'):
            otazka.remove(stara_tabulka)
         if nove_data['tabulka']:
            _vloz_tabulku(otazka, over_tabulku(nove_data['tabulka']))
      # odpovede
      if 'odpovede' in nove_data:
         for old in otazka.findall('napoveda'):
            if 'pre' in old.attrib:
               otazka.remove(old)
         for old in otazka.findall('odpoved'):
            otazka.remove(old)
         _pridaj_odpovede(otazka, nove_data['odpovede'])
      # napovede (celoplosne, bez @pre)
      if 'napovede' in nove_data:
         for old in otazka.findall('napoveda'):
            if 'pre' not in old.attrib:
               otazka.remove(old)
         _pridaj_napovede(otazka, nove_data['napovede'])
      # vzory (viac vzorov = alternativy)
      if 'vzory' in nove_data:
         for stary in otazka.findall('vzor'):
            otazka.remove(stary)
         for vzor in nove_data['vzory']:
            el = ET.SubElement(otazka, 'vzor')
            el.text = vzor
      # klucove_slova
      if 'klucove_slova' in nove_data:
         stare = otazka.find('klucove_slova')
         if stare is not None:
            otazka.remove(stare)
         if nove_data['klucove_slova']:
            ks_el = ET.SubElement(otazka, 'klucove_slova')
            for slovo in nove_data['klucove_slova']:
               s_el = ET.SubElement(ks_el, 'slovo')
               s_el.text = slovo

      ET.indent(tree, space='   ')
      tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
   return True

def delete_question(otazka_id: str, cache: dict | None = None) -> bool:
   """Vymaze otazku z questions XML podla @id.
   Ak je otazka pouzita v tests, nastavi @deprecated='1' namiesto vymazania.
   Vracia True ak uspech, False ak otazka nenajdena.
   """
   otazka, cesta = find_question(otazka_id, cache)
   if otazka is None or cesta is None:
      return False
   lock = FileLock(cesta + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      otazka = _xfind(tree, ".//otazka[@id=$id]", id=otazka_id)
      if otazka is None:
         return False
      if is_used(otazka_id):
         otazka.set('deprecated', '1')
      else:
         rodic = otazka.getparent()
         if rodic is None:
            return False
         rodic.remove(otazka)
         if cache is not None:
            cache.pop(otazka_id, None)
      ET.indent(tree, space='   ')
      tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
   return True

def restore_question(otazka_id: str, cache: dict | None = None) -> bool:
   """Obnovi (odstrani @deprecated) otazku v questions XML podla @id.
   Nerobi nic s jej rodicovskou kategoriou.
   Vracia True ak uspech, False ak otazka nenajdena.
   """
   otazka, cesta = find_question(otazka_id, cache)
   if otazka is None or cesta is None:
      return False
   lock = FileLock(cesta + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      otazka = _xfind(tree, ".//otazka[@id=$id]", id=otazka_id)
      if otazka is None:
         return False
      if 'deprecated' in otazka.attrib:
         del otazka.attrib['deprecated']
      ET.indent(tree, space='   ')
      tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
   return True

def add_question(kategoria_id: str, nova_otazka: dict, za_otazka_id: str | None = None, cache: dict | None = None) -> tuple[str | None, bool]:
   """Prida novu otazku do kategorie v questions XML.
   nova_otazka je dict, moze obsahovat:
     'znenie'   - XML string obsahu znenia (povinny)
     'body'     - string s poctom bodov, volitelne
     'static'   - '1', volitelne
     'bonus'    - '1', volitelne
     'rating'   - '1' (hodnotenie hviezdickami), volitelne
     'nazov'    - string s nazvom otazky, volitelne
     'odpovede' - list dictov [{'text': ..., 'spravna': '1'/'0', 'napovedy': [text, ...]}, ...]
     'napovede' - list textov celoplosnych napovedi (bez @pre)
   za_otazka_id - volitelne, vlozi otazku za otazku s danym id, inak na koniec.
   Vracia (otazka_id, True) ak uspech, (None, False) ak kategoria nenajdena.
   """
   kategoria, cesta = find_category(kategoria_id, cache)
   if kategoria is None or cesta is None:
      return None, False
   lock = FileLock(cesta + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      kategoria = _xfind(tree, ".//kategoria[@id=$id]", id=kategoria_id)
      if kategoria is None:
         return None, False
      el = _zostav_otazka_element(nova_otazka)
      if za_otazka_id:
         ref = _xfind(kategoria, "otazka[@id=$id]", id=za_otazka_id)
         if ref is not None:
            ref.addnext(el)
         else:
            kategoria.append(el)
      else:
         kategoria.append(el)
      ET.indent(tree, space='   ')
      tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
   ensure_ids(cesta)
   tree2 = ET.parse(cesta)
   kat2 = _xfind(tree2, ".//kategoria[@id=$id]", id=kategoria_id)
   if kat2 is not None:
      otazky = kat2.findall('otazka')
      nova_id = otazky[-1].get('id') if otazky else None
      return nova_id, True
   return None, True

def fork_question(otazka_id: str, nova_data: dict, cache: dict | None = None) -> str | None:
   """Vytvori novu otazku s upravenym obsahom namiesto zapisu na mieste (fork).
   Pouziva sa pri uprave otazky, ktora je pouzita v testoch (is_used()), aby sa
   nemiesali statistiky pod jednym @id medzi starou a novou verziou. Stara otazka
   dostane @deprecated='1', nova nema ziadnu vazbu na staru (ziadny nahrada_za
   ani autor) - je to bezna nova otazka pridana na koniec tej istej kategorie.
   nova_data ma rovnaky tvar ako add_question's nova_otazka.
   Vracia id novej otazky, alebo None ak sa stara otazka nenajde.
   """
   otazka, cesta = find_question(otazka_id, cache)
   if otazka is None or cesta is None:
      return None
   lock = FileLock(cesta + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      stara = _xfind(tree, ".//otazka[@id=$id]", id=otazka_id)
      if stara is None:
         return None
      kategoria = stara.getparent()
      if kategoria is None:
         return None
      kategoria_id = kategoria.get('id')
      nova = _zostav_otazka_element(nova_data)
      tabulka = stara.find('tabulka')      # formular bez pola tabulka (stary JS v keši) ju necha zo starej otazky
      if tabulka is not None and 'tabulka' not in nova_data:
         _vloz_tabulku(nova, copy.deepcopy(tabulka))
      kategoria.append(nova)
      stara.set('deprecated', '1')
      ET.indent(tree, space='   ')
      tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
   ensure_ids(cesta)
   tree2 = ET.parse(cesta)
   kat2 = _xfind(tree2, ".//kategoria[@id=$id]", id=kategoria_id)
   if kat2 is not None:
      otazky = kat2.findall('otazka')
      return otazky[-1].get('id') if otazky else None
   return None

# --- Testy a cas ---
_SAFE_PARAM = re.compile(r'^[A-Za-z0-9_-]*$')
_SAFE_TRIEDA = re.compile(r'^[A-Za-z0-9_.,-]*$')
#kapitola je len cast nazvu suboru, takze bodka je v poriadku (kapitola 02.5); predmet je v ceste samostatny adresar, tam by '..' vybehlo vyssie
_SAFE_KAPITOLA_PARAM = re.compile(r'^[A-Za-z0-9_.-]*$')

def test_xml_path(predmet: str, trieda: str, skupina: str, kapitola: str, fileid: str) -> str:
   for val in (predmet, fileid):
      if not _SAFE_PARAM.fullmatch(val):
         raise ValueError(f'Neplatný parameter: {val!r}')
   if not _SAFE_KAPITOLA_PARAM.fullmatch(kapitola):
      raise ValueError(f'Neplatný parameter: {kapitola!r}')
   for val in (trieda, skupina):
      if not _SAFE_TRIEDA.fullmatch(val):
         raise ValueError(f'Neplatný parameter: {val!r}')
   return f'./res/xml/tests/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}_{fileid}.xml'

def get_testy_autor(predmet: str, trieda: str, skupina: str, kapitola: str, fileid: str) -> str:
   """Vrati atribut autor z root elementu testy suboru."""
   try:
      return ET.parse(test_xml_path(predmet, trieda, skupina, kapitola, fileid)).getroot().get('autor', '')
   except Exception:
      return ''

def zaloz_subor_odpovedi(cesta: str | Path, predmet: str, trieda: str, skupina: str, kapitola: str, fileid: str) -> None:
   """Vytvori prazdny subor odpovedi sady testov; hodnoty atributov serializuje lxml, takze ich escapuje
   (autor je meno ucitela z hlavicky a nemoze rozbit XML)."""
   atributy = {
      '{http://www.w3.org/XML/1998/namespace}lang': 'sk', 'predmet': predmet, 'trieda': trieda, 'skupina': skupina,
      'kapitola': kapitola, 'fileid': fileid, 'autor': get_testy_autor(predmet, trieda, skupina, kapitola, fileid),
   }
   ET.ElementTree(ET.Element('odpovede', atributy)).write(str(cesta), encoding='utf-8', xml_declaration=True)

def modify_test_xml(cesta: str, callback: 'Callable[[ET._ElementTree], None]') -> None:
   """Upravi xml subor testov podla callbacku."""
   xmlParser = ET.XMLParser(remove_blank_text=True)
   tree = ET.parse(cesta, xmlParser)
   callback(tree)
   ET.indent(tree, space='   ')
   tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)

def find_test(proc: 'PySaxonProcessor', kluc: str, admin: bool = False, cache: dict | None = None) -> 'PyXdmNode | None':
   """Najde test v tests XML podla @id."""
   if cache is None:
      cache = {}
   if kluc in _REZERVOVANE_KLUCE:
      return None
   xsltpath = proc.new_xpath_processor()
   try:
      test_node = None

      def _try_file(filename):
         try:
            node = proc.parse_xml(xml_file_name=filename)
            if node is None:
               return None
            xsltpath.set_context(xdm_item=node)
            return next((t for t in (xsltpath.evaluate('/testy/test') or []) if t.get_attribute_value('id') == kluc), None)
         except Exception:
            return None

      #1. kluc je v cache - ideme priamo na subor
      if kluc in cache:
         filename = cache[kluc]
         test_node = _try_file(filename)
         if test_node is None:
            del cache[kluc]  #subor bol zmazany, odstranime z cache

      #2. kluc nie je v cache - skusime najprv hot_file
      if test_node is None and cache.get('__hot__'):
         test_node = _try_file(cache['__hot__'])
         if test_node is not None:
            cache[kluc] = cache['__hot__']

      #3. full scan ako posledna moznost; kluc, ktory sa pri rovnakom stave tests XML uz nenasiel, sa nehlada znova
      if test_node is None:
         otlacok = _otlacok_testov()
         if _nenajdeny_znamy(cache, kluc, otlacok):
            return None
         for filename in glob.iglob('./res/xml/tests/**/*.xml', recursive=True):
            try:
               node = proc.parse_xml(xml_file_name=filename)
               if node is None:
                  continue
            except Exception as e:
               logging.getLogger('pisomky').warning(f'chyba parsexml {filename}: {e}')
               continue
            xsltpath.set_context(xdm_item=node)
            found = next((t for t in (xsltpath.evaluate('/testy/test') or []) if t.get_attribute_value('id') == kluc), None)
            if found is not None:
               cache[kluc] = filename
               cache['__hot__'] = filename
               test_node = found
               break
         if test_node is None:
            _zapamataj_nenajdeny(cache, kluc, otlacok)

      if test_node is not None and not admin:
         rodic_node = test_node.get_parent()
         if not _check_time_node(test_node, rodic_node):
            return None
      return test_node
   except Exception:
      return None

def check_time(proc: 'PySaxonProcessor', kluc: str) -> bool:
   """Najde platny cas pre test."""
   subor = find_test_file(kluc)
   if not subor:
      return False
   node = proc.parse_xml(xml_file_name=subor)
   xsltpath = proc.new_xpath_processor()
   xsltpath.set_context(xdm_item=node)
   test_node = next((t for t in (xsltpath.evaluate('/testy/test') or []) if t.get_attribute_value('id') == kluc), None)
   if test_node is not None:
      rodic_node = test_node.get_parent()
      return _check_time_node(test_node, rodic_node)
   return False

def _parse_time(node: 'PyXdmNode', attr: str) -> dat.datetime | None:
   try:
      return dat.datetime.fromisoformat(node.get_attribute_value(attr).strip())
   except Exception:
      return None

def _check_time_node(test_node: 'PyXdmNode', rodic_node: 'PyXdmNode') -> bool:
   start = _parse_time(test_node, 'start') or _parse_time(rodic_node, 'start')
   stop = _parse_time(test_node, 'stop') or _parse_time(rodic_node, 'stop')
   teraz = dat.datetime.now()
   return (not start or teraz >= start) and (not stop or teraz <= stop)

def get_time_state(test_node: 'PyXdmNode', rodic_node: 'PyXdmNode') -> str:
   """Vrati 'before', 'during' alebo 'after' podla aktualneho casu voči start/stop."""
   start = _parse_time(test_node, 'start') or _parse_time(rodic_node, 'start')
   stop = _parse_time(test_node, 'stop') or _parse_time(rodic_node, 'stop')
   teraz = dat.datetime.now()
   if start and teraz < start:
      return 'before'
   if stop and teraz > stop:
      return 'after'
   return 'during'

def format_body(body: Decimal) -> str:
   """Body na vypis (zrkadli my:body-text v formatbodov.xsl): 2 desatinne miesta (.5 hore), bez zbytocnych nul,
   desatinna bodka. Vypocty ostavaju nezaokruhlene."""
   text = format(body.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), 'f')
   return text.rstrip('0').rstrip('.') if '.' in text else text

def format_percent(percento: Decimal) -> str:
   """Percenta na vypis (zrkadli my:percent-text): orezane (nie zaokruhlene) na 2 desatinne miesta, aby zobrazena
   hodnota nikdy nebola nad hranicou znamky, ktoru vysledok nedosiahol."""
   text = format(percento.quantize(Decimal('0.01'), rounding=ROUND_FLOOR), 'f')
   return text.rstrip('0').rstrip('.') if '.' in text else text

def body_tabulka(otazka: ET._Element, odpoved: str) -> Decimal:
   """Body za tabulku (zrkadli my:bodytabulka v grading.xsl): @body krat podiel spravnych poli, bez zaokruhlenia.
   Odpoved ziaka je 'hodnota|hodnota|...' v poradi poli v dokumente."""
   spravne = [b.get('odpoved', '') for b in otazka.iterfind('.//tabulka//bunka[@odpoved]')]
   if not spravne:
      return Decimal(0)
   zadane = odpoved.split('|')

   def normalizuj(text: str) -> str:
      return ' '.join(text.split()).lower()

   zhody = sum(1 for i, spravna in enumerate(spravne) if i < len(zadane) and normalizuj(zadane[i]) != '' and normalizuj(zadane[i]) == normalizuj(spravna))
   return Decimal(otazka.get('body', '0')) * zhody / len(spravne)

def _podpis_suboru(cesta: str) -> tuple[int, int]:
   """Cas poslednej zmeny a velkost suboru; zmena kedykolvek po zapise znamena, ze subor treba znova spracovat."""
   st = os.stat(cesta)
   return st.st_mtime_ns, st.st_size

def store_mcq_scores(kluc: str, cache: dict | None = None, hotove: dict | None = None) -> None:
   """Zapise @body pre MCQ a tabulkove otazky do answer XML, ak este nie su zapisane (statistiky citaju
   body len z odpovedi; hodnotenie tabuliek sa aj tak pocita znova v grading.xsl a score.xq).
   `hotove` (kluc -> podpis suboru odpovedi po spracovani, pamat jedneho workera) vynecha zamykanie a parsovanie,
   ak sa subor od posledneho spracovania nezmenil; dopisane odpovede po predlzeni testu ho zmenia, takze sa
   spracuju znova. Chyba sa zaloguje a do `hotove` sa nezapise."""
   test_subor = find_test_file(kluc, cache)
   if not test_subor:
      return
   answer_subor = test_subor.replace('/tests/', '/answers/', 1)
   try:
      if hotove is not None and hotove.get(kluc) == _podpis_suboru(answer_subor):
         return
   except OSError:  #subor odpovedi neexistuje, nie je co zapisovat
      return
   lock = FileLock(f'{answer_subor}.lock')
   try:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      test_node = next(iter(ET.parse(test_subor, xmlParser).xpath('.//test[@id=$id]', id=kluc)), None)  # type: ignore[arg-type]
      if test_node is None:
         return
      with lock:
         answer_tree = ET.parse(answer_subor, xmlParser)
         answer_test = next(iter(answer_tree.xpath('.//test[@id=$id]', id=kluc)), None)  # type: ignore[arg-type]
         if answer_test is not None:
            changed = False
            for otazka in test_node.findall('otazka'):
               if otazka.get('rating'):
                  continue
               odpovedove = otazka.findall('odpoved')
               spravna = ''.join(chr(ord('a') + i) for i, o in enumerate(odpovedove) if o.get('spravna') == '1')
               je_tabulka = otazka.find('tabulka') is not None
               if not spravna and not je_tabulka:
                  continue
               oid = otazka.get('id')
               answer_otazka = next(iter(answer_test.xpath('.//otazka[@id=$id]', id=oid)), None)
               if answer_otazka is None or answer_otazka.get('body') is not None:
                  continue
               if je_tabulka:
                  body = body_tabulka(otazka, answer_otazka.text or '')
               else:
                  student_answer = (answer_otazka.text or '').strip()
                  body = Decimal(otazka.get('body', '0')) if student_answer == spravna else Decimal(0)
               answer_otazka.set('body', format(body, 'f'))
               changed = True
            if changed:
               ET.indent(answer_tree, space='   ')
               answer_tree.write(answer_subor, encoding='utf-8', xml_declaration=True, pretty_print=True)
         if hotove is not None:
            hotove[kluc] = _podpis_suboru(answer_subor)  #pod zamkom, aby zapis ziaka medzi zapisom a podpisom neostal nespracovany
   except Exception as e:
      logging.getLogger('pisomky').error(f'chyba store_mcq_scores {kluc}: {e}')

def je_odhalene(kluc: str, cache: dict | None = None) -> bool:
   """Vrati True, ak ucitel odhalil zakovi spravne odpovede (answers test/@odhalene)."""
   test_subor = find_test_file(kluc, cache)
   if not test_subor:
      return False
   answer_subor = test_subor.replace('/tests/', '/answers/', 1)
   try:
      tree = ET.parse(answer_subor)
   except (OSError, ET.XMLSyntaxError):
      return False
   test = _xfind(tree, './/test[@id=$id]', id=kluc)
   return test is not None and test.get('odhalene') == '1'

def get_score(proc: 'PySaxonProcessor', kluc: str, cache: dict | None = None) -> dict | None:
   """Vypocita skore testu cez XQuery. Vracia dict so ziskane/maximum/percento, alebo None."""
   test_subor = find_test_file(kluc, cache)
   if not test_subor:
      return None
   # Cesty relativne k umiestneniu XQuery suboru (res/xquery/)
   rel = test_subor.removeprefix('./res/')
   test_cesta   = '../' + rel
   answer_cesta = '../' + rel.replace('tests/', 'answers/', 1)
   try:
      params = {'kluc': kluc, 'test_cesta': test_cesta, 'answer_cesta': answer_cesta}
      xml_result = xquery_to_string(proc, './res/xquery/score.xq', params=params)
      node = ET.fromstring(xml_result.encode())
      if node.tag == 'neohodnoteny':
         return None
      znamka_cislo = node.get('znamka', '')
      return {
         'ziskane':  format_body(Decimal(node.get('ziskane', '0'))),
         'maximum':  format_body(Decimal(node.get('maximum', '0'))),
         'percento': format_percent(Decimal(node.get('percento', '0'))),
         'neuplne':  node.get('neuplne') == 'true',
         'znamka':   znamka_cislo or None,
      }
   except Exception:
      return None
