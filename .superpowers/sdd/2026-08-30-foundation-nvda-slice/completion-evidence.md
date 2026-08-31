# Foundation NVDA slice — completion evidence

Captures the evidence required by the "Completion evidence" section of
`docs/superpowers/plans/2026-08-30-foundation-nvda-slice.md`, plus the design
specification review that gates Phase 2.

Verified at `5eeff9e` (`docs: record task 10 port override fix`) on
`feat/foundation-nvda-slice`.

## Required evidence

| Item | Result |
| --- | --- |
| Python test count, zero failures | `uv run pytest -q` — **76 passed** in 1.75s |
| Frontend test count, zero failures | `npm test --prefix apps/dashboard -- --run` — **8 passed**, 3 files |
| Ruff exit status | `uv run ruff check src tests scripts migrations` — `All checks passed!`, exit 0 |
| mypy exit status | `uv run mypy src/argusfinance` — no issues in 25 source files, exit 0 |
| Vite build exit status | `npm run build --prefix apps/dashboard` — exit 0 |
| Shared NVDA snapshot ID | `00000000-0000-0000-0000-000000000001` through API, CLI, and MCP |
| Dashboard screenshot | `dashboard-nvda-snapshot.png` (this directory) |
| `git status --short --branch` clean | clean; 0 commits ahead of `origin/feat/foundation-nvda-slice` |
| Remote URL and push | `https://github.com/Apoorva87/ArgusFinance.git`; all 36 plan commits pushed |

## Shared snapshot identity

The same persisted snapshot was observed through every interface against one
state directory and one SQLite database:

- HTTP: `GET /api/market/NVDA/latest` returned `snapshot_id`
  `00000000-0000-0000-0000-000000000001`.
- CLI: `uv run argusfinance market snapshot NVDA --weeks 8` returned the same ID.
- MCP: `MarketMcpTools` latest returned the same ID.
- Dashboard: rendered `SNAPSHOT 00000000…` from the same API response, proxied
  through Vite to `127.0.0.1:8765`.

`tests/e2e/test_nvda_vertical_slice.py` enforces this identity — 12 passed.

Storage was verified on disk as partitioned Parquet:
`data/market/ticker=NVDA/date=2026-08-28/snapshot=00000000-0000-0000-0000-000000000001.parquet`.

## Dashboard screenshot

`dashboard-nvda-snapshot.png` was captured from the running launcher
(`uv run python scripts/dev.py`) at `http://127.0.0.1:5173` with live data
served by the local API. It shows all four required elements:

- **Ticker** — `NVDA` with underlying price `$180.2500000000`.
- **Provenance and status** — `source mock`, `2026-08-28 20:00 UTC`, `FROZEN`,
  plus a "Chain readout" panel carrying source, source timestamp, retrieval
  timestamp, snapshot creation time, and contract count.
- **Expiration horizon** — a two-point timeline, `Sep 18, 2026` to
  `Oct 16, 2026`, labelled "2 dates available".
- **Liquidity chart** — grouped call/put open interest by strike, with an
  accessible table alternative (175: 12,800 calls / 10,000 puts; 185: 11,300
  calls / 9,500 puts).

Browser console during capture contained one 404 for `/favicon.ico` and no
application errors.

This closes the gap recorded in the Task 8 ledger entry, where screenshot QA was
unavailable because no browser instance was connected.

## Design specification review

Reviewed against `docs/superpowers/specs/2026-08-30-argusfinance-design.md`
§19 Phase 1, with supporting checks against §2, §6, and §21.

| Phase 1 requirement | Status |
| --- | --- |
| Repository, local launcher, FastAPI, React, SQLite, DuckDB/Parquet | Met |
| Typed domain skeleton and database migrations | **Partially met** — see finding below |
| Mock/replay providers and IBKR connection diagnostics | Met |
| Fixed agent definitions, playbooks, plugin manifest, MCP shell | Met — six agents, six playbooks, manifest, MCP server |
| NVDA eight-week snapshot consistent across API, CLI/MCP, UI | Met |

Supporting principles confirmed:

- §6.2 — every datum carries source, source timestamp, retrieval timestamp, and
  a market-data status (`FROZEN`).
- §6.2 — normalized snapshots are partitioned Parquet read through DuckDB.
- §2.7 — no provider object crosses `MarketDataProvider`; the service depends
  only on the port.
- §2.8 — staleness is visible in the UI rather than hidden.
- §21 — IBKR access is read-only; no order path exists.

### Finding: schema ownership bypasses Alembic

`src/argusfinance/bootstrap.py:24` calls `Base.metadata.create_all(engine)`, so
the composition root creates the metadata table directly instead of leaving
schema ownership to the migrations required by §19 Phase 1.

Reproduced on pristine SQLite databases:

- Alembic alone: `alembic upgrade head` exits 0 and produces both
  `alembic_version` and `market_snapshot_metadata`, stamped
  `0001_snapshot_metadata`.
- Application first: any entry point (`argusfinance market snapshot`, the API,
  or MCP) creates `market_snapshot_metadata` with **no** `alembic_version` row.
  A subsequent `alembic upgrade head` then fails permanently with
  `sqlite3.OperationalError: table market_snapshot_metadata already exists`, and
  `alembic current` reports no stamped revision.

Impact is latent rather than functional: the slice works today because
`create_all` produces the correct schema. The consequence is that the setup
command documented in `README.md` fails against any database an application
entry point touched first, and Phase 2 migrations cannot be applied to an
existing local database.

This is recorded rather than fixed here; the fix changes which component owns
schema creation and is a design decision for the repository owner.
