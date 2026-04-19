# -*- coding: utf-8 -*-
# Jednorazový skript: v každom answers XML ponechá len posledný záznam na žiaka.

import glob
import lxml.etree as ET
from collections import defaultdict

def cleanup_file(cesta):
   xmlParser = ET.XMLParser(remove_blank_text=True)
   tree = ET.parse(cesta, xmlParser)
   root = tree.getroot()

   skupiny = defaultdict(list)
   for test in root.findall('test'):
      skupiny[test.get('id')].append(test)

   zmenene = False
   for kluc, zaznamy in skupiny.items():
      if len(zaznamy) <= 1:
         continue
      zaznamy.sort(key=lambda t: t.get('dat', ''))
      for stary in zaznamy[:-1]:
         root.remove(stary)
      zmenene = True
      print(f'  {kluc}: odstránených {len(zaznamy) - 1} starých záznamov')

   if zmenene:
      ET.indent(tree, space='   ')
      tree.write(cesta, encoding='utf-8', xml_declaration=True, pretty_print=True)
      print(f'  -> uložené: {cesta}')

for cesta in glob.iglob('./res/xml/answers/**/*.xml', recursive=True):
   print(f'Spracovávam: {cesta}')
   try:
      cleanup_file(cesta)
   except Exception as e:
      print(f'  CHYBA: {e}')

print('Hotovo.')
