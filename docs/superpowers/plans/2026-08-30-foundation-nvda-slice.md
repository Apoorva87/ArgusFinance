# ArgusFinance Foundation and NVDA Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local ArgusFinance foundation where one deterministic NVDA option-market snapshot is stored once and exposed consistently through FastAPI, the CLI, MCP, and a React dashboard.

**Architecture:** Implement a small Python modular monolith under `src/argusfinance` with typed domain contracts, adapter interfaces, SQLite metadata, and a DuckDB/Parquet snapshot store. A Vite React application reads the FastAPI contract, while CLI and MCP entry points call the same application service rather than duplicating provider or storage logic.

**Tech Stack:** Python 3.12 managed by uv; FastAPI; Pydantic v2; SQLAlchemy 2; Alembic; DuckDB; PyArrow; Typer; official MCP Python SDK; pytest; Ruff; mypy; React 19; TypeScript; Vite; Vitest; Testing Library; Plotly.js; npm.

**Spec:** `docs/superpowers/specs/2026-08-30-argusfinance-design.md`

## Global Constraints

- The application must run locally and must not require a hosted ArgusFinance service.
- Interactive Brokers access is read-only; this slice uses a deterministic mock provider and adds only an IBKR diagnostic boundary.
- The mock NVDA snapshot is the single test fixture consumed by API, CLI, MCP, and dashboard tests.
- Provider-specific objects must not cross the `MarketDataProvider` interface.
- Market values carry source, source timestamp, retrieval timestamp, and data status.
- SQLite stores operational metadata; Parquet stores normalized rows; DuckDB queries Parquet.
- Agents never write databases directly; application services own persistence.
- No AI-generated numeric chart values are permitted.
- The repository must not commit secrets, `.env` files, SQLite databases, Parquet files, DuckDB files, or browser session data.
- Every code task follows red-green-refactor and ends with a focused commit.
- The first slice supports only `NVDA`; unsupported tickers fail explicitly rather than returning fabricated data.
- The API binds to `127.0.0.1` by default.

## Scope deferral

This plan implements only Phase 1 of the approved specification. Strategy
lifecycle, paper fills, scenario and Greek engines, company intelligence, news,
historical backtesting, and live OptionStrat handoff are separate subprojects
with their own future specs/plans. This slice creates their shared contracts and
agent/plugin shells but does not simulate partial implementations of them.

## File map

```text
pyproject.toml                         Python project, dependencies, and tool config
uv.lock                                Reproducible Python dependency lock
Makefile                               Local setup, quality, test, and run commands
.env.example                           Non-secret local configuration template
src/argusfinance/config.py             Typed local settings
src/argusfinance/domain/market.py      Normalized market value objects
src/argusfinance/ports/market_data.py  Provider protocol
src/argusfinance/adapters/mock_market.py Deterministic NVDA provider
src/argusfinance/adapters/ibkr.py      Read-only diagnostic port implementation shell
src/argusfinance/storage/database.py   SQLite engine/session construction
src/argusfinance/storage/models.py     SQLAlchemy snapshot metadata model
src/argusfinance/storage/repositories.py Metadata repository
src/argusfinance/storage/snapshots.py  Parquet writer and DuckDB reader
src/argusfinance/services/market.py    Shared snapshot application service
src/argusfinance/api/app.py            FastAPI application factory
src/argusfinance/api/routes/market.py  Market HTTP routes
src/argusfinance/cli.py                Typer entry point
src/argusfinance/mcp_server.py         MCP tools backed by MarketService
src/argusfinance/bootstrap.py          Dependency composition root
apps/dashboard/                        React/Vite local decision surface
.codex/config.toml                     Project-scoped agent settings
.codex/agents/*.toml                   Six stable custom-agent definitions
.codex-plugin/plugin.json              Local plugin manifest
skills/evaluate-ticker/SKILL.md        Repeatable orchestration workflow
agents/*/                              Versioned role playbooks
scripts/dev.py                         Local multi-process launcher
tests/                                 Python unit, contract, API, CLI, MCP, and E2E tests
```

---

