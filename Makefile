.PHONY: install install-agents install-skills validate-agents migrate dev test lint typecheck dashboard-test dashboard-build quality run

PYTHON ?= uv run --locked python

install: install-agents
	uv sync --locked
	npm ci --prefix apps/dashboard

# skills/ is the single source of truth. Codex reads it through
# .codex-plugin/plugin.json; Claude Code reads it through .claude/skills/.
install-skills:
	mkdir -p .claude/skills
	ln -sfn ../../skills/evaluate-ticker .claude/skills/evaluate-ticker

# Role definitions are versioned and project-local; validate them on every install.
install-agents: validate-agents install-skills

validate-agents:
	$(PYTHON) scripts/validate_agent_roster.py

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

quality: validate-agents lint typecheck dashboard-test dashboard-build

run:
	uv run uvicorn argusfinance.api.app:app --host 127.0.0.1 --port "$$(uv run python -c 'from argusfinance.config import Settings; print(Settings().api_port)')"
