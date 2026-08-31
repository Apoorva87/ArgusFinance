# Task 6 Report: CLI and read-only IBKR diagnostics

## Delivered

- Added the `argusfinance` Typer script with `market snapshot`, `market latest`,
  and `provider diagnostic ibkr` commands.
- Each market invocation creates `Settings()` afresh, builds the shared local
  container, and uses `MarketService.capture` or `MarketService.latest`.
- Snapshot commands emit pretty Pydantic JSON; expected input/missing-latest
  errors use concise stderr text and a non-zero exit.
- Added a typed, injected `ib_async` client boundary. Its diagnostic only uses
  `connect`, `isConnected`, and `disconnect`; snapshot retrieval remains
  explicitly out of scope.
- Added bounded runtime dependency `ib_async>=2.1,<3` and regenerated `uv.lock`.

## TDD evidence

### CLI RED/GREEN

- `uv run pytest tests/test_cli.py -v` initially failed at collection with
  `ModuleNotFoundError: No module named 'argusfinance.cli'`.
- After the minimal CLI implementation, the four snapshot/latest JSON, identity,
  unsupported ticker, missing-latest, and environment-scoped-state tests passed.
- The provider diagnostic command test then failed because
  `argusfinance.cli.IbkrMarketDataProvider` was not yet present; it passed after
  adding the command at that boundary.

### IBKR RED/GREEN

- `uv run pytest tests/adapters/test_ibkr_diagnostic.py -v` initially failed at
  collection with `ModuleNotFoundError: No module named 'argusfinance.adapters.ibkr'`.
- The fake-client tests passed after the adapter was implemented. The exception
  diagnostic was subsequently made red again and then green with a redacted,
  concise `connection failed` error message.

## Fake-client call evidence

The success fake recorded exactly one call:

```python
{
    "host": "127.0.0.1",
    "port": 7497,
    "clientId": 17,
    "timeout": 4,
    "readonly": True,
}
```

It recorded one `disconnect()` call on success, false connection state, and
raised exception. Its attribute guard would fail the test if any account,
position, market-data, order, or other client method were accessed.

## Verification

- `uv lock` — resolved `ib-async 2.1.0` and lock dependencies.
- `uv run pytest tests/test_cli.py tests/adapters/test_ibkr_diagnostic.py -v` — 9 passed.
- `uv run pytest -v` — 47 passed.
- `uv run ruff check src tests migrations` — passed.
- `uv run mypy src/argusfinance` — passed, 24 source files checked.
- `uv run argusfinance --help` — passed; lists `market` and `provider`.
- `git diff --check` — passed before feature commit.

## Self-review

- The default factory imports and constructs the official `ib_async.IB` only at
  the outer boundary; tests inject fakes and never contact TWS/Gateway.
- `readonly=True`, an explicit short timeout, and documented `clientId` spelling
  are passed on every connection attempt.
- `disconnect()` is in `finally`; failures return a redacted concise error rather
  than exposing arbitrary client exception details.
- No account, position, order, or market-data operation is represented or called.
- CLI commands delegate through the existing shared service and emit stable JSON.
- Changes are limited to Task 6's owned files and dependency lock update.

## Commit and concerns

- Feature commit: `5f0495e043bf43c869c5f40223c625b5e9105131` (`feat: add CLI and IBKR diagnostics`).
- No live IBKR process was contacted. No remaining concerns.