### Task 1: Python project and local health endpoint

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.env.example`
- Create: `Makefile`
- Create: `src/argusfinance/__init__.py`
- Create: `src/argusfinance/config.py`
- Create: `src/argusfinance/api/__init__.py`
- Create: `src/argusfinance/api/app.py`
- Test: `tests/api/test_health.py`

**Interfaces:**
- Consumes: no application interfaces.
- Produces: `Settings`, `get_settings()`, and `create_app(settings: Settings | None = None) -> FastAPI`.

- [ ] **Step 1: Write the failing health test**

```python
from fastapi.testclient import TestClient

from argusfinance.api.app import create_app
from argusfinance.config import Settings


def test_health_reports_local_service_identity(tmp_path):
    settings = Settings(
        state_dir=tmp_path,
        database_url=f"sqlite:///{tmp_path / 'workspace.sqlite'}",
    )
    response = TestClient(create_app(settings)).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "argusfinance",
        "status": "ok",
        "mode": "local",
    }
```

- [ ] **Step 2: Run the test and verify the missing package failure**

Run: `uv run pytest tests/api/test_health.py -v`

Expected: FAIL because `argusfinance.api.app` does not exist.

- [ ] **Step 3: Create project metadata and minimal application**

Set `requires-python = ">=3.12,<3.15"`. Add runtime dependencies for FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy, Alembic, DuckDB, PyArrow, Typer, and the MCP SDK. Add development dependencies for pytest, pytest-cov, HTTPX, Ruff, and mypy. Configure uv to package `src/argusfinance`, pytest to use `tests`, Ruff for Python 3.12, and mypy with strict mode for `src/argusfinance`.

```python
# src/argusfinance/config.py
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ARGUS_", env_file=".env")

    state_dir: Path = Path("data")
    database_url: str = "sqlite:///db/workspace.sqlite"
    api_host: str = "127.0.0.1"
    api_port: int = 8765


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# src/argusfinance/api/app.py
from fastapi import FastAPI

from argusfinance.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    app = FastAPI(title="ArgusFinance", version="0.1.0")
    app.state.settings = resolved

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"service": "argusfinance", "status": "ok", "mode": "local"}

    return app


app = create_app()
```

- [ ] **Step 4: Lock dependencies and run quality checks**

Run: `uv lock`

Run: `uv run pytest tests/api/test_health.py -v`

Run: `uv run ruff check src tests`

Expected: all commands exit 0 and the health test passes.

- [ ] **Step 5: Commit the foundation**

```bash
git add pyproject.toml uv.lock .python-version .env.example Makefile src tests/api/test_health.py
git commit -m "feat: add local API foundation"
```

---

### Task 2: Normalized market contracts and deterministic NVDA provider

**Files:**
- Create: `src/argusfinance/domain/__init__.py`
- Create: `src/argusfinance/domain/market.py`
- Create: `src/argusfinance/ports/__init__.py`
- Create: `src/argusfinance/ports/market_data.py`
- Create: `src/argusfinance/adapters/__init__.py`
- Create: `src/argusfinance/adapters/mock_market.py`
- Create: `tests/fixtures/nvda_snapshot.json`
- Test: `tests/domain/test_market.py`
- Test: `tests/adapters/test_mock_market.py`

**Interfaces:**
- Consumes: standard-library `datetime`, `Decimal`, and Pydantic.
- Produces: `MarketDataStatus`, `UnderlyingQuote`, `OptionQuote`, `MarketSnapshot`, `MarketDataProvider`, and `MockMarketDataProvider`.

- [ ] **Step 1: Write contract tests for provenance and ticker validation**

```python
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from argusfinance.domain.market import MarketDataStatus, UnderlyingQuote


def test_underlying_quote_preserves_provenance():
    observed = datetime(2026, 8, 28, 20, 0, tzinfo=UTC)
    quote = UnderlyingQuote(
        ticker="nvda",
        price=Decimal("180.25"),
        source="mock",
        source_timestamp=observed,
        retrieved_at=observed,
        status=MarketDataStatus.REALTIME,
    )
    assert quote.ticker == "NVDA"
    assert quote.price == Decimal("180.25")


def test_quote_rejects_naive_timestamps():
    with pytest.raises(ValidationError):
        UnderlyingQuote(
            ticker="NVDA",
            price=Decimal("180.25"),
            source="mock",
            source_timestamp=datetime(2026, 8, 28, 20, 0),
            retrieved_at=datetime(2026, 8, 28, 20, 0),
            status=MarketDataStatus.REALTIME,
        )
