# Task 3 Report: SQLite snapshot metadata repository

## Implementation summary

Implemented the local SQLAlchemy 2 operational-metadata boundary for immutable
market snapshots. The repository persists only snapshot provenance and Parquet
location metadata; it does not store option rows or provider-specific objects.
SQLite connections enable foreign keys, sessions are short-lived context
managers, timestamps are canonicalized to UTC, and duplicate snapshot IDs raise
`DuplicateSnapshotError` after a rollback.

Feature files committed in `25976ba6d69ffd12b263a483bb2c1ce0a3200c56`:

- `alembic.ini`
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions/0001_snapshot_metadata.py`
- `src/argusfinance/storage/__init__.py`
- `src/argusfinance/storage/database.py`
- `src/argusfinance/storage/models.py`
- `src/argusfinance/storage/repositories.py`
- `tests/storage/test_snapshot_repository.py`

The Alembic environment uses the application-aligned fallback
`sqlite:///db/workspace.sqlite` and accepts `ARGUS_DATABASE_URL` for a
disposable migration target.

## RED evidence

The new integration test file was written before the storage package existed:

```text
$ uv run pytest tests/storage/test_snapshot_repository.py -v
collected 0 items / 1 error
E   ModuleNotFoundError: No module named 'argusfinance.storage'
```

The final focused suite covers round-trip retrieval, missing IDs/tickers,
deterministic latest lookup, ticker normalization, naive timestamp rejection,
UTC reattachment/canonicalization, and duplicate-ID rollback behavior.

## GREEN and migration evidence

```text
$ UV_CACHE_DIR=/private/tmp/argusfinance-uv-cache uv run pytest \
    tests/storage/test_snapshot_repository.py -v
8 passed in 0.12s
```

Migration validation used only the disposable
`/private/tmp/argusfinance-task-3-migration.sqlite` target:

```text
$ ARGUS_DATABASE_URL=sqlite:////private/tmp/argusfinance-task-3-migration.sqlite \
    uv run alembic upgrade head
Running upgrade  -> 0001_snapshot_metadata

$ sqlite schema inspection
[('market_snapshot_metadata',)]
[('ix_market_snapshot_metadata_ticker_retrieved_at',)]

$ ARGUS_DATABASE_URL=sqlite:////private/tmp/argusfinance-task-3-migration.sqlite \
    uv run alembic downgrade base
Running downgrade 0001_snapshot_metadata ->

$ sqlite schema inspection after downgrade
[]

$ ARGUS_DATABASE_URL=sqlite:////private/tmp/argusfinance-task-3-migration.sqlite \
    uv run alembic upgrade head
Running upgrade  -> 0001_snapshot_metadata
```

## Full checks

```text
$ uv run pytest -v
19 passed in 0.24s

$ uv run ruff check src tests migrations
All checks passed!

$ uv run mypy src/argusfinance
Success: no issues found in 15 source files

$ git diff --check
exit 0 (no output)
```

## Self-review

- The model and migration both create exactly one table and the same named
  `(ticker, retrieved_at)` index; the downgrade drops those objects only.
- `add` rejects naive timestamps before opening a transaction, canonicalizes
  aware values to UTC, rolls back `IntegrityError`, and re-raises the
  domain-specific duplicate error.
- Hydration reattaches UTC to SQLite's naive datetime values; normalized ticker
  storage and lookup are covered by integration tests.
- The query orders `retrieved_at DESC, snapshot_id DESC`, so equal retrieval
  times are deterministic.
- No runtime database resides in the worktree. The only migration database was
  placed under `/private/tmp`; no database, cache, or generated artifact was
  staged.

## Deviation and concern

The first migration command attempted to use the default UV cache and failed
before Alembic ran because the sandbox denied access to
`/Users/akarnik/.cache/uv`. An escalated retry was interrupted by the user and
produced no migration evidence. Subsequent checks used the task-local writable
UV cache at `/private/tmp/argusfinance-uv-cache`; this was an environment
constraint, not a migration defect. The initial root-level generated SQLite
file was deleted after identifying that it was unignored; later migration
validation used the explicit disposable URL above.

The report is committed separately after the immutable feature commit so it can
record that commit SHA.

## Review round 1: fresh-clone Alembic database parent

Review finding: `alembic.ini` correctly used the application default
`sqlite:///db/workspace.sqlite`, but a fresh clone has no `db/` directory.
Alembic attempted its first SQLite connection before any code created that
parent and therefore could not open the file.

Review-fix commit: `ffd4f94aef53449f3c9207cc41e608f01a3a228c`.

RED evidence, with no `db/` directory present:

```text
$ uv run alembic upgrade head
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file
```

The focused regression test was then added before production code. It creates a
real engine for `tmp_path / "missing" / "nested" / "metadata.sqlite"` and
connects to it. Before the fix, that test failed with the same SQLite
`OperationalError`; the focused suite result was `1 failed, 8 passed`.

The shared `ensure_sqlite_file_parent(database_url)` helper parses URLs with
SQLAlchemy, creates only the parent for file-backed SQLite paths, and skips
non-SQLite, database-less, and `:memory:` URLs. It is invoked from both
`create_session_factory` and Alembic's online migration path before engine
construction.

GREEN/default-migration evidence:

```text
$ uv run pytest tests/storage/test_snapshot_repository.py -v
9 passed in 0.11s

$ uv run alembic upgrade head
Running upgrade  -> 0001_snapshot_metadata

$ git check-ignore -v db/workspace.sqlite
.gitignore:23:db/*.sqlite*  db/workspace.sqlite
```

The generated `db/workspace.sqlite` and its empty `db/` parent were removed
after the check; neither runtime state nor a cache was staged. Final suite:

```text
$ uv run pytest -v
20 passed in 0.23s

$ uv run ruff check src tests migrations
All checks passed!

$ uv run mypy src/argusfinance
Success: no issues found in 15 source files

$ git diff --check
exit 0 (no output)
```
