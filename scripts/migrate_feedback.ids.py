# -*- coding: utf-8 -*-
# Migracny skript: prevedie stare otazka_id (kapitola.kategoria.otazka)
# na nove hash id v feedback XML suboroch.

import glob
import lxml.etree as ET
from pathlib import Path

QUESTIONS_DIR = './res/xml/questions'
FEEDBACK_DIR  = './res/xml/feedback'

def parse_prefix(val):
   if val.startswith('bs'):
      return ('bonus', 'static'), val[2:]
   elif val.startswith('s'):
      return ('static',), val[1:]
   elif val.startswith('b'):
      return ('bonus',), val[1:]
   else:
      return (), val

def kategoria_matches(kat, flags):
   has_static = kat.get('static') is not None
   has_bonus  = kat.get('bonus') is not None
   if 'bonus' in flags and 'static' in flags:
      return has_bonus and has_static
   elif 'static' in flags:
      return has_static and not has_bonus
   elif 'bonus' in flags:
      return has_bonus and not has_static
   else:
      return not has_static and not has_bonus

def otazka_matches(otazka, flags):
   has_static = otazka.get('static') is not None
   has_bonus  = otazka.get('bonus') is not None
   if 'bonus' in flags and 'static' in flags:
      return has_bonus and has_static
   elif 'static' in flags:
      return has_static and not has_bonus
   elif 'bonus' in flags:
      return has_bonus and not has_static
   else:
      return not has_static and not has_bonus

def build_mapping(predmet):
   mapping = {}
   for cesta in glob.iglob(f'{QUESTIONS_DIR}/{predmet}/*.xml'):
      try:
         tree = ET.parse(cesta)
         root = tree.getroot()
         id_kapitola = root.get('id')
         if not id_kapitola:
            continue
         for kat in root.findall('kategoria'):
            for otazka in kat.findall('otazka'):
               hash_id = otazka.get('id')
               if not hash_id:
                  continue
               for kat_flags in [(), ('static',), ('bonus',), ('bonus', 'static')]:
                  if not kategoria_matches(kat, kat_flags):
                     continue
                  kats = [k for k in root.findall('kategoria') if kategoria_matches(k, kat_flags)]
                  if kat not in kats:
                     continue
                  kat_num = kats.index(kat) + 1
                  kat_prefix = {(): '', ('static',): 's', ('bonus',): 'b', ('bonus','static'): 'bs'}[tuple(sorted(kat_flags))]
                  for otazka_flags in [(), ('static',), ('bonus',), ('bonus', 'static')]:
                     if not otazka_matches(otazka, otazka_flags):
                        continue
                     otazky = [o for o in kat.findall('otazka') if otazka_matches(o, otazka_flags)]
                     if otazka not in otazky:
                        continue
                     otazka_num = otazky.index(otazka) + 1
                     otazka_prefix = {(): '', ('static',): 's', ('bonus',): 'b', ('bonus','static'): 'bs'}[tuple(sorted(otazka_flags))]
                     stare_id = f'{id_kapitola}.{kat_prefix}{kat_num}.{otazka_prefix}{otazka_num}'
                     mapping[stare_id] = hash_id
      except Exception as e:
         print(f'  CHYBA pri {cesta}: {e}')
   return mapping

def migrate_feedback(cesta, mapping, dry_run=False):
   try:
      xmlParser = ET.XMLParser(remove_blank_text=True)
      tree = ET.parse(cesta, xmlParser)
      zmenene = 0
      nenajdene = []
      for zapis in tree.findall('.//zapis[@otazka_id]'):
         stare = zapis.get('otazka_id')
         if stare in mapping:
            zapis.set('otazka_id', mapping[stare])
            zmenene += 1
         elif '.' in stare:
            nenajdene.append(stare)
      if nenajdene:
         print(f'  NENAJDENE otazka_id v {cesta}: {nenajdene}')
      if zmenene > 0 and not dry_run:
         ET.indent(tree, space='   ')
         tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
      return zmenene
   except Exception as e:
      print(f'  CHYBA pri {cesta}: {e}')
      return 0

def main(dry_run=False):
   if dry_run:
      print('=== DRY RUN — ziadne subory sa nezmenia ===\n')

   predmety = [p.name for p in Path(QUESTIONS_DIR).iterdir() if p.is_dir()]

   for predmet in sorted(predmety):
      print(f'Predmet: {predmet}')
      mapping = build_mapping(predmet)
      print(f'  Mapping: {len(mapping)} zaznamov')

      celkom = 0
      for cesta in sorted(glob.iglob(f'{FEEDBACK_DIR}/{predmet}/*.xml')):
         n = migrate_feedback(cesta, mapping, dry_run)
         if n > 0:
            print(f'  {cesta}: {n} zmen')
         celkom += n
      print(f'  Celkom zmen: {celkom}\n')

if __name__ == '__main__':
   import sys
   dry_run = '--dry-run' in sys.argv
   main(dry_run=dry_run)