```

- [ ] **Step 2: Run the contract tests and verify they fail**

Run: `uv run pytest tests/domain/test_market.py -v`

Expected: FAIL because the market domain module does not exist.

- [ ] **Step 3: Implement immutable normalized models and provider protocol**

Define `MarketDataStatus` as `REALTIME | DELAYED | FROZEN | UNAVAILABLE`.
Define frozen Pydantic models with timezone-aware timestamp validators. An
`OptionQuote` includes expiration, strike, option type, bid, ask, volume, open
interest, IV, delta, gamma, theta, and vega. `MarketSnapshot` includes a UUID,
underlying quote, tuple of option quotes, and `created_at`.

```python
# src/argusfinance/ports/market_data.py
from typing import Protocol

from argusfinance.domain.market import MarketSnapshot


class MarketDataProvider(Protocol):
    def get_snapshot(self, ticker: str, weeks: int = 8) -> MarketSnapshot: ...

    def diagnostic(self) -> dict[str, str | bool]: ...
```

- [ ] **Step 4: Write the mock-provider test**

```python
import pytest

from argusfinance.adapters.mock_market import MockMarketDataProvider


def test_mock_provider_returns_eight_week_nvda_fixture():
    snapshot = MockMarketDataProvider().get_snapshot("NVDA", weeks=8)
    assert snapshot.underlying.ticker == "NVDA"
    assert len(snapshot.options) == 8
    assert {quote.option_type for quote in snapshot.options} == {"CALL", "PUT"}


def test_mock_provider_rejects_unsupported_ticker():
    with pytest.raises(ValueError, match="Mock provider supports only NVDA"):
        MockMarketDataProvider().get_snapshot("AAPL")
```

- [ ] **Step 5: Add the deterministic JSON fixture and provider**

Create eight option rows across two expirations with fixed UTC timestamps. Load
the fixture through `importlib.resources`; do not call the network or use the
wall clock. Ensure `diagnostic()` returns
`{"provider": "mock", "connected": True, "mode": "deterministic"}`.

- [ ] **Step 6: Run focused and full Python checks**

Run: `uv run pytest tests/domain/test_market.py tests/adapters/test_mock_market.py -v`

Run: `uv run ruff check src tests`

Run: `uv run mypy src/argusfinance`

Expected: all commands exit 0.

- [ ] **Step 7: Commit normalized market contracts**

```bash
git add src/argusfinance/domain src/argusfinance/ports src/argusfinance/adapters tests/domain tests/adapters tests/fixtures
git commit -m "feat: add normalized market data contracts"
```

---

### Task 3: SQLite snapshot metadata repository

**Files:**
- Create: `src/argusfinance/storage/__init__.py`
- Create: `src/argusfinance/storage/database.py`
- Create: `src/argusfinance/storage/models.py`
- Create: `src/argusfinance/storage/repositories.py`
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/versions/0001_snapshot_metadata.py`
- Test: `tests/storage/test_snapshot_repository.py`

**Interfaces:**
- Consumes: `MarketSnapshot.snapshot_id`, ticker, timestamps, provider, status, and future Parquet path.
- Produces: `SnapshotMetadataRepository.add(...)`, `SnapshotMetadataRepository.get(snapshot_id)`, and `SnapshotMetadataRepository.latest_for_ticker(ticker)`.

- [ ] **Step 1: Write the repository round-trip test**

```python
from datetime import UTC, datetime

from argusfinance.storage.database import create_session_factory
from argusfinance.storage.models import Base
from argusfinance.storage.repositories import SnapshotMetadata, SnapshotMetadataRepository


def test_snapshot_metadata_round_trip(tmp_path):
    factory, engine = create_session_factory(f"sqlite:///{tmp_path / 'test.sqlite'}")
    Base.metadata.create_all(engine)
    repository = SnapshotMetadataRepository(factory)
    metadata = SnapshotMetadata(
        snapshot_id="00000000-0000-0000-0000-000000000001",
        ticker="NVDA",
        provider="mock",
        status="REALTIME",
        source_timestamp=datetime(2026, 8, 28, 20, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 8, 28, 20, 0, tzinfo=UTC),
        parquet_path="market/ticker=NVDA/date=2026-08-28/snapshot.parquet",
    )

    repository.add(metadata)

    assert repository.get(metadata.snapshot_id) == metadata
```

