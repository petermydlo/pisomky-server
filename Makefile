.PHONY: test lint run dev

test:
	pytest

lint:
	ruff check app/

run:
	hypercorn --worker-class trio -w 4 --bind unix:/tmp/pisomkyserver.sock app.main:app

dev:
	fastapi dev app/main.py
