VENV = .venv

.PHONY: test validate lint run dev


test:
	$(VENV)/bin/pytest
	node --test tests/js/*.test.js

# banka otazok, testy, odpovede, feedback a archivy oproti res/xsd/*.xsd (iba lokalne, res/xml/ nie je v gite)
validate:
	$(VENV)/bin/pytest tests/test_xsd.py -q

lint:
	$(VENV)/bin/ruff check app/
	$(VENV)/bin/mypy app/
	$(VENV)/bin/pyright app/ tests/

run:
	$(VENV)/bin/hypercorn --worker-class trio -w 4 --bind unix:/tmp/pisomkyserver.sock app.main:app

dev:
	$(VENV)/bin/fastapi dev app/main.py
