# -*- coding: utf-8 -*-

import os
import glob
import hashlib
import tempfile
import subprocess
import datetime as dat
import lxml.etree as ET
from pathlib import Path
from queue import Queue, Empty
from filelock import FileLock
from contextlib import contextmanager

def _xfind(node, expr, **kw):
   """Bezpecny XPath lookup — vracia prvy vysledok alebo None."""
   result = node.xpath(expr, **kw)
   return result[0] if result else None

def get_test_metadata(proc, test_node):
   """Vrati predmet, trieda, skupina, kapitola z rodica test nodu."""
   xp = proc.new_xpath_processor()
   xp.set_context(xdm_item=test_node.get_parent())
   return (
      xp.evaluate_single('string(@predmet)'),
      xp.evaluate_single('string(@trieda)'),
      xp.evaluate_single('string(@skupina)'),
      xp.evaluate_single('string(@kapitola)'),
   )

# --- Konverzie do inych formatov ---

@contextmanager
def _xslt_executable(proc, stylesheet_file, xslt_pools):
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

def _set_params(proc, executable, params):
   """Nastavi parametre na skompilovanej XSLT šablóne."""
   for k, v in params.items():
      if isinstance(v, bool):
         executable.set_parameter(k, proc.make_boolean_value(v))
      else:
         executable.set_parameter(k, proc.make_string_value(v))

def xslt_to_pdf(proc, stylesheet, source_file=None, xdm_node=None, params=None, xslt_pools=None):
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

def xslt_to_string(proc, stylesheet_file, source_file=None, xdm_node=None, params=None, xslt_pools=None):
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
            else:
               xsltproc.set_parameter(k, proc.make_string_value(v))
      executable = xsltproc.compile_stylesheet(stylesheet_file=stylesheet_file)
      if source_file:
         return executable.transform_to_string(source_file=source_file)
      elif xdm_node:
         return executable.transform_to_string(xdm_node=xdm_node)
      else:
         return executable.call_template_returning_string(None)

def xquery_to_string(proc, query_file, params=None):
   """Transformuje xquery subor na retazec."""
   xqproc = proc.new_xquery_processor()
   if params:
      for k, v in params.items():
         xqproc.set_parameter(k, proc.make_string_value(v))
   xqproc.set_query_file(query_file)
   result = xqproc.run_query_to_string()
   return result

# --- Zabezpecenie ID ---
def _hash_category(kategoria, subor_id=''):
   """Vypocita hash kategorie z hashu suboru a hashov jej otazok."""
   hashe = [o.get('id', '') for o in kategoria.findall('otazka')]
   obsah = subor_id + '|' + '|'.join(hashe)
   return hashlib.sha256(obsah.encode('utf-8')).hexdigest()[:8]

def _hash_question(otazka, predmet):
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

def ensure_ids(cesta):
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
def find_chapter(kapitola_id, predmet=None, cache=None):
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

def delete_chapter(kapitola_id, predmet, cache=None):
   """Vymaze XML subor kapitoly ak nie je pouzita v tests suboroch.
   Vracia True ak uspech, False ak pouzita alebo nenajdena.
   """
   kapitola, cesta = find_chapter(kapitola_id, predmet, cache)
   if kapitola is None:
      return False
   pouzita = any(
      is_used(o.get('id'))
      for o in kapitola.findall('.//otazka[@id]')
   )
   if pouzita:
      return False
   Path(cesta).unlink()
   if cache is not None:
      cache.pop(f'{predmet}:{kapitola_id}', None)
   return True

def create_chapter(predmet, kapitola_id, nazov=None):
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

def find_category(kategoria_id, cache=None):
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