- [ ] **Step 2: Run the repository test and verify it fails**

Run: `uv run pytest tests/storage/test_snapshot_repository.py -v`

Expected: FAIL because storage modules do not exist.

- [ ] **Step 3: Implement engine, model, value object, and repository**

Use SQLAlchemy 2 declarative mappings. Store timestamps as timezone-aware UTC
values, reject duplicate snapshot IDs with a domain-specific
`DuplicateSnapshotError`, and return a frozen `SnapshotMetadata` dataclass.
Reattach UTC when SQLite returns a naive timestamp. Enable SQLite foreign keys
on connect. `latest_for_ticker` orders by retrieval timestamp and snapshot ID,
returning `None` when no row exists. The migration creates only the
`market_snapshot_metadata` table and its ticker/retrieved-at index.

- [ ] **Step 4: Verify migrations and repository behavior**

Run: `uv run alembic upgrade head`

Run: `uv run pytest tests/storage/test_snapshot_repository.py -v`

Expected: migration exits 0 and repository tests pass.

- [ ] **Step 5: Commit operational metadata storage**

```bash
git add alembic.ini migrations src/argusfinance/storage tests/storage/test_snapshot_repository.py
git commit -m "feat: persist market snapshot metadata"
```

---

### Task 4: Parquet snapshot writer and DuckDB reader

**Files:**
- Create: `src/argusfinance/storage/snapshots.py`
- Test: `tests/storage/test_snapshot_store.py`

**Interfaces:**
- Consumes: `MarketSnapshot`.
- Produces: `SnapshotStore.write(snapshot) -> Path`, `SnapshotStore.read(snapshot_id) -> MarketSnapshot`, and `SnapshotStore.delete(snapshot_id) -> None`.

- [ ] **Step 1: Write the immutable snapshot round-trip test**

```python
from argusfinance.adapters.mock_market import MockMarketDataProvider
from argusfinance.storage.snapshots import SnapshotStore


def test_parquet_snapshot_round_trip(tmp_path):
    expected = MockMarketDataProvider().get_snapshot("NVDA", weeks=8)
    store = SnapshotStore(tmp_path)

    path = store.write(expected)
    actual = store.read(expected.snapshot_id)

    assert path.suffix == ".parquet"
    assert actual == expected
    assert store.write(expected) == path
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `uv run pytest tests/storage/test_snapshot_store.py -v`

Expected: FAIL because `SnapshotStore` does not exist.

- [ ] **Step 3: Implement partitioned Parquet storage**

Write one normalized row per option leg and repeat snapshot/underlying provenance
columns on every row. Use the deterministic path
`market/ticker=<ticker>/date=<UTC-date>/snapshot=<uuid>.parquet`. Write to a
temporary sibling and atomically replace the destination. DuckDB reads the
single file and reconstructs immutable domain models ordered by expiration,
strike, and option type. `delete` removes only the exact UUID-addressed file and
is idempotent. If a snapshot is absent, raise `SnapshotNotFoundError`.

- [ ] **Step 4: Verify round-trip and schema**

Run: `uv run pytest tests/storage/test_snapshot_store.py -v`

Run: `uv run ruff check src tests`

Expected: all checks pass, including a test asserting the exact Parquet column names.

- [ ] **Step 5: Commit analytical snapshot storage**

```bash
git add src/argusfinance/storage/snapshots.py tests/storage/test_snapshot_store.py
git commit -m "feat: store normalized market snapshots"
```

---

### Task 5: Shared market service and HTTP contract

**Files:**
- Create: `src/argusfinance/services/__init__.py`
- Create: `src/argusfinance/services/market.py`
- Create: `src/argusfinance/bootstrap.py`
- Create: `src/argusfinance/api/dependencies.py`
- Create: `src/argusfinance/api/routes/__init__.py`
- Create: `src/argusfinance/api/routes/market.py`
- Modify: `src/argusfinance/api/app.py`
- Test: `tests/services/test_market_service.py`
- Test: `tests/api/test_market.py`

**Interfaces:**
- Consumes: `MarketDataProvider`, `SnapshotStore`, `SnapshotMetadataRepository`.
- Produces: `MarketService.capture(ticker, weeks=8) -> MarketSnapshot`, `MarketService.latest(ticker) -> MarketSnapshot`, `POST /api/market/{ticker}/snapshots`, and `GET /api/market/{ticker}/latest`.

- [ ] **Step 1: Write a service test proving single-write orchestration**

```python
def test_capture_persists_data_before_metadata(market_service, metadata_repository):
    snapshot = market_service.capture("NVDA", weeks=8)
    metadata = metadata_repository.get(str(snapshot.snapshot_id))

    assert metadata is not None
    assert metadata.ticker == "NVDA"
    assert market_service.latest("NVDA") == snapshot
