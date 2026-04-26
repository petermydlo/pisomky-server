VENV = /srv/venv

.PHONY: test lint run dev


test:
	$(VENV)/bin/pytest

lint:
	$(VENV)/bin/ruff check app/
	$(VENV)/bin/mypy app/

run:
	$(VENV)/bin/hypercorn --worker-class trio -w 4 --bind unix:/tmp/pisomkyserver.sock app.main:app

dev:
	$(VENV)/bin/fastapi dev app/main.py
