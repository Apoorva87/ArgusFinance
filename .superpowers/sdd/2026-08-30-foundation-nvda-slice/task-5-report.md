# Task 5 Report: Shared market service and HTTP contract

## Delivered

- Added `MarketService` as the sole capture/latest persistence workflow.
- Added frozen dependency `Container` and `build_container(settings)` for SQLite schema, metadata repository, Parquet snapshot store, deterministic provider, and singleton service composition.
- Added FastAPI container dependency and market capture/latest routes.
- Updated `create_app` to accept an optional container, retain `app.state.settings`, save `app.state.container`, include the market router, and preserve `/health` payload.
- Added a narrowly authorized pytest import-mode setting because the planned `tests/api/test_market.py` and existing `tests/domain/test_market.py` share a basename.

## TDD evidence

### Service RED

`uv run pytest tests/services/test_market_service.py -v` initially failed at collection with `ModuleNotFoundError: No module named 'argusfinance.services'`.

### Service GREEN

The focused service/API command passed all 9 tests. Service coverage includes provider single-call capture, metadata/latest identity, relative Parquet metadata, absent metadata, absent referenced Parquet, cleanup of a new file after metadata failure, and preservation of an immutable pre-existing file after metadata failure.

### API RED

With the market router intentionally absent from the app integration, `uv run pytest tests/api/test_market.py -v` produced the expected route-absent failures: capture and provider-error POSTs returned 404 rather than 201/422, and latest returned the framework `Not Found` detail rather than the contract detail.

### API GREEN

After router integration, capture/latest JSON identity, 201/200 status codes, exact unsupported-ticker 422 detail, stable missing-latest 404 detail, and unchanged health response all passed.

## Rollback review

`capture` reads the snapshot UUID through the public `SnapshotStore.read` API before writing. If metadata persistence fails, it calls `delete` only when that UUID was absent before the write. Tests prove both new-file cleanup and preservation/readability of an existing immutable file on a duplicate/idempotent write path.

## Verification

- `uv run pytest tests/services/test_market_service.py tests/api/test_market.py -v` — 9 passed.
- `uv run pytest -v` — 38 passed.
- `uv run ruff check src tests migrations` — passed.
- `uv run mypy src/argusfinance` — passed, 22 source files checked.
- `git diff --check` — passed.

The first exact full-suite run exposed the duplicate bare test-module name collection failure. The authorized `addopts = ["--import-mode=importlib"]` pytest configuration change fixed that infrastructure issue; the final exact full-suite command passed.

## Self-review

- Provider invocation happens once before persistence; metadata derives solely from that normalized snapshot and the final root-relative Parquet path.
- Unexpected storage/programming exceptions remain unconverted; only provider input rejection maps to 422 and unavailable latest snapshots map to 404.
- The service returns the stored snapshot after capture, ensuring capture/latest serialize identical normalized decimal values.
- Container construction happens once per app construction and request injection reads `app.state.container.market_service` without rebuilding dependencies.
- No prior storage/domain code or later-task areas were modified.

## Commits and concerns

- Feature commit: `6d163ae7967fcdf6f8f17210f62fe06f60e3fb56` (`feat: expose shared market snapshot service`).
- Report commit follows this file.
- No remaining concerns.