```

- [ ] **Step 2: Run the service test and verify it fails**

Run: `uv run pytest tests/services/test_market_service.py -v`

Expected: FAIL because `MarketService` does not exist.

- [ ] **Step 3: Implement the service and composition root**

`capture` calls the provider once, writes Parquet, then commits SQLite metadata.
If metadata persistence fails, remove only the newly written Parquet file and
re-raise. `latest` finds the newest metadata row for a normalized ticker and
loads that exact Parquet snapshot. `build_container(settings)` owns concrete
construction and exposes a `Container.market_service` property.

- [ ] **Step 4: Write API contract tests**

```python
def test_capture_and_latest_use_same_snapshot(client):
    captured = client.post("/api/market/NVDA/snapshots?weeks=8")
    latest = client.get("/api/market/NVDA/latest")

    assert captured.status_code == 201
    assert latest.status_code == 200
    assert latest.json() == captured.json()
    assert captured.json()["underlying"]["ticker"] == "NVDA"


def test_unsupported_mock_ticker_is_explicit(client):
    response = client.post("/api/market/AAPL/snapshots?weeks=8")
    assert response.status_code == 422
    assert response.json()["detail"] == "Mock provider supports only NVDA"
```

- [ ] **Step 5: Implement routes and exception translation**

Return the Pydantic `MarketSnapshot` directly. Use status 201 for capture, 404
for absent latest snapshots, and 422 for provider input limitations. Include the
router from `create_app` and inject the service from `app.state.container`.

- [ ] **Step 6: Run service and API checks**

Run: `uv run pytest tests/services/test_market_service.py tests/api/test_market.py -v`

Run: `uv run mypy src/argusfinance`

Expected: all commands exit 0.

- [ ] **Step 7: Commit the shared market workflow**

```bash
git add src/argusfinance/services src/argusfinance/bootstrap.py src/argusfinance/api tests/services tests/api
git commit -m "feat: expose shared market snapshot service"
```

---

### Task 6: CLI and read-only IBKR diagnostics

**Files:**
- Create: `src/argusfinance/adapters/ibkr.py`
- Create: `src/argusfinance/cli.py`
- Modify: `pyproject.toml`
- Test: `tests/adapters/test_ibkr_diagnostic.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `build_container(settings)` and `MarketDataProvider.diagnostic()`.
- Produces: `argusfinance market snapshot NVDA --weeks 8`, `argusfinance market latest NVDA`, and `argusfinance provider diagnostic ibkr`.

- [ ] **Step 1: Write CLI output tests**

```python
from typer.testing import CliRunner

from argusfinance.cli import app


def test_market_snapshot_prints_snapshot_id(monkeypatch, tmp_path):
    monkeypatch.setenv("ARGUS_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("ARGUS_DATABASE_URL", f"sqlite:///{tmp_path / 'cli.sqlite'}")
    result = CliRunner().invoke(app, ["market", "snapshot", "NVDA", "--weeks", "8"])
    assert result.exit_code == 0
    assert "NVDA" in result.stdout
    assert "snapshot_id" in result.stdout
```

- [ ] **Step 2: Run the CLI test and verify it fails**

Run: `uv run pytest tests/test_cli.py -v`

Expected: FAIL because the CLI module does not exist.

- [ ] **Step 3: Implement Typer commands using the shared service**

The snapshot command calls `MarketService.capture`; latest calls
`MarketService.latest`. Serialize JSON with Pydantic's `model_dump_json(indent=2)`.
Register the entry point as `argusfinance = "argusfinance.cli:app"`.

- [ ] **Step 4: Implement the IBKR diagnostic boundary**

