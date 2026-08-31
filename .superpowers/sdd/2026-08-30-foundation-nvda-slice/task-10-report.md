# Task 10 report: local launcher and NVDA vertical-slice proof

## Delivered

- `scripts/dev.py` starts Uvicorn and Vite as foreground child processes,
  prints their exact loopback URLs, forwards SIGINT/SIGTERM, terminates a
  surviving sibling, and reaps both children.
- `tests/e2e/test_nvda_vertical_slice.py` captures deterministic eight-week
  NVDA data through FastAPI, parses `market latest NVDA` CLI JSON, and reads MCP
  latest against the same temporary SQLite and snapshot state. It also covers
  launcher argument vectors, strict dashboard port binding, sibling cleanup,
  signal forwarding, and reaping without starting real servers.
- `Makefile` provides `make dev`, full Python/dashboard `make test`, and Python
  plus dashboard `make quality` targets while retaining the existing narrower
  targets.
- `README.md` documents locked setup, migrations, deterministic capture,
  local URLs, verification, the read-only IBKR diagnostic, and the explicit
  foundation limitations and OptionStrat user-takeover boundary.

Implementation commit: `bbbca04` (`feat: complete local NVDA foundation slice`).

## TDD evidence

### Vertical-slice RED

Command:

```bash
uv run pytest tests/e2e/test_nvda_vertical_slice.py -v
```

Initial result: exit 1; one test collected; setup failed with
`fixture 'vertical_slice' not found`. This was the intended missing shared-state
harness failure, not an import or configuration failure.

After adding the test-only temporary-state harness and launcher behavior tests,
the same command remained RED with one vertical-slice test passing and two
launcher tests failing with `FileNotFoundError` for the absent `scripts/dev.py`.

### Exact-port RED

Command:

```bash
uv run pytest tests/e2e/test_nvda_vertical_slice.py::test_launcher_starts_local_children_and_terminates_surviving_sibling -v
```

Result before the minimal fix: exit 1; the observed Vite argument vector lacked
`--strictPort`, so the printed `127.0.0.1:5173` URL was not guaranteed to match
the bound port. Adding only that flag turned the narrow test GREEN: 1 passed.

### Focused GREEN

Command:

```bash
uv run pytest tests/e2e/test_nvda_vertical_slice.py -v
```

Final result: 3 passed in 0.52s. API capture, CLI latest, and MCP latest all
observed snapshot ID `00000000-0000-0000-0000-000000000001`; the captured
underlying ticker was `NVDA`.

## Final verification

- `uv run pytest tests/e2e/test_nvda_vertical_slice.py -v` — 3 passed in 0.52s.
- `uv run pytest -v` — 67 passed in 0.86s.
- `uv run ruff check src tests scripts` — `All checks passed!`.
- `uv run mypy src/argusfinance` — no issues in 25 source files.
- `npm test --prefix apps/dashboard -- --run` — 3 files and 8 tests passed.
- `npm run build --prefix apps/dashboard` — exit 0; 23 modules transformed and
  production assets emitted in 1.03s.
- `git diff --check b083f08..HEAD` at `bbbca04` — exit 0.
- `make -n dev test quality` — exit 0 and expanded to the intended launcher,
  Python, dashboard, lint, typecheck, and build commands.

## Concerns

Vite's successful production build emits its existing advisory that the
minified JavaScript chunk is larger than 500 kB (4,311.97 kB; 1,316.93 kB
gzip). Dashboard code splitting is outside Task 10 ownership. No real dev
servers were started by the launcher tests, and no processes were left running.
