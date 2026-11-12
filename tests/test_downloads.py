# -*- coding: utf-8 -*-
"""Dočasné súbory pri sťahovaní PDF: QR kódy a PDF sa upratujú aj pri chybe."""

import asyncio
import logging
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks
from fastapi.exceptions import HTTPException

import app.routers.downloads as downloads

TESTY_XML = """<?xml version='1.0' encoding='utf-8'?>
<testy predmet="MAT" trieda="1A" skupina="" kapitola="kap1" fileid="ab12">
   <test id="K1"/>
   <test id="K2"/>
</testy>
"""


@pytest.fixture
def prostredie(tmp_path, monkeypatch):
   (tmp_path / 'res/xml/tests/MAT').mkdir(parents=True)
   (tmp_path / 'res/xml/tests/MAT/MAT_1A_kap1_ab12.xml').write_text(TESTY_XML, encoding='utf-8')
   docasne = tmp_path / 'tmp'
   docasne.mkdir()
   monkeypatch.setattr(tempfile, 'tempdir', str(docasne))
   monkeypatch.chdir(tmp_path)
   return docasne


def _stiahni(background_tasks):
   request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(proc=None, xslt_pools={}, logger=logging.getLogger('pisomky'))))
   return asyncio.run(downloads.downloadtests(request, background_tasks, 'MAT', '1A', 'kap1', 'ab12', ''))  # type: ignore[arg-type]


def test_downloadtests_pri_chybe_pdf_sa_qr_adresar_zmaze_hned(prostredie, monkeypatch):
   def zlyhaj(*args, **kwargs):
      raise RuntimeError('fop spadol')

   monkeypatch.setattr(downloads, 'xslt_to_pdf', zlyhaj)
   tasks = BackgroundTasks()
   with pytest.raises(HTTPException) as exc:
      _stiahni(tasks)
   assert exc.value.status_code == 400
   assert list(prostredie.iterdir()) == []     # background tasks sa pri vynimke nespustia, preto sa maze hned
   assert tasks.tasks == []


def test_generuj_qr_kody_pri_chybe_zmaze_adresar(prostredie, monkeypatch):
   def zlyhaj(*args, **kwargs):
      raise RuntimeError('qr spadlo')

   monkeypatch.setattr(downloads.qrcode, 'QRCode', zlyhaj)
   with pytest.raises(RuntimeError):
      downloads._generuj_qr_kody('./res/xml/tests/MAT/MAT_1A_kap1_ab12.xml')
   assert list(prostredie.iterdir()) == []


def test_downloadtests_uspech_upratanie_ostava_na_pozadi(prostredie, monkeypatch):
   pdf = prostredie / 'vysledok.pdf'
   pdf.write_bytes(b'%PDF-')
   qr_adresare = []

   def falosne_pdf(proc, stylesheet, source_file=None, params=None, xslt_pools=None, **_):
      qr_adresare.append((params or {})['qrdir'].removeprefix('file://'))
      return SimpleNamespace(name=str(pdf))

   monkeypatch.setattr(downloads, 'xslt_to_pdf', falosne_pdf)
   tasks = BackgroundTasks()
   odpoved = _stiahni(tasks)
   assert odpoved.status_code == 200
   assert len(tasks.tasks) == 2
   assert sorted(p.name for p in Path(qr_adresare[0]).iterdir()) == ['K1.svg', 'K2.svg']
   asyncio.run(tasks())
   assert list(prostredie.iterdir()) == []     # po odoslani odpovede sa QR adresar aj PDF zmazu