Define `IbkrConnectionSettings(host="127.0.0.1", port=7497, client_id=17,
readonly=True)`. `IbkrMarketDataProvider.diagnostic()` attempts only a connection
handshake through an injected `ib_async.IB` client factory, reports
connected/error state, and always disconnects. Add `ib_async` as a runtime
dependency. `get_snapshot` raises `NotImplementedError` with the exact message
`IBKR snapshot retrieval is not part of the foundation slice`. Unit tests use a
fake client and assert `readonly=True`; they never contact TWS or Gateway.

- [ ] **Step 5: Run CLI and adapter tests**

Run: `uv run pytest tests/test_cli.py tests/adapters/test_ibkr_diagnostic.py -v`

Expected: all tests pass without a running IBKR process.

- [ ] **Step 6: Commit CLI and diagnostic boundary**

```bash
git add pyproject.toml src/argusfinance/cli.py src/argusfinance/adapters/ibkr.py tests/test_cli.py tests/adapters/test_ibkr_diagnostic.py
git commit -m "feat: add CLI and IBKR diagnostics"
```

---

### Task 7: MCP market tools

**Files:**
- Create: `src/argusfinance/mcp_server.py`
- Test: `tests/test_mcp_server.py`

**Interfaces:**
- Consumes: `MarketService.capture` and `MarketService.latest`.
- Produces: MCP tools `capture_market_snapshot(ticker: str, weeks: int = 8)` and `get_latest_market_snapshot(ticker: str)`.

- [ ] **Step 1: Write direct tool-function tests**

```python
def test_mcp_capture_and_latest_share_snapshot(mcp_tools):
    captured = mcp_tools.capture_market_snapshot("NVDA", 8)
    latest = mcp_tools.get_latest_market_snapshot("NVDA")
    assert captured["snapshot_id"] == latest["snapshot_id"]
    assert captured["underlying"]["ticker"] == "NVDA"
```

- [ ] **Step 2: Run the MCP test and verify it fails**

Run: `uv run pytest tests/test_mcp_server.py -v`

Expected: FAIL because `mcp_server` does not exist.

- [ ] **Step 3: Implement an injectable MCP tool set**

Create `MarketMcpTools(service)` with ordinary Python methods returning
JSON-compatible dictionaries. Create `build_mcp_server(service)` and register
the two methods with the official SDK's FastMCP decorator. Keep registration at
the edge so unit tests do not require a transport. Add a `main()` that runs
STDIO and a `argusfinance-mcp` project entry point.

- [ ] **Step 4: Verify tool behavior and STDIO initialization**

Run: `uv run pytest tests/test_mcp_server.py -v`

Run: `uv run python -c "from argusfinance.mcp_server import build_mcp_server; print(build_mcp_server.__name__)"`

Expected: tests pass and the import check prints `build_mcp_server` without starting a transport.

- [ ] **Step 5: Commit MCP tools**

```bash
git add pyproject.toml src/argusfinance/mcp_server.py tests/test_mcp_server.py
git commit -m "feat: expose market snapshot MCP tools"
```

---

### Task 8: React market decision surface

**Files:**
- Create: `apps/dashboard/package.json`
- Create: `apps/dashboard/package-lock.json`
- Create: `apps/dashboard/vite.config.ts`
- Create: `apps/dashboard/tsconfig.json`
- Create: `apps/dashboard/index.html`
- Create: `apps/dashboard/src/main.tsx`
- Create: `apps/dashboard/src/App.tsx`
- Create: `apps/dashboard/src/api/market.ts`
- Create: `apps/dashboard/src/features/market/MarketSnapshotView.tsx`
- Create: `apps/dashboard/src/features/market/ExpirationTimeline.tsx`
- Create: `apps/dashboard/src/features/market/LiquidityChart.tsx`
- Create: `apps/dashboard/src/test/nvdaSnapshot.ts`
- Create: `apps/dashboard/src/styles.css`
- Test: `apps/dashboard/src/features/market/MarketSnapshotView.test.tsx`

**Interfaces:**
- Consumes: `GET /api/market/NVDA/latest` and its serialized `MarketSnapshot` schema.
- Produces: a local dashboard showing spot, status/freshness, expirations, call/put liquidity, and explicit missing-data state.

- [ ] **Step 1: Scaffold Vite React TypeScript and install test/chart dependencies**

Run: `npm create vite@latest apps/dashboard -- --template react-ts`

Run: `npm install`

Run: `npm install react-plotly.js plotly.js-dist-min`

