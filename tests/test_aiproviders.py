# -*- coding: utf-8 -*-

import base64
from types import SimpleNamespace
from typing import Any, TypeVar, cast
from unittest.mock import MagicMock

import pytest

from app.routers.aiproviders import (
   ClaudeProvider,
   GeminiProvider,
   OllamaProvider,
   get_provider,
)

T = TypeVar('T')

def _bez_initu(cls: type[T]) -> T:
   """Vytvorí inštanciu bez volania __init__ (ten by vytváral reálneho SDK klienta)."""
   return cls.__new__(cls)


# --- ClaudeProvider._content_block ---

def test_content_block_obrazok():
   blok = ClaudeProvider._content_block(b'obrazok-data', 'image/png')
   zdroj = blok['source']
   assert blok['type'] == 'image'
   assert zdroj['type'] == 'base64'
   assert zdroj['media_type'] == 'image/png'
   udaje = zdroj['data']
   assert isinstance(udaje, str)
   assert base64.b64decode(udaje) == b'obrazok-data'

def test_content_block_pdf():
   blok = ClaudeProvider._content_block(b'pdf-data', 'application/pdf')
   zdroj = blok['source']
   assert blok['type'] == 'document'
   assert zdroj['type'] == 'base64'
   assert zdroj['media_type'] == 'application/pdf'
   udaje = zdroj['data']
   assert isinstance(udaje, str)
   assert base64.b64decode(udaje) == b'pdf-data'


# --- get_provider ---

@pytest.fixture(autouse=True)
def dummy_providers(monkeypatch):
   class DummyClaude: ...
   class DummyGemini: ...
   class DummyOllama: ...
   monkeypatch.setattr('app.routers.aiproviders.ClaudeProvider', DummyClaude)
   monkeypatch.setattr('app.routers.aiproviders.GeminiProvider', DummyGemini)
   monkeypatch.setattr('app.routers.aiproviders.OllamaProvider', DummyOllama)
   return {'claude': DummyClaude, 'gemini': DummyGemini, 'ollama': DummyOllama}

def test_get_provider_default_je_claude(monkeypatch, dummy_providers):
   monkeypatch.delenv('AI_PROVIDER', raising=False)
   assert isinstance(get_provider(), dummy_providers['claude'])

def test_get_provider_gemini(monkeypatch, dummy_providers):
   monkeypatch.setenv('AI_PROVIDER', 'gemini')
   assert isinstance(get_provider(), dummy_providers['gemini'])

def test_get_provider_ollama(monkeypatch, dummy_providers):
   monkeypatch.setenv('AI_PROVIDER', 'ollama')
   assert isinstance(get_provider(), dummy_providers['ollama'])

def test_get_provider_case_insensitive(monkeypatch, dummy_providers):
   monkeypatch.setenv('AI_PROVIDER', 'GEMINI')
   assert isinstance(get_provider(), dummy_providers['gemini'])

def test_get_provider_neznamy_padne_na_claude(monkeypatch, dummy_providers):
   monkeypatch.setenv('AI_PROVIDER', 'neexistujuci')
   assert isinstance(get_provider(), dummy_providers['claude'])


# --- ClaudeProvider.get_test_ids / get_answers ---

def test_claude_get_test_ids_rozdeli_ciarkou():
   provider = _bez_initu(ClaudeProvider)
   provider.client = MagicMock()
   provider.model = 'test-model'
   provider.client.messages.create.return_value = SimpleNamespace(
      content=[SimpleNamespace(type='text', text='id1, id2, id3')]
   )
   assert provider.get_test_ids(b'data', 'image/png') == ['id1', 'id2', 'id3']

def test_claude_get_answers_ciste_json():
   provider = _bez_initu(ClaudeProvider)
   provider.client = MagicMock()
   provider.model = 'test-model'
   provider.client.messages.create.return_value = SimpleNamespace(
      content=[SimpleNamespace(type='text', text='{"tests": []}')]
   )
   assert provider.get_answers(b'data', 'image/png', '<xml/>') == {'tests': []}

def test_claude_get_answers_json_v_code_fence():
   provider = _bez_initu(ClaudeProvider)
   provider.client = MagicMock()
   provider.model = 'test-model'
   provider.client.messages.create.return_value = SimpleNamespace(
      content=[SimpleNamespace(type='text', text='```json\n{"tests": [{"test_id": "t1"}]}\n```')]
   )
   assert provider.get_answers(b'data', 'image/png', '<xml/>') == {'tests': [{'test_id': 't1'}]}


# --- OllamaProvider ---

def test_ollama_image_b64_odmietne_pdf():
   provider = _bez_initu(OllamaProvider)
   with pytest.raises(ValueError):
      provider._image_b64(b'data', 'application/pdf')

def test_ollama_get_test_ids():
   provider = _bez_initu(OllamaProvider)
   provider.client = MagicMock()
   provider.model = 'test-model'
   provider.client.chat.return_value = {'message': {'content': 'a, b'}}
   assert provider.get_test_ids(b'data', 'image/png') == ['a', 'b']

def test_ollama_get_answers_json_v_code_fence():
   provider = _bez_initu(OllamaProvider)
   provider.client = MagicMock()
   provider.model = 'test-model'
   provider.client.chat.return_value = {'message': {'content': '```json\n{"tests": []}\n```'}}
   assert provider.get_answers(b'data', 'image/png', '<xml/>') == {'tests': []}


# --- GeminiProvider ---

def test_gemini_get_test_ids():
   provider = _bez_initu(GeminiProvider)
   provider.client = MagicMock()
   provider.types = cast(Any, MagicMock())
   provider.model = 'test-model'
   provider.client.models.generate_content.return_value = SimpleNamespace(text='id1, id2')
   assert provider.get_test_ids(b'data', 'image/png') == ['id1', 'id2']

def test_gemini_get_answers():
   provider = _bez_initu(GeminiProvider)
   provider.client = MagicMock()
   provider.types = cast(Any, MagicMock())
   provider.model = 'test-model'
   provider.client.models.generate_content.return_value = SimpleNamespace(text='{"tests": []}')
   assert provider.get_answers(b'data', 'image/png', '<xml/>') == {'tests': []}
