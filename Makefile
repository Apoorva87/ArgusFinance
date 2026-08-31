.PHONY: install migrate dev test lint typecheck dashboard-test dashboard-build quality run

install:
	uv sync --locked
	npm ci --prefix apps/dashboard

migrate:
	uv run alembic upgrade head

dev:
	uv run python scripts/dev.py

test:
	uv run pytest
	npm test --prefix apps/dashboard -- --run

lint:
	uv run ruff check src tests scripts migrations

typecheck:
	uv run mypy src/argusfinance

dashboard-test:
	npm test --prefix apps/dashboard -- --run

dashboard-build:
	npm run build --prefix apps/dashboard

quality: lint typecheck dashboard-test dashboard-build

run:
	uv run uvicorn argusfinance.api.app:app --host 127.0.0.1 --port 8765