Run: `npm install --save-dev vitest jsdom @testing-library/react @testing-library/jest-dom @types/react-plotly.js`

Expected: `package-lock.json` is generated and `npm run build` exits 0.

- [ ] **Step 2: Write the failing dashboard test**

```tsx
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { MarketSnapshotView } from "./MarketSnapshotView";
import { nvdaSnapshot } from "../../../test/nvdaSnapshot";

it("renders provenance, expirations, and visual sections", () => {
  render(<MarketSnapshotView snapshot={nvdaSnapshot} />);
  expect(screen.getByRole("heading", { name: "NVDA" })).toBeInTheDocument();
  expect(screen.getByText("REALTIME")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Expiration horizon" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Liquidity by strike" })).toBeInTheDocument();
});
```

- [ ] **Step 3: Run the component test and verify it fails**

Run: `npm test -- --run src/features/market/MarketSnapshotView.test.tsx`

Expected: FAIL because `MarketSnapshotView` does not exist.

- [ ] **Step 4: Implement the API types and accessible visual shell**

Use a dark, information-dense research-workbench direction rather than a generic
card dashboard. `fetchLatestSnapshot(ticker)` throws a typed error on non-2xx
responses. `MarketSnapshotView` renders exact timestamp/status text, a horizontal
expiration timeline, and a Plotly grouped bar chart of open interest by strike
and call/put type. Include visible loading, absent-snapshot, delayed-data, and
unavailable-Greeks states. Do not add strategy recommendation UI in this phase.

- [ ] **Step 5: Run frontend tests and build**

Run: `npm test -- --run`

Run: `npm run build`

Expected: all tests pass and Vite emits a production build.

- [ ] **Step 6: Commit the dashboard slice**

```bash
git add apps/dashboard
git commit -m "feat: visualize the NVDA market snapshot"
```

---

### Task 9: Project agents and local plugin shell

**Files:**
- Create: `.codex/config.toml`
- Create: `.codex/agents/company-analyst.toml`
- Create: `.codex/agents/market-options-analyst.toml`
- Create: `.codex/agents/historical-evidence-analyst.toml`
- Create: `.codex/agents/strategy-analyst.toml`
- Create: `.codex/agents/risk-critic.toml`
- Create: `.codex/agents/optionstrat-operator.toml`
- Create: `.codex-plugin/plugin.json`
- Create: `skills/evaluate-ticker/SKILL.md`
- Create: `agents/<role>/PLAYBOOK.md` for all six roles
- Create: `agents/<role>/CHECKLIST.md` for all six roles
- Create: `agents/<role>/SOURCES.md` for all six roles
- Create: `agents/<role>/lessons/pending.md` for all six roles
- Create: `agents/<role>/lessons/approved.md` for all six roles
- Create: `scripts/validate_agent_roster.py`
- Test: `tests/test_agent_roster.py`

**Interfaces:**
- Consumes: MCP tools from Task 7 and project commands from Task 6.
- Produces: exactly six named custom agents, a local plugin manifest, and an `evaluate-ticker` skill that delegates only to the five analytical roles.

- [ ] **Step 1: Write the failing roster-validation test**

