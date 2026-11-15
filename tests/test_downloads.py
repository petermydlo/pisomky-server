# -*- coding: utf-8 -*-
"""Dočasné súbory pri sťahovaní PDF: QR kódy a PDF sa upratujú aj pri chybe."""

import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from http_klient import http

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


def _stiahni():
   """POST /admin/downloadtests; TestClient vrati odpoved az po spusteni background tasks, ako server po odoslani odpovede."""
   with http() as klient:
      return klient.post('/admin/downloadtests', data={'predmet': 'MAT', 'trieda': '1A', 'kapitola': 'kap1', 'fileid': 'ab12'})


def test_downloadtests_pri_chybe_pdf_sa_qr_adresar_zmaze_hned(prostredie, monkeypatch):
   def zlyhaj(*args, **kwargs):
      raise RuntimeError('fop spadol')

   monkeypatch.setattr(downloads, 'xslt_to_pdf', zlyhaj)
   assert _stiahni().status_code == 400
   assert list(prostredie.iterdir()) == []     # background tasks sa pri vynimke nespustia, preto sa maze hned


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
   qr_subory = []

   def falosne_pdf(proc, stylesheet, source_file=None, params=None, xslt_pools=None, **_):
      qr_subory.append(sorted(p.name for p in Path((params or {})['qrdir'].removeprefix('file://')).iterdir()))
      return SimpleNamespace(name=str(pdf))

   monkeypatch.setattr(downloads, 'xslt_to_pdf', falosne_pdf)
   odpoved = _stiahni()
   assert odpoved.status_code == 200
   assert qr_subory == [['K1.svg', 'K2.svg']]
   assert list(prostredie.iterdir()) == []     # po odoslani odpovede sa QR adresar aj PDF zmazu
