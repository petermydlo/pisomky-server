# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`pisomky-server` is a FastAPI web application for creating and managing school tests (písomky). It serves test questions to students, collects answers, and provides admin tools for teachers. The code and comments are primarily in Slovak.

## Running the Server

```bash
# Install dependencies (using venv at /srv/venv)
/srv/venv/bin/pip install -r /srv/requirements.txt

# Run development server (from /srv/web/pisomky)
/srv/venv/bin/fastapi dev main.py

# Run production server
/srv/venv/bin/fastapi run main.py
```

The server requires the `Host: pisomky.ternac.net` header (enforced by `TrustedHostMiddleware`). Admin routes require an `X-Remote-User` header (set by a reverse proxy).

## External Dependencies

- **Saxon (saxonche)**: XSLT 3.0 / XQuery processor — used for all XML-to-HTML and XML-to-PDF transformations
- **Apache FOP**: must be installed on the system; called via subprocess to convert XSL-FO to PDF
- **Ollama** (`llama3.1`): local LLM used for the AI hint feature (`/ai/napoveda`). Vision model (`gemma4:26b` by default) optionally used for answer import via `OLLAMA_VISION_MODEL`
- **Anthropic / Google Gemini**: used for AI answer import from photos/PDFs (configured via `.env`)

## Environment Variables (`.env`)

```
AI_PROVIDER=claude              # or 'gemini' or 'ollama'
ANTHROPIC_MODEL=claude-sonnet-4-20250514
GEMINI_MODEL=gemini-2.0-flash
OLLAMA_MODEL=llama3.1           # model for AI hints
OLLAMA_VISION_MODEL=gemma4:26b  # model for answer import from images
```

## Architecture

### Request Flow

1. Student enters a test key → `GET /{kluc}` in `main.py`
2. `find_test()` in `utils.py` locates the test XML using a hot-file + dict cache stored in `app.state`
3. Saxon XSLT transforms the XML node to HTML (`res/xslt/showtest.xsl` or `writetest.xsl`)
4. Student submits answers → `POST /saveanswers/{kluc}` writes to `res/xml/answers/`

### XML Data Layer

All persistent data is stored as XML files:

| Directory | Content |
|---|---|
| `res/xml/questions/{predmet}/` | Question banks, one XML per chapter (`kapitola`). Structure: `kapitola > kategoria > otazka > odpoved` |
| `res/xml/tests/{predmet}/` | Generated test instances with randomized question selection |
| `res/xml/answers/{predmet}/` | Student answer submissions |
| `res/xml/feedback/{predmet}/` | AI feedback results |
| `res/xml/lists/roster.xml` | Class/student roster used when generating tests |

Questions and categories have stable `@id` attributes (8-char SHA-256 hashes). `ensure_ids()` in `utils.py` assigns them on first use. If a question or category is referenced in a tests file, deletion marks it `@deprecated="1"` instead of removing it.

### XSLT/XQuery

All HTML rendering and PDF generation goes through Saxon. Stylesheets are in `res/xslt/`, XQuery files in `res/xquery/`. The global `PySaxonProcessor` instance lives in `app.state.proc` and must not be recreated per request.

### Routers

Each file in `routers/` is a single-route FastAPI `APIRouter`. Naming matches the route function. AI-related routers:
- `aihelp.py` — AI hint via Ollama (JSON response, persists hint + keys to feedback XML)
- `aifeedback.py` / `aifeedback_report.py` — AI grading feedback
- `aievaluate.py` — AI evaluation of open-answer questions
- `importanswers.py` — AI-assisted import of answers from scanned photos/PDFs (uses `routers/ai_providers.py`)

### Caches

Three in-memory dicts in `app.state` speed up repeated lookups:
- `kluc_cache` — test key → XML file path
- `otazka_cache` — question id → XML file path  
- `kategoria_cache` — category id → XML file path

Cache entries use a `__hot__` key pointing to the most recently accessed file.

### File Locking

Concurrent writes to XML files are guarded by `filelock.FileLock` (lock file = `<path>.lock`). Always acquire the lock, then re-parse the file before writing.

## Key Conventions

- Variable names and XML element/attribute names are Slovak (e.g. `predmet`=subject, `trieda`=class, `kapitola`=chapter, `kategoria`=category, `otazka`=question, `odpoved`=answer, `znenie`=question text, `spravna`=correct)
- Type aliases for FastAPI parameters are defined in `mytypes.py`
- All XML files use UTF-8 with XML declaration; write with `pretty_print=True` and `ET.indent(tree, space='   ')`
