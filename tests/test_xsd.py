# -*- coding: utf-8 -*-

import tarfile
import pytest
import lxml.etree as ET
from pathlib import Path

ROOT = Path(__file__).parent.parent
XSD_DIR = ROOT / 'res' / 'xsd'
ARCHIV_DIR = ROOT / 'res' / 'xml' / 'archiv'


def _load_schema(name: str) -> ET.XMLSchema:
   return ET.XMLSchema(ET.parse(str(XSD_DIR / name)))


def _questions_files():
   return [
      pytest.param(p, id=p.relative_to(ROOT).as_posix())
      for p in sorted((ROOT / 'res' / 'xml' / 'questions').rglob('*.xml'))
      if not p.name.endswith('~')
   ]


def _tests_files():
   live = [
      pytest.param(('file', p, None), id=p.relative_to(ROOT).as_posix())
      for p in sorted((ROOT / 'res' / 'xml' / 'tests').rglob('*.xml'))
      if not p.name.endswith('~')
   ]
   archived = []
   for arch in sorted(ARCHIV_DIR.rglob('*.tar.xz')):
      with tarfile.open(arch, 'r:xz') as tar:
         for member in tar.getmembers():
            if 'tests/' in member.name and member.name.endswith('.xml'):
               archived.append(pytest.param(
                  ('tar', arch, member.name),
                  id=f'{arch.name}/{member.name}',
               ))
   return live + archived


def _answers_files():
   return [
      pytest.param(p, id=p.relative_to(ROOT).as_posix())
      for p in sorted((ROOT / 'res' / 'xml' / 'answers').rglob('*.xml'))
      if not p.name.endswith('~')
   ]


def _feedback_files():
   return [
      pytest.param(p, id=p.relative_to(ROOT).as_posix())
      for p in sorted((ROOT / 'res' / 'xml' / 'feedback').rglob('*.xml'))
      if not p.name.endswith('~')
   ]


@pytest.mark.parametrize('xml_path', _questions_files())
def test_questions_schema(xml_path: Path):
   schema = _load_schema('questions.xsd')
   doc = ET.parse(str(xml_path))
   assert schema.validate(doc), _format_errors(schema)


@pytest.mark.parametrize('src', _tests_files())
def test_tests_schema(src):
   schema = _load_schema('tests.xsd')
   kind, path, member_name = src
   if kind == 'file':
      doc = ET.parse(str(path))
   else:
      with tarfile.open(path, 'r:xz') as tar:
         doc = ET.fromstring(tar.extractfile(member_name).read())
   assert schema.validate(doc), _format_errors(schema)


@pytest.mark.parametrize('xml_path', _answers_files())
def test_answers_schema(xml_path: Path):
   schema = _load_schema('answers.xsd')
   doc = ET.parse(str(xml_path))
   assert schema.validate(doc), _format_errors(schema)


@pytest.mark.parametrize('xml_path', _feedback_files())
def test_feedback_schema(xml_path: Path):
   schema = _load_schema('feedback.xsd')
   doc = ET.parse(str(xml_path))
   assert schema.validate(doc), _format_errors(schema)


def _format_errors(schema: ET.XMLSchema) -> str:
   return '\n'.join(f'{e.line}: {e.message}' for e in schema.error_log)
