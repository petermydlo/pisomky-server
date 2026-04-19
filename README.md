# pisomky-server

FastAPI webová aplikácia pre tvorbu a správu školských písomiek. Umožňuje učiteľom generovať testy z databázy otázok, zdieľať ich so žiakmi cez unikátny kľúč a zbierať odpovede online.

## Funkcie

- Žiaci odovzdávajú odpovede cez webový prehliadač
- Učitelia spravujú otázky, kategórie a kapitoly
- Generovanie testov s náhodným výberom otázok
- Export testov a výsledkov do PDF
- AI nápoveda pre žiakov (Ollama)
- AI import odpovedí z fotiek/PDF (Anthropic / Google Gemini)
- AI hodnotenie otvorených odpovedí

## Požiadavky

- Python 3.11+
- [Apache FOP](https://xmlgraphics.apache.org/fop/) — generovanie PDF (`fop` musí byť v PATH)
- [Ollama](https://ollama.com/) — AI nápoveda (model `llama3.1`)

## Inštalácia

```bash
pip install -r /srv/requirements.txt
```

## Konfigurácia

Vytvor súbor `.env` v koreňovom adresári projektu:

```env
AI_PROVIDER=claude              # claude | gemini | ollama
ANTHROPIC_API_KEY=xxxxxx
ANTHROPIC_MODEL=claude-sonnet-4-6
GEMINI_API_KEY=yyyyyy
GEMINI_MODEL=gemini-2.5-flash
OLLAMA_MODEL=llama3.1
OLLAMA_VISION_MODEL=gemma4:26b
ALLOWED_HOST=pisomky.ternac.net
```

## Spustenie

```bash
# Vývojový server
/srv/venv/bin/fastapi dev app/main.py

# Produkčný server (hypercorn)
/srv/venv/bin/hypercorn --worker-class trio -w 4 --bind unix:/tmp/pisomkyserver.sock app.main:app
```

Server vyžaduje hlavičku `Host: pisomky.ternac.net`. Admin rozhranie vyžaduje hlavičku `X-Remote-User` (nastavuje reverse proxy).

## Štruktúra projektu

```
app/
   main.py          # FastAPI aplikácia, middleware, mountovanie routerov
   utils.py         # XML operácie, XSLT/XQuery transformácie, cache
   mytypes.py       # Type aliasy pre FastAPI parametre
   routers/         # Každý súbor = jeden route
   templates/       # Jinja2 HTML šablóny
res/
   xml/
      questions/    # Databáza otázok (XML, per predmet/kapitola)
      tests/        # Vygenerované testy
      answers/      # Odpovede žiakov
      feedback/     # AI hodnotenia
      lists/        # Zoznamy tried (roster.xml)
   xslt/            # XSLT šablóny (Saxon)
   xquery/          # XQuery súbory (Saxon)
pubres/             # Statické súbory (CSS, JS, obrázky)
scripts/            # Pomocné migračné skripty
tests/              # Pytest testy
```

## Testy

```bash
/srv/venv/bin/python -m pytest tests/ -v
```

## Dátová vrstva

Všetky dáta sú uložené ako XML súbory. Otázky a kategórie majú stabilné `@id` atribúty (8-znakový SHA-256 hash). Ak je otázka použitá v teste, pri mazaní sa označí `@deprecated="1"` namiesto fyzického vymazania.

Súbežné zápisy sú chránené cez `filelock.FileLock`.
