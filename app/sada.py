# -*- coding: utf-8 -*-

"""Zavislost pre handlery, ktore pracuju s jednou sadou testov (predmet, trieda, skupina, kapitola, fileid).

Overi format parametrov (400) a existenciu pozadovaneho suboru sady (404) skor, nez handler zacne pracovat,
teda pred mkdir, zamkami, citanim formulara a transformaciami."""

import os
from typing import Annotated, Literal, NamedTuple
from fastapi import Depends
from fastapi.exceptions import HTTPException
from app.mytypes import StringForm
from app.utils import test_xml_path


class Sada(NamedTuple):
   predmet: str
   trieda: str
   skupina: str
   kapitola: str
   fileid: str

   @property
   def cesta(self) -> str:
      """Cesta k test XML sady."""
      return test_xml_path(self.predmet, self.trieda, self.skupina, self.kapitola, self.fileid)

   @property
   def cesta_odpovedi(self) -> str:
      """Cesta k XML s odpovedami sady."""
      return self.cesta.replace('/tests/', '/answers/', 1)


def _sada(existuje: Literal['tests', 'answers'] | None):
   def over_sadu(predmet: StringForm, trieda: StringForm, kapitola: StringForm, fileid: StringForm, skupina: StringForm = '') -> Sada:
      sada = Sada(predmet, trieda, skupina, kapitola, fileid)
      try:
         cesta = sada.cesta  #validuje vsetkych pat parametrov
      except ValueError as e:
         raise HTTPException(status_code=400, detail=str(e))
      if existuje == 'tests' and not os.path.exists(cesta):
         raise HTTPException(status_code=404, detail='Súbor nenájdený!')
      if existuje == 'answers' and not os.path.isfile(sada.cesta_odpovedi):
         raise HTTPException(status_code=404, detail='Súbor odpovedí nenájdený')
      return sada
   return over_sadu

#sada s platnym formatom parametrov, bez kontroly existencie (handler si ju overi sam, napr. podla priznakov)
SadaFormat = Annotated[Sada, Depends(_sada(None))]
#existujuca sada s test XML (pre handlery, ktore z testu citaju alebo ho menia)
SadaTestov = Annotated[Sada, Depends(_sada('tests'))]
#existujuca sada so suborom odpovedi (hodnotenie, odhalenie odpovedi)
SadaOdpovedi = Annotated[Sada, Depends(_sada('answers'))]
