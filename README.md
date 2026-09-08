# ArgusFinance

ArgusFinance is a local-first options research workbench. The current
foundation captures one deterministic NVDA market snapshot and exposes the same
persisted data through FastAPI, the CLI, MCP tools, and a local React dashboard.

## Local setup

Install the locked Python and dashboard dependencies, then apply the SQLite
metadata migration:

```bash
uv sync --locked
npm ci --prefix apps/dashboard
uv run alembic upgrade head
```

The migration step is required. Alembic owns the operational schema; no
application entry point creates tables on startup, so a database that has not
been upgraded reports a missing `market_snapshot_metadata` table.

Runtime paths and the API port can be overridden with the `ARGUS_` settings in
`.env.example`. The API host is intentionally local-only.

Capture the deterministic eight-week NVDA fixture from the command line:

```bash
uv run argusfinance market snapshot NVDA --weeks 8
```

For offline replay in tests or local tooling, inject a JSON path into
`ReplayMarketDataProvider`. It validates the requested ticker and the
eight-week horizon, returns the normalized `MarketSnapshot` contract, and
never contacts a broker or network:

```python
from argusfinance.adapters import ReplayMarketDataProvider

provider = ReplayMarketDataProvider("path/to/snapshot.json")
snapshot = provider.get_snapshot("NVDA", weeks=8)
```

Then start both foreground development processes:

```bash
make dev
```

The launcher prints and serves these local URLs:

- API: <http://127.0.0.1:8765>
- Dashboard: <http://127.0.0.1:5173>

Press Ctrl-C to stop both processes. If either process exits, the launcher
terminates and reaps its sibling.

## Agent clients

`skills/` is the single source of truth for the `evaluate-ticker` workflow. Two
clients discover it by different conventions, so `make install-skills` links the
one directory into the location Claude Code expects:

- **Codex** reads `skills/` directly through `.codex-plugin/plugin.json`, along
  with the six roles in `.codex/config.toml`.
- **Claude Code** reads `.claude/skills/`, which `make install-skills` points at
  `skills/` with a relative symlink. Restart the session to pick up a newly
  linked skill.

Both clients read the MCP server from `.mcp.json`, which exposes
`capture_market_snapshot` and `get_latest_market_snapshot` over stdio.

The workflow's analytical roles (`company_analyst`, `market_options_analyst`,
`historical_evidence_analyst`, `strategy_analyst`, `risk_critic`) are versioned
playbooks under `agents/`. They are role definitions, not running code; the
orchestration that dispatches them is Phase 2 and later work.

## Verification

Run all Python and dashboard tests:

```bash
make test
```

Run Python lint and strict type checking plus dashboard tests and a production
build:

```bash
make quality
```

## Read-only IBKR diagnostic

With a local TWS or IB Gateway paper endpoint available on `127.0.0.1:7497`,
run the startup-minimized read-only diagnostic handshake:

```bash
uv run argusfinance provider diagnostic ibkr
```

The connection is forced to read-only mode and passes `StartupFetchNONE` to
disable ib_async's optional startup account, order, and execution fetch groups.
ib_async still performs baseline connection synchronization, including
positions. ArgusFinance does not request a market snapshot or take any order
action.

## Current limitations

- Foundation market data is the deterministic NVDA fixture. The mock provider
  loads the packaged fixture, while `ReplayMarketDataProvider` supports an
  injected local JSON path for offline replay.
- IBKR is diagnostic-handshake only. IBKR capture is not implemented.
- The dashboard and API run locally; there is no hosted ArgusFinance service.
- Paper and live order staging and placement are not implemented or permitted.
- Any future OptionStrat handoff requires explicit user takeover. ArgusFinance
  does not open, prefill, or operate OptionStrat.

The approved architecture and deferred phases are described in
[`docs/superpowers/specs/2026-08-30-argusfinance-design.md`](docs/superpowers/specs/2026-08-30-argusfinance-design.md).
