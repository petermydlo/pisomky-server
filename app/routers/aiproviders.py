# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = (Path(__file__).parent.parent / 'templates' / 'aiproviders_system.md').read_text()


class AIImportProvider:
   """Abstraktna baza pre AI providery na import odpovedi."""

   def get_test_ids(self, obsah: bytes, mime_type: str) -> list[str]:
      """Zisti zoznam test ID v dokumente. Vracia list stringov."""
      raise NotImplementedError

   def get_answers(self, obsah: bytes, mime_type: str, xml_context: str) -> dict:
      """Extrahuje odpovede z dokumentu. Vracia dict so strukturou {tests: [...]}."""
      raise NotImplementedError


class ClaudeProvider(AIImportProvider):
   def __init__(self):
      import anthropic
      self.client = anthropic.Anthropic()
      self.model = os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-6')

   def _content_block(self, obsah: bytes, mime_type: str) -> dict:
      import base64
      b64 = base64.b64encode(obsah).decode('utf-8')
      if mime_type == 'application/pdf':
         return {'type': 'document', 'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': b64}}
      return {'type': 'image', 'source': {'type': 'base64', 'media_type': mime_type, 'data': b64}}

   def get_test_ids(self, obsah: bytes, mime_type: str) -> list[str]:
      resp = self.client.messages.create(
         model=self.model,
         max_tokens=300,
         output_config={'effort': 'low'},
         messages=[{
            'role': 'user',
            'content': [
               self._content_block(obsah, mime_type),
               {'type': 'text', 'text': 'List all unique test IDs found in this document. The test ID appears as a text code in the top-right corner (e.g. aut303d3676e37) and as a QR code in the top-left corner. Return as a plain comma-separated string.'}
            ]
         }]
      )
      return [s.strip() for s in resp.content[0].text.split(',') if s.strip()]

   def get_answers(self, obsah: bytes, mime_type: str, xml_context: str) -> dict:
      resp = self.client.messages.create(
         model=self.model,
         max_tokens=3000,
         output_config={'effort': 'low'},
         system=SYSTEM_PROMPT,
         messages=[{
            'role': 'user',
            'content': [
               self._content_block(obsah, mime_type),
               {'type': 'text', 'text': f'Here is the XML with the questions:\n{xml_context}'}
            ]
         }]
      )
      raw = resp.content[0].text.strip()
      if '```' in raw:
         raw = raw.split('```')[1]
         if raw.startswith('json'):
            raw = raw[4:]
         raw = raw.strip()
      return json.loads(raw)


class GeminiProvider(AIImportProvider):
   def __init__(self):
      from google import genai
      from google.genai import types
      self.client = genai.Client()
      self.types = types
      self.model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

   def get_test_ids(self, obsah: bytes, mime_type: str) -> list[str]:
      doc_part = self.types.Part.from_bytes(data=obsah, mime_type=mime_type)
      resp = self.client.models.generate_content(
         model=self.model,
         contents=[doc_part, 'List all unique test IDs found in this document. The test ID appears as a text code in the top-right corner (e.g. aut303d3676e37) and as a QR code in the top-left corner. Return as a plain comma-separated string.'],
      )
      return [s.strip() for s in resp.text.split(',') if s.strip()]

   def get_answers(self, obsah: bytes, mime_type: str, xml_context: str) -> dict:
      doc_part = self.types.Part.from_bytes(data=obsah, mime_type=mime_type)
      resp = self.client.models.generate_content(
         model=self.model,
         contents=[doc_part, f'{SYSTEM_PROMPT}\n\nXML Contexts:\n{xml_context}'],
         config=self.types.GenerateContentConfig(response_mime_type='application/json'),
      )
      return json.loads(resp.text)


class OllamaProvider(AIImportProvider):
   def __init__(self):
      import ollama
      self.client = ollama.Client()
      self.model = os.getenv('OLLAMA_VISION_MODEL', 'gemma4:26b')

   def _image_b64(self, obsah: bytes, mime_type: str) -> str:
      import base64
      if mime_type == 'application/pdf':
         raise ValueError('Ollama nepodporuje PDF, použite obrázok (JPG/PNG).')
      return base64.b64encode(obsah).decode('utf-8')

   def get_test_ids(self, obsah: bytes, mime_type: str) -> list[str]:
      b64 = self._image_b64(obsah, mime_type)
      resp = self.client.chat(
         model=self.model,
         messages=[{
            'role': 'user',
            'content': 'List all unique test IDs found in this document. The test ID appears as a text code in the top-right corner (e.g. aut303d3676e37) and as a QR code in the top-left corner. Return as a plain comma-separated string.',
            'images': [b64]
         }]
      )
      text = resp['message']['content']
      return [s.strip() for s in text.split(',') if s.strip()]

   def get_answers(self, obsah: bytes, mime_type: str, xml_context: str) -> dict:
      b64 = self._image_b64(obsah, mime_type)
      resp = self.client.chat(
         model=self.model,
         messages=[{
            'role': 'user',
            'content': f'{SYSTEM_PROMPT}\n\nHere is the XML with the questions:\n{xml_context}',
            'images': [b64]
         }]
      )
      raw = resp['message']['content'].strip()
      if '```' in raw:
         raw = raw.split('```')[1]
         if raw.startswith('json'):
            raw = raw[4:]
         raw = raw.strip()
      return json.loads(raw)


def get_provider() -> AIImportProvider:
   """Vrati spravny AI provider podla nastavenia AI_PROVIDER v .env."""
   provider = os.getenv('AI_PROVIDER', 'claude').lower()
   if provider == 'gemini':
      return GeminiProvider()
   if provider == 'ollama':
      return OllamaProvider()
   return ClaudeProvider()
