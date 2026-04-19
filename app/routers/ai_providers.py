# -*- coding: utf-8 -*-

import os
import json
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are an assistant that extracts student answers from photographs of printed test papers.
You will receive a photo of one or more completed tests and an XML file containing the questions and their IDs.
Your task is:
1. Find the test ID — the possible test IDs are provided in the XML context. Match the answers on the page to the correct test ID from the XML. If you cannot determine which test ID belongs to a page, use the text code in the top right corner (e.g. aut303d3676e37) as a fallback.
2. For each question, identify which letter the STUDENT circled on the paper. You are NOT looking for the correct answer - you are reading what the student actually wrote/circled, which may be wrong. A circled answer is a letter with a hand-drawn oval around it. Do NOT confuse the printed parenthesis ")" after each option letter with a student-drawn circle.
3. Check the XML to see how many answer options each question has — the number varies per question. Only return letters that are valid options for that question.
4. Match the student's circled answers to the question IDs from the XML based on question order only. Do not look at which answer is marked as correct in the XML.

Return ONLY a JSON object in this exact format, no other text:
{
   "tests": [
      {
        "test_id": "test id from the photo",
        "odpovede": [
          {"id": "question id from XML", "odpoved": "a"},
          ...
        ],
        "nejasnosti": [
          {"id": "question id from XML", "znenie": "question text", "dovod": "description of the problem"},
          ...
        ]
     }
  ]
}

If you cannot read the test ID, set test_id to null.
If the answer for a question is unclear, put it in nejasnosti instead of odpovede.
If you are not completely certain about an answer, put it in nejasnosti rather than odpovede. It is better to ask for confirmation than to guess wrong.
Rules for ambiguous markings:
- If a letter is circled multiple times, it counts as one circle
- If a letter is filled/colored in, treat it as circled
- If a letter is crossed out or has a line through it, it is CANCELLED - ignore it
- If an answer text is circled (not just the letter), identify which letter it corresponds to
- If two answers appear marked but one is crossed out, use the one that is NOT crossed out
- If it is still genuinely unclear after applying these rules, put it in nejasnosti
The question numbers on the photo correspond to the order of questions in the XML."""


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

   def _content_block(self, obsah, mime_type):
      import base64
      b64 = base64.b64encode(obsah).decode('utf-8')
      if mime_type == 'application/pdf':
         return {'type': 'document', 'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': b64}}
      return {'type': 'image', 'source': {'type': 'base64', 'media_type': mime_type, 'data': b64}}

   def get_test_ids(self, obsah, mime_type):
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

   def get_answers(self, obsah, mime_type, xml_context):
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

   def get_test_ids(self, obsah, mime_type):
      doc_part = self.types.Part.from_bytes(data=obsah, mime_type=mime_type)
      resp = self.client.models.generate_content(
         model=self.model,
         contents=[doc_part, 'List all unique test IDs found in this document. The test ID appears as a text code in the top-right corner (e.g. aut303d3676e37) and as a QR code in the top-left corner. Return as a plain comma-separated string.'],
      )
      return [s.strip() for s in resp.text.split(',') if s.strip()]

   def get_answers(self, obsah, mime_type, xml_context):
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

   def _image_b64(self, obsah, mime_type):
      import base64
      if mime_type == 'application/pdf':
         raise ValueError('Ollama nepodporuje PDF, použite obrázok (JPG/PNG).')
      return base64.b64encode(obsah).decode('utf-8')

   def get_test_ids(self, obsah, mime_type):
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

   def get_answers(self, obsah, mime_type, xml_context):
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