def update_category(kategoria_id, nove_data, cache=None):
   """Upravi atributy kategorie v questions XML.
   nove_data je dict, moze obsahovat:
     'pocet'  - string s poctom otazok na vyber
     'body'   - string s poctom bodov
     'static' - '1' alebo None (odstranit atribut)
     'bonus'  - '1' alebo None (odstranit atribut)
   Vracia True ak uspech, False ak kategoria nenajdena.
   """
   kategoria, cesta = find_category(kategoria_id, cache)
   if kategoria is None:
      return False
   lock = FileLock(cesta + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      kategoria = _xfind(tree, ".//kategoria[@id=$id]", id=kategoria_id)
      if kategoria is None:
         return False
      for attr in ('pocet', 'body', 'static', 'bonus', 'paused'):
         if attr in nove_data:
            if nove_data[attr] is None:
               if attr in kategoria.attrib:
                  del kategoria.attrib[attr]
            else:
               kategoria.set(attr, nove_data[attr])
      ET.indent(tree, space='   ')
      tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
   return True

def delete_category(kategoria_id, cache=None):
   """Vymaze kategoriu z questions XML podla @id.
   Ak je ktora otazka pouzita v tests, nastavi @deprecated='1' na kategorii
   aj vsetkych jej otazkach namiesto vymazania.
   Vracia True ak uspech, False ak kategoria nenajdena.
   """
   kategoria, cesta = find_category(kategoria_id, cache)
   if kategoria is None:
      return False
   lock = FileLock(cesta + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      kategoria = _xfind(tree, ".//kategoria[@id=$id]", id=kategoria_id)
      if kategoria is None:
         return False
      pouzita = any(is_used(o.get('id')) for o in kategoria.findall('.//otazka[@id]'))
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

def add_category(kapitola_id, nova_kategoria, za_kategoria_id=None, predmet=None, cache=None):
   """Prida novu kategoriu do kapitoly v questions XML.
   nova_kategoria je dict, moze obsahovat:
     'pocet'    - string s poctom otazok na vyber (povinny)
     'body'     - string s poctom bodov
     'static'   - '1' alebo None
     'bonus'    - '1' alebo None
   za_kategoria_id - volitelne, vlozi kategoriu za kategoriu s danym id, inak na koniec.
   Vracia (kategoria_id, True) ak uspech, (None, False) pri chybe.
   """
   kapitola, cesta = find_chapter(kapitola_id, predmet, cache)
   if kapitola is None:
      return None, False
   lock = FileLock(cesta + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      root = tree.getroot()
      el = ET.Element('kategoria')
      for attr in ('pocet', 'body', 'static', 'bonus'):
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

def find_test_file(kluc, cache=None):
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

def is_used(otazka_id):
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

def find_question(otazka_id, cache=None):
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

def update_question(otazka_id, nove_data, cache=None):
   """Upravi atributy a obsah otazky v questions XML.
   nove_data je dict, moze obsahovat:
     'znenie'    - novy XML string obsahu znenia (napr. '<znenie>text</znenie>')
     'body'      - string s poctom bodov
     'static'    - '1' alebo None (odstranit atribut)
     'bonus'     - '1' alebo None (odstranit atribut)
     'odpovede'  - list dictov [{'text': ..., 'spravna': '1'/'0'}, ...]
   Vracia True ak uspech, False ak otazka nenajdena.
   """
   otazka, cesta = find_question(otazka_id, cache)
   if otazka is None:
      return False
   lock = FileLock(cesta + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      otazka = _xfind(tree, ".//otazka[@id=$id]", id=otazka_id)
      if otazka is None:
         return False
      # atributy
      for attr in ('body', 'static', 'bonus', 'paused'):
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
         for old in otazka.findall('odpoved'):
            otazka.remove(old)
         for odp in nove_data['odpovede']:
            el = ET.SubElement(otazka, 'odpoved')
            el.text = odp.get('text', '')
            if odp.get('spravna') == '1':
               el.set('spravna', '1')
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

def delete_question(otazka_id, cache=None):
   """Vymaze otazku z questions XML podla @id.
   Ak je otazka pouzita v tests, nastavi @deprecated='1' namiesto vymazania.
   Vracia True ak uspech, False ak otazka nenajdena.
   """
   otazka, cesta = find_question(otazka_id, cache)
   if otazka is None:
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

def add_question(kategoria_id, nova_otazka, za_otazka_id=None, cache=None):
   """Prida novu otazku do kategorie v questions XML.
   nova_otazka je dict, moze obsahovat:
     'znenie'   - XML string obsahu znenia (povinny)
     'body'     - string s poctom bodov
     'static'   - '1' alebo None
     'bonus'    - '1' alebo None
     'odpovede' - list dictov [{'text': ..., 'spravna': '1'/'0'}, ...]
   za_otazka_id - volitelne, vlozi otazku za otazku s danym id, inak na koniec.
   Vracia (otazka_id, True) ak uspech, (None, False) ak kategoria nenajdena.
   """
   kategoria, cesta = find_category(kategoria_id, cache)
   if kategoria is None:
      return None, False
   lock = FileLock(cesta + '.lock')
   with lock:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      kategoria = _xfind(tree, ".//kategoria[@id=$id]", id=kategoria_id)
      if kategoria is None:
         return None, False
      el = ET.Element('otazka')
      for attr in ('body', 'static', 'bonus'):
         if nova_otazka.get(attr):
            el.set(attr, nova_otazka[attr])
      if 'znenie' in nova_otazka:
         znenie_el = ET.fromstring(nova_otazka['znenie'])
         el.append(znenie_el)
      for odp in nova_otazka.get('odpovede', []):
         odp_el = ET.SubElement(el, 'odpoved')
         odp_el.text = odp.get('text', '')
         if odp.get('spravna') == '1':
            odp_el.set('spravna', '1')
      if nova_otazka.get('vzor'):
         vzor_el = ET.SubElement(el, 'vzor')
         vzor_el.text = nova_otazka['vzor']
      if nova_otazka.get('klucove_slova'):
         ks_el = ET.SubElement(el, 'klucove_slova')
         for slovo in nova_otazka['klucove_slova']:
            s_el = ET.SubElement(ks_el, 'slovo')
            s_el.text = slovo
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

# --- Testy a cas ---
def modify_test_xml(predmet, trieda, skupina, kapitola, callback):
   """Najde spravny xml subor a upravy ho podla parametrov."""
   cesta = f'./res/xml/tests/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}.xml'
   xmlParser = ET.XMLParser(remove_blank_text=True)
   tree = ET.parse(cesta, xmlParser)
   callback(tree)
   ET.indent(tree, space='   ')
   tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)

def find_test(proc, kluc, admin=False, cache=None):
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

def check_time(proc, predmet, trieda, skupina, kapitola, kluc):
   """Najde platny cas pre test."""
   subor = f'./res/xml/tests/{predmet}/{predmet}_{trieda}{skupina}_{kapitola}.xml'
   node = proc.parse_xml(xml_file_name=subor)
   xsltpath = proc.new_xpath_processor()
   xsltpath.set_context(xdm_item=node)
   test_node = next((t for t in (xsltpath.evaluate('/testy/test') or []) if t.get_attribute_value('id') == kluc), None)
   if test_node is not None:
      rodic_node = test_node.get_parent()
      return _check_time_node(test_node, rodic_node)
   return False

def _check_time_node(test_node, rodic_node):
   def parse_time(node, attr):
      try:
         return dat.datetime.fromisoformat(node.get_attribute_value(attr).strip())
      except Exception:
         return None

   start = parse_time(test_node, 'start') or parse_time(rodic_node, 'start')
   stop = parse_time(test_node, 'stop') or parse_time(rodic_node, 'stop')
   teraz = dat.datetime.now()
   return (not start or teraz >= start) and (not stop or teraz <= stop)
