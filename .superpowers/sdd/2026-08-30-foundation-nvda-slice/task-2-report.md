# Task 2 Report: normalized market contracts and deterministic NVDA provider

## Implementation summary

Implemented immutable, normalized Pydantic market-domain values; the
`MarketDataProvider` protocol; and a local-only deterministic `NVDA` mock
provider. The provider reads one packaged JSON fixture with `importlib.resources`,
uses fixed UTC timestamps and UUID values, supports only `NVDA` and `weeks=8`,
and makes no network or wall-clock calls.

Files changed by the feature commit:

- `src/argusfinance/domain/__init__.py`
- `src/argusfinance/domain/market.py`
- `src/argusfinance/ports/__init__.py`
- `src/argusfinance/ports/market_data.py`
- `src/argusfinance/adapters/__init__.py`
- `src/argusfinance/adapters/mock_market.py`
- `src/argusfinance/adapters/fixtures/__init__.py`
- `src/argusfinance/adapters/fixtures/nvda_snapshot.json`
- `tests/domain/test_market.py`
- `tests/adapters/test_mock_market.py`

No `pyproject.toml` change was necessary: the Hatchling wheel includes the JSON
resource under the package automatically.

## RED evidence

Domain stage, `uv run pytest tests/domain/test_market.py -v`:

```text
collected 0 items / 1 error
E   ModuleNotFoundError: No module named 'argusfinance.domain'
```

Provider stage, `uv run pytest tests/adapters/test_mock_market.py -v`:

```text
collected 0 items / 1 error
E   ModuleNotFoundError: No module named 'argusfinance.adapters'
```

## GREEN and final verification

```text
$ uv run pytest tests/domain/test_market.py tests/adapters/test_mock_market.py -v
9 passed in 0.04s

$ uv run pytest -v
10 passed in 0.14s

$ uv run ruff check src tests
All checks passed!

$ uv run mypy src/argusfinance
Success: no issues found in 11 source files

$ git diff --check
exit 0 (no output)
```

Installed-package resource review:

```text
$ uv build --wheel --out-dir /private/tmp/argusfinance-task2-wheel
Successfully built .../argusfinance-0.1.0-py3-none-any.whl

$ unzip -l .../argusfinance-0.1.0-py3-none-any.whl
argusfinance/adapters/fixtures/__init__.py
argusfinance/adapters/fixtures/nvda_snapshot.json
```

## Self-review

- Scope is limited to the assigned domain, port, adapter, fixture, and tests.
- Frozen Pydantic models normalize tickers, reject naive timestamps, and reject
  invalid numeric bounds and an ask below bid.
- The snapshot uses a UUID and tuple option collection; repeated provider calls
  compare equal because all fixture values are fixed.
- The provider boundary returns only `MarketSnapshot`; it does not expose
  provider-specific objects.
- Fixture loading was checked from a built wheel, not only from the editable
  source tree.

## Commit and deviations

Feature commit: `6835ba711bc8d83397c80de985ec068591baa1e3`

Deviation: the plan's obsolete `tests/fixtures/nvda_snapshot.json` location was
intentionally not created. The canonical packaged fixture follows the task brief
preflight ruling. The verification report is committed separately after the
feature commit so it can record that immutable commit SHA.
