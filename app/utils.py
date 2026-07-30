# -*- coding: utf-8 -*-

import os
import re
import glob
import shutil
import hashlib
import tarfile
import tempfile
import subprocess
import datetime as dat
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
   subprocess.run(['fop', '-nocs', '-c', './res/config.xml', '-fo', fofile.name, '-pdf', pdffile.name], check=True)
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
   pouzita = any(
      is_used(o.get('id') or '')
      for o in kapitola.findall('.//otazka[@id]')
   )
   if pouzita:
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

def create_predmet(predmet: str) -> bool:
   """Vytvori novy adresar pre predmet v res/xml/questions/.
   Vracia True ak uspech, False ak zly format skratky alebo uz existuje.
   """
   if not _SAFE_PREDMET.match(predmet):
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
   if not _SAFE_PREDMET.match(predmet):
      return False, 'Neplatný formát skratky predmetu'
   cesta = Path(f'./res/xml/questions/{predmet}')
   if not cesta.is_dir():
      return False, 'Predmet neexistuje'
   pouzita = any(
      is_used(o.get('id') or '')
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
      pouzita = any(is_used(o.get('id') or '') for o in kategoria.findall('.//otazka[@id]'))
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

def find_test_file(kluc: str, cache: dict | None = None) -> str | None:
   """Najde cestu k tests XML suboru podla kluca testu, vyuziva cache."""
   if cache is None:
      cache = {}

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

   for cesta in glob.iglob(os.path.join('./res/xml/tests/', '**/*.xml'), recursive=True):
      try:
         tree = ET.parse(cesta)
         if tree.xpath(".//test[@id=$id]", id=kluc):
            cache[kluc] = cesta
            cache['__hot__'] = cesta
            return cesta
      except Exception:
         continue

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

def _zostav_otazka_element(data: dict) -> ET._Element:
   """Zostavi novy <otazka> element z data dictu (rovnaky tvar ako add_question's
   nova_otazka), bez @id (ten prideli az ensure_ids). Pouziva sa v add_question
   aj fork_question.
   """
   el = ET.Element('otazka')
   for attr in ('body', 'static', 'bonus', 'nazov', 'deprecated'):
      if data.get(attr):
         el.set(attr, data[attr])
   if 'znenie' in data:
      znenie_el = ET.fromstring(data['znenie'])
      el.append(znenie_el)
   _pridaj_odpovede(el, data.get('odpovede', []))
   if data.get('napovede'):
      _pridaj_napovede(el, data['napovede'])
   if data.get('vzor'):
      vzor_el = ET.SubElement(el, 'vzor')
      vzor_el.text = data['vzor']
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
   (znenie, text/spravna odpovedi, body, static, bonus) oproti aktualnemu stavu
   otazka_el. Zmena len vzor/klucove_slova/napoveda (citaju sa zivo pri AI
   napovede, nekopiruju sa do testu) sa nepocita.
   """
   if 'znenie' in data:
      nove_znenie = ET.fromstring(data['znenie']) if data.get('znenie') else None
      if _serializuj_obsah(otazka_el.find('znenie')) != _serializuj_obsah(nove_znenie):
         return True
   for attr in ('body', 'static', 'bonus'):
      if attr in data and (otazka_el.get(attr) or None) != (data[attr] or None):
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
     'nazov'     - string s nazvom otazky, alebo None (odstranit atribut)
     'deprecated' - '1' (rucne archivovat), alebo None (odstranit atribut)
     'odpovede'  - list dictov [{'text': ..., 'spravna': '1'/'0', 'napovedy': [text, ...]}, ...]
     'napovede'  - list textov celoplosnych napovedi (bez @pre)
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
      for attr in ('body', 'static', 'bonus', 'nazov', 'paused', 'deprecated'):
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
      # vzor
      if 'vzor' in nove_data:
         stary = otazka.find('vzor')
         if stary is not None:
            otazka.remove(stary)
         if nove_data['vzor']:
            el = ET.SubElement(otazka, 'vzor')
            el.text = nove_data['vzor']
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

def test_xml_path(predmet: str, trieda: str, skupina: str, kapitola: str, fileid: str) -> str:
   for val in (predmet, kapitola, fileid):
      if not _SAFE_PARAM.match(val):
         raise ValueError(f'Neplatný parameter: {val!r}')
   for val in (trieda, skupina):
      if not _SAFE_TRIEDA.match(val):
         raise ValueError(f'Neplatný parameter: {val!r}')
   return f'./res/xml/tests/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}_{fileid}.xml'

def get_testy_autor(predmet: str, trieda: str, skupina: str, kapitola: str, fileid: str) -> str:
   """Vrati atribut autor z root elementu testy suboru."""
   try:
      return ET.parse(test_xml_path(predmet, trieda, skupina, kapitola, fileid)).getroot().get('autor', '')
   except Exception:
      return ''

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

      #3. full scan ako posledna moznost
      if test_node is None:
         for filename in glob.iglob('./res/xml/tests/**/*.xml', recursive=True):
            try:
               node = proc.parse_xml(xml_file_name=filename)
               if node is None:
                  continue
            except Exception as e:
               print('chyba parsexml: ' + str(e))
               continue
            xsltpath.set_context(xdm_item=node)
            found = next((t for t in (xsltpath.evaluate('/testy/test') or []) if t.get_attribute_value('id') == kluc), None)
            if found is not None:
               cache[kluc] = filename
               cache['__hot__'] = filename
               test_node = found
               break

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

def store_mcq_scores(kluc: str, cache: dict | None = None) -> None:
   """Zapise @body pre MCQ otazky do answer XML, ak este nie su zapisane."""
   test_subor = find_test_file(kluc, cache)
   if not test_subor:
      return
   answer_subor = test_subor.replace('/tests/', '/answers/', 1)
   if not os.path.exists(answer_subor):
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
         if answer_test is None:
            return
         changed = False
         for otazka in test_node.findall('otazka'):
            if otazka.get('rating'):
               continue
            odpovedove = otazka.findall('odpoved')
            spravna = ''.join(chr(ord('a') + i) for i, o in enumerate(odpovedove) if o.get('spravna') == '1')
            if not spravna:
               continue
            oid = otazka.get('id')
            answer_otazka = next(iter(answer_test.xpath('.//otazka[@id=$id]', id=oid)), None)
            if answer_otazka is None or answer_otazka.get('body') is not None:
               continue
            student_answer = (answer_otazka.text or '').strip()
            body = int(otazka.get('body', 0)) if student_answer == spravna else 0
            answer_otazka.set('body', str(body))
            changed = True
         if changed:
            ET.indent(answer_tree, space='   ')
            answer_tree.write(answer_subor, encoding='utf-8', xml_declaration=True, pretty_print=True)
   except Exception:
      pass

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
         'ziskane':  int(node.get('ziskane', 0)),
         'maximum':  int(node.get('maximum', 0)),
         'percento': int(node.get('percento', 0)),
         'neuplne':  node.get('neuplne') == 'true',
         'znamka':   znamka_cislo or None,
      }
   except Exception:
      return None
