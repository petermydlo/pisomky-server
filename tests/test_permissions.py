# -*- coding: utf-8 -*-

import os
import pytest
from fastapi.exceptions import HTTPException

from app import permissions


@pytest.fixture
def perm_file(tmp_path, monkeypatch):
   cesta = tmp_path / '.perm'
   monkeypatch.setattr(permissions, 'PERM_FILE', cesta)
   return cesta


def test_ziadny_subor_znamena_bez_opravneni(perm_file):
   assert permissions.has_permission({}, 'mydlo', 'edit', 'SXT4') is False


def test_akcia_pre_konkretny_predmet(perm_file):
   perm_file.write_text('mydlo: edit:SXT4 delete:ALL create:AUT3,PIT4\n', encoding='utf-8')
   cache = {}
   assert permissions.has_permission(cache, 'mydlo', 'edit', 'SXT4') is True
   assert permissions.has_permission(cache, 'mydlo', 'edit', 'AUT3') is False


def test_akcia_all_plati_pre_vsetky_predmety(perm_file):
   perm_file.write_text('mydlo: delete:ALL\n', encoding='utf-8')
   cache = {}
   assert permissions.has_permission(cache, 'mydlo', 'delete', 'SXT4') is True
   assert permissions.has_permission(cache, 'mydlo', 'delete', 'AUT3') is True


def test_viacero_predmetov_oddelenych_ciarkou(perm_file):
   perm_file.write_text('mydlo: create:AUT3,PIT4\n', encoding='utf-8')
   cache = {}
   assert permissions.has_permission(cache, 'mydlo', 'create', 'AUT3') is True
   assert permissions.has_permission(cache, 'mydlo', 'create', 'PIT4') is True
   assert permissions.has_permission(cache, 'mydlo', 'create', 'SXT4') is False


def test_iny_pouzivatel_bez_zaznamu(perm_file):
   perm_file.write_text('mydlo: edit:SXT4\n', encoding='utf-8')
   cache = {}
   assert permissions.has_permission(cache, 'novak', 'edit', 'SXT4') is False


def test_hot_reload_po_zmene_suboru(perm_file):
   perm_file.write_text('mydlo: edit:SXT4\n', encoding='utf-8')
   cache = {}
   assert permissions.has_permission(cache, 'mydlo', 'edit', 'SXT4') is True
   povodne_mtime = perm_file.stat().st_mtime
   perm_file.write_text('mydlo: delete:SXT4\n', encoding='utf-8')
   os.utime(perm_file, (povodne_mtime + 1, povodne_mtime + 1))
   assert permissions.has_permission(cache, 'mydlo', 'edit', 'SXT4') is False
   assert permissions.has_permission(cache, 'mydlo', 'delete', 'SXT4') is True


def test_check_permission_vyhodi_403(perm_file):
   with pytest.raises(HTTPException) as exc_info:
      permissions.check_permission({}, 'mydlo', 'edit', 'SXT4')
   assert exc_info.value.status_code == 403


def test_check_permission_prejde_bez_chyby(perm_file):
   perm_file.write_text('mydlo: edit:SXT4\n', encoding='utf-8')
   permissions.check_permission({}, 'mydlo', 'edit', 'SXT4')


def test_predmet_from_cesta():
   assert permissions.predmet_from_cesta('./res/xml/questions/SXT4/SXT4_01.xml') == 'SXT4'
