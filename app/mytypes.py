# -*- coding: utf-8 -*-

from typing import Annotated
from fastapi import Form, Header, Query, Path, File, UploadFile

IntForm            = Annotated[int, Form()]
StringForm         = Annotated[str, Form()]
StringFormOptional = Annotated[str | None, Form()]
StringListForm     = Annotated[list[str], Form()]
BoolForm           = Annotated[bool, Form()]
StringHeader       = Annotated[str, Header()]
StringPath         = Annotated[str, Path()]
StringQuery        = Annotated[str, Query()]
StringQueryOptional= Annotated[str | None, Query()]
FileListOptional   = Annotated[list[UploadFile] | None, File()]
