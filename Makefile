.PHONY: test lint run

test:
	/srv/venv/bin/python -m pytest

lint:
	/srv/venv/bin/ruff check app/

run:
	/srv/venv/bin/hypercorn --worker-class trio -w 4 --bind unix:/tmp/pisomkyserver.sock app.main:app

dev:
	/srv/venv/bin/fastapi dev app/main.py
