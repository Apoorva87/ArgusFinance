# Task 4 Report: Parquet snapshot writer and DuckDB reader

## Files

- `src/argusfinance/storage/snapshots.py`
- `tests/storage/test_snapshot_store.py`

## TDD evidence

RED:

```text
uv run pytest tests/storage/test_snapshot_store.py -v
ModuleNotFoundError: No module named 'argusfinance.storage.snapshots'
```

GREEN:

```text
uv run pytest tests/storage/test_snapshot_store.py -v
8 passed in 0.13s
```

## Final checks

```text
uv run pytest tests/storage/test_snapshot_store.py -v  # 8 passed
uv run pytest -v                                      # 28 passed
uv run ruff check src tests migrations                 # All checks passed
uv run mypy src/argusfinance                           # Success: no issues found in 16 source files
git diff --check                                       # exit 0
```

## Path and schema evidence

- The exact tested output path is
  `market/ticker=NVDA/date=2026-08-28/snapshot=00000000-0000-0000-0000-000000000001.parquet`.
- PyArrow writes the required stable 25-column explicit schema, including
  timezone-aware UTC timestamps and explicit `decimal128` financial columns.
- DuckDB reads exactly one validated UUID-addressed Parquet path with a bound
  query parameter and orders rows by expiration, strike, and option type.

## Self-review

- UUIDs are parsed before lookup; reads and deletes match only the exact
  `snapshot=<UUID>.parquet` filename beneath the injected root.
- Writes use a temporary sibling then `os.replace`, and clean the temporary
  file if PyArrow or replacement fails.
- Existing UUID files are never overwritten: equal canonical content is
  idempotent and different content raises `SnapshotConflictError`.
- Decimal values pass directly through PyArrow and DuckDB; reconstruction uses
  Pydantic domain models to retain Decimal, UUID, date, UTC timestamp, enum,
  and tuple semantics.
- The DuckDB connection is closed in `finally`; no runtime Parquet files are
  created in the repository.

## Commit

Implementation commit: `8a6d7efeafdd6a8ea3f6ff505990b88c6742f5b7`

## Deviations and concerns

None. PyArrow lacks a `py.typed` marker in this environment, so its two imports
use narrowly scoped `import-untyped` mypy suppressions.
