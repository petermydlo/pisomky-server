# -*- coding: utf-8 -*-

import logging
from typing import Annotated, Any
from anyio.abc import TaskGroup
from fastapi import Depends, Form, Header, Query, Path, File, Request, UploadFile
from fastapi.templating import Jinja2Templates
from app.routers.aiproviders import AIImportProvider

IntForm            = Annotated[int, Form()]
StringForm         = Annotated[str, Form()]
StringFormOptional = Annotated[str | None, Form()]
StringListForm     = Annotated[list[str], Form()]
BoolForm           = Annotated[bool, Form()]
StringHeader       = Annotated[str, Header()]
StringPath         = Annotated[str, Path()]
StringQuery        = Annotated[str, Query()]
StringQueryOptional= Annotated[str | None, Query()]
BoolQuery          = Annotated[bool, Query()]
FileListOptional   = Annotated[list[UploadFile] | None, File()]


#zavislosti: zdielany stav aplikacie (app.state, nastavuje main.py) a prihlaseny ucitel
def _get_proc(request: Request) -> Any:
   return request.app.state.proc

def _get_logger(request: Request) -> logging.Logger:
   return request.app.state.logger

def _get_perm_cache(request: Request) -> dict:
   return request.app.state.perm_cache

def _get_kluc_cache(request: Request) -> dict:
   return request.app.state.kluc_cache

def _get_mcq_hotove(request: Request) -> dict:
   return request.app.state.mcq_hotove

def _get_xslt_pools(request: Request) -> dict:
   return request.app.state.xslt_pools

def _get_templates(request: Request) -> Jinja2Templates:
   return request.app.state.templates

def _get_task_group(request: Request) -> TaskGroup:
   return request.app.state.task_group

def _get_ai_provider(request: Request) -> AIImportProvider:
   return request.app.state.ai_provider

def _get_user(x_remote_user: Annotated[str, Header()]) -> str:
   return x_remote_user

#saxonche je skompilovany modul bez stubov (pyright ho vidi ako Unknown, v Annotated by vznikla chyba), preto Any
Proc       = Annotated[Any, Depends(_get_proc)]
Logger     = Annotated[logging.Logger, Depends(_get_logger)]
PermCache  = Annotated[dict, Depends(_get_perm_cache)]
KlucCache  = Annotated[dict, Depends(_get_kluc_cache)]
McqHotove  = Annotated[dict, Depends(_get_mcq_hotove)]
XsltPools  = Annotated[dict, Depends(_get_xslt_pools)]
Templates  = Annotated[Jinja2Templates, Depends(_get_templates)]
TaskGroupDep = Annotated[TaskGroup, Depends(_get_task_group)]
AiProvider = Annotated[AIImportProvider, Depends(_get_ai_provider)]
User       = Annotated[str, Depends(_get_user)]
