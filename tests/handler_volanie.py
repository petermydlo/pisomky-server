# -*- coding: utf-8 -*-

"""Priame volanie route handlerov v testoch: zavislosti (Proc, Logger, ...) sa berú z request.app.state, ako ich dosadzuje FastAPI."""

import inspect
import typing
from fastapi.params import Depends

#parametre handlerov, ktore FastAPI dosadzuje cez Depends z app.state (pozri app/mytypes.py)
_STAV = ('proc', 'logger', 'perm_cache', 'kluc_cache', 'mcq_hotove', 'xslt_pools', 'templates', 'task_group', 'ai_provider')

def volaj(handler, request, *args, **kwargs):
   """Zavola handler s fiktivnym `request`; zavislosti dosadi z request.app.state, `user` z `X_Remote_User` (alebo `user`).
   Parameter `sada` (app/sada.py) sa vyrobi spustenim skutocnej dependency z poli predmet, trieda, kapitola, fileid, skupina,
   takze 400/404 nastanu ako v aplikacii.
   Pozicne argumenty sa priradia parametrom handlera v poradi, ako ich definuje (bez zavislosti a `request`)."""
   volne = []
   hotove = {}
   sada_dep = None
   hinty = typing.get_type_hints(handler, include_extras=True)
   for nazov in inspect.signature(handler).parameters:
      if nazov == 'request':
         hotove[nazov] = request
      elif nazov == 'user':
         hotove[nazov] = kwargs.pop('X_Remote_User', kwargs.pop('user', None))
      elif nazov in _STAV:
         hotove[nazov] = getattr(request.app.state, nazov, None)
      elif nazov == 'sada':
         sada_dep = next(m.dependency for m in hinty[nazov].__metadata__ if isinstance(m, Depends))
         assert sada_dep is not None
         volne.extend(inspect.signature(sada_dep).parameters)
      else:
         volne.append(nazov)
   kwargs.update(zip(volne, args))
   if sada_dep is not None:
      hotove['sada'] = sada_dep(**{k: kwargs.pop(k) for k in inspect.signature(sada_dep).parameters if k in kwargs})
   return handler(**hotove, **kwargs)