```python
from pathlib import Path

from scripts.validate_agent_roster import validate_roster


def test_project_defines_exact_approved_roster():
    assert validate_roster(Path(".")) == {
        "company_analyst",
        "market_options_analyst",
        "historical_evidence_analyst",
        "strategy_analyst",
        "risk_critic",
        "optionstrat_operator",
    }
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `uv run pytest tests/test_agent_roster.py -v`

Expected: FAIL because roster files and validator do not exist.

- [ ] **Step 3: Create project agent definitions and concurrency policy**

Set `agents.enabled = true` and
`agents.max_concurrent_threads_per_session = 5`. Each TOML file defines exact
`name`, `description`, `developer_instructions`, and a read-only sandbox for the
five analytical roles. The OptionStrat operator receives browser/computer-use
instructions, must consume a typed handoff packet, verify every leg, and stop
for takeover. It receives no database-write permission.

- [ ] **Step 4: Create role playbooks and promotion rules**

Every playbook states scope, required inputs, output contract, failure states,
and explicit non-responsibilities. `pending.md` and `approved.md` begin with a
schema requiring date, evidence/evaluation ID, proposed lesson, scope, and
reviewer. No file contains ticker conclusions or secrets.

- [ ] **Step 5: Scaffold and validate the local plugin**

Use the built-in `plugin-creator` workflow to create a valid manifest named
`argusfinance`, package the `evaluate-ticker` skill, and reference the local MCP
server command `uv run argusfinance-mcp`. The skill must load workspace state,
capture a market snapshot, delegate the five analytical roles with bounded
outputs, wait for all results, run risk critique after the other evidence is
available, and return a structured synthesis without placing orders.

- [ ] **Step 6: Run roster and manifest checks**

Run: `uv run pytest tests/test_agent_roster.py -v`

Run: `uv run python scripts/validate_agent_roster.py`

Expected: both commands exit 0 and report exactly six roles.

- [ ] **Step 7: Commit agent and plugin scaffolding**

```bash
git add .codex .codex-plugin skills agents scripts/validate_agent_roster.py tests/test_agent_roster.py
git commit -m "feat: add fixed agent roster and plugin shell"
```

---

### Task 10: Local launcher and vertical-slice verification

**Files:**
- Create: `scripts/dev.py`
- Create: `tests/e2e/test_nvda_vertical_slice.py`
- Modify: `Makefile`
- Modify: `README.md`

**Interfaces:**
- Consumes: API app, CLI, MCP tool set, dashboard development server, and deterministic mock provider.
- Produces: `make dev`, `make test`, `make quality`, and one proof that all non-UI interfaces return the same persisted snapshot ID.

- [ ] **Step 1: Write the cross-interface failing test**

```python
def test_nvda_snapshot_identity_across_api_cli_and_mcp(vertical_slice):
    api_snapshot = vertical_slice.capture_with_api("NVDA", weeks=8)
    cli_snapshot = vertical_slice.latest_with_cli("NVDA")
    mcp_snapshot = vertical_slice.latest_with_mcp("NVDA")

    assert api_snapshot["snapshot_id"] == cli_snapshot["snapshot_id"]
    assert api_snapshot["snapshot_id"] == mcp_snapshot["snapshot_id"]
    assert api_snapshot["underlying"]["ticker"] == "NVDA"
```

- [ ] **Step 2: Run the E2E test and verify the fixture failure**

Run: `uv run pytest tests/e2e/test_nvda_vertical_slice.py -v`

Expected: FAIL because the vertical-slice fixture and launcher do not exist.

- [ ] **Step 3: Implement the test harness and launcher**

The E2E fixture builds one container against a temporary directory, calls the
FastAPI app through `TestClient`, invokes the Typer command with the same env,
and calls `MarketMcpTools` directly. `scripts/dev.py` launches Uvicorn and the
Vite development server as child processes, forwards termination to both, and
prints the exact local URLs. It does not daemonize or write PID files.

- [ ] **Step 4: Document local setup and explicit limitations**

README instructions include `uv sync`, `npm install --prefix apps/dashboard`,
`uv run alembic upgrade head`, `make test`, and `make dev`. State that the
foundation uses deterministic NVDA data, IBKR capture is not implemented yet,
the dashboard is local, and no live orders are supported.

- [ ] **Step 5: Run full verification**

Run: `uv run pytest -v`

Run: `uv run ruff check src tests scripts`

Run: `uv run mypy src/argusfinance`

Run: `npm test --prefix apps/dashboard -- --run`

Run: `npm run build --prefix apps/dashboard`

Run: `git diff --check`

Expected: every command exits 0, Python reports zero failed tests, Vitest reports zero failed tests, and Vite completes a production build.

- [ ] **Step 6: Commit the verified vertical slice**

```bash
git add README.md Makefile scripts/dev.py tests/e2e/test_nvda_vertical_slice.py
git commit -m "feat: complete local NVDA foundation slice"
```

## Completion evidence

Before marking this plan complete, record:

- Python test count and zero failures.
- Frontend test count and zero failures.
- Ruff and mypy exit status.
- Vite build exit status.
- The shared NVDA snapshot ID observed through API, CLI, and MCP.
- A screenshot of the local dashboard showing ticker, provenance/status,
  expiration horizon, and liquidity chart.
- `git status --short --branch` showing a clean branch.
- GitHub remote URL and successful push of every plan commit.

Phase 2 must not begin until this evidence is captured and the foundation slice
has been reviewed against the design specification.
