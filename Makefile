.PHONY: install test lint typecheck run

install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src/argusfinance

run:
	uv run uvicorn argusfinance.api.app:app --host 127.0.0.1 --port 8765
