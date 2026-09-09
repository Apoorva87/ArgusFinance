# ArgusFinance

ArgusFinance is a local-first options research workbench. It displays saved
market snapshots for NVDA, AAPL, MSFT, AMZN, GOOGL, META, and TSLA, evaluates
expiration payoff from stored option quotes, and preserves immutable strategy
entry evidence through FastAPI, the CLI, MCP tools, and a local React dashboard.
Snapshots can be imported from connected IBKR evidence; a deterministic NVDA
fixture remains available for offline demos.

## Local setup

Install the locked Python and dashboard dependencies, then apply the SQLite
metadata migration:

```bash
make install
make migrate
```

The migration step is required. Alembic owns the operational schema; no
application entry point creates tables on startup, so a database that has not
been upgraded reports a missing `market_snapshot_metadata` table. The command
uses `ARGUS_DATABASE_URL` from the environment or `.env`, matching the runtime
settings used by the application.

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

## Strategy Lab workflow

Open the dashboard and use the top navigation to move between the existing
Market explorer, Strategy Lab, and Saved Strategies. If no evidence has been
captured, **Load demo snapshot** persists the packaged deterministic NVDA data.
It is always labeled frozen and hypothetical.

Strategy Lab starts with the September 18, 2026 NVDA 175/185 bull call vertical
when those contracts exist in the snapshot. Natural pricing buys the 175 call
at its $8.80 ask and sells the 185 call at its $3.75 bid, producing a $505 net
debit and maximum loss, $495 maximum profit, and a $180.05 break-even before
fees. Select one expiration and up to four BUY or SELL call/put legs, then set
quantity, pricing, entry fees, status, thesis, and optional price or review-date
boundaries.

Choose **Evaluate strategy** to request backend-calculated payoff points, exact
risk limits, break-evens, and snapshot-quoted net Greeks. The chart and its text
scenario table use those returned values. Warnings retain their backend text;
missing Greeks remain unavailable, and unlimited tails are identified beyond
the finite chart. Any draft edit clears the result and disables saving until a
new evaluation completes.

Choose **Save strategy** after evaluation, then open **Saved Strategies** to
review the original thesis, boundaries, resolved legs and entry premiums,
pricing, payoff, source timestamp, and snapshot ID. Saved research remains
available when no latest market snapshot exists. WATCH, PAPER, REAL_MANUAL, and
SHADOW are research record labels; they do not simulate or place orders.

## Seven-stock dashboard and real snapshots

Select a ticker above the Market or Strategy Lab view. **Reload saved data**
reads the newest snapshot already in the local database. It does not contact
IBKR or provide streaming quotes. Switching ticker or snapshot resets the draft
so a prior stock's legs cannot carry into the next evaluation.

Use the `evaluate-ticker` skill with an explicit dashboard request, for example:

> Refresh the ArgusFinance dashboards for NVDA, AAPL, MSFT, AMZN, GOOGL,
> META, and TSLA using connected IBKR data. Capture and display snapshots only.

The skill's [refresh reference](skills/evaluate-ticker/references/dashboard-refresh.md)
documents exact US contract selection, bounded option sampling, raw-response
retention, and the schema-v1 import envelope. An agent with the connected IBKR
tools collects the data; the local web app does not have access to that chat
connector. On another machine, install the project, enable the IBKR connector
in the agent client, and run the same skill workflow.

For a collected bundle, use the reusable importer:

```bash
uv run argusfinance market import-ibkr data/connector-captures/NVDA.json
uv run argusfinance market latest NVDA
```

CLI, API and MCP must use the same `ARGUS_DATABASE_URL` and `ARGUS_STATE_DIR`.
The importer validates the raw bundle, preserves source and retrieval times,
and writes through the same immutable storage workflow as capture. Reimporting
the same bundle is idempotent. HTTP `POST /api/market/import` and MCP
`import_market_snapshot` accept already normalized snapshots.

The dashboard shows the imported coverage notes and data quality. Missing IV,
Greeks, option source timestamps, volume and open interest remain unavailable.
Frozen/delayed options are identified independently of the underlying status;
a REALTIME underlying label does not make its options live. Connector IV is
currently not imported because its units are unspecified. Missing or crossed
bid/ask quotes are skipped and counted. Monetary values are rounded half-even
to the existing ten-decimal storage precision to remove JSON float artifacts.
Quoted Greeks, when supplied, use twelve decimal places; values outside the
storage precision remain unavailable.
Partial open-interest totals are labeled as partial.

This capture-and-display mode does not run the full company, historical,
strategy and risk research workflow. Ask for a full evaluation when that
analysis is wanted. Local captured data is ignored by Git; recreate it through
the skill or copy the configured local database and snapshot files together.

## Agent clients

Run `make install-agents` after cloning on another machine (Python 3.12+).
This validates all six project-local Codex roles and their playbooks, then
installs the Claude Code skill link. `make install` runs this step automatically;
`make quality` checks the same roster. No user-global agent configuration is
needed. Open Codex from the repository and trust it when prompted, then start a
new session to load the project roles. Claude Code shares the workflow skill;
the `.codex/agents/*.toml` files are Codex-specific role definitions.

Role `config_file` paths resolve relative to `.codex/config.toml`, so they use
`agents/<role>.toml`, not `.codex/agents/<role>.toml`. The validator checks the
resolved files, required role fields, playbooks, and research authority limits.
Use `make validate-agents` to check without installing links. This follows the
[Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

`skills/` is the single source of truth for the `evaluate-ticker` workflow. Two
clients discover it by different conventions, so `make install-skills` links the
one directory into the location Claude Code expects:

- **Codex** reads `skills/` directly through `.codex-plugin/plugin.json`, along
  with the six roles in `.codex/config.toml`.
- **Claude Code** reads `.claude/skills/`, which `make install-skills` points at
  `skills/` with a relative symlink. Restart the session to pick up a newly
  linked skill.

The MCP server is configured in `.mcp.json`. When loaded by the client, it
exposes market capture/import/latest and strategy evaluate/save/list/get over
stdio. Local server configuration alone does not guarantee the current chat
session has exposed its tools; the CLI is an equivalent local entry point.

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

- The default capture provider is the deterministic NVDA fixture. Real data
  is imported from connected IBKR snapshots through the skill/CLI workflow;
  dashboard reload reads saved evidence. `ReplayMarketDataProvider` also supports
  an injected normalized JSON path for offline replay.
- Strategy analytics cover exact expiration payoff and quoted snapshot Greeks.
  Pre-expiration price/time/volatility surfaces, model-derived Greeks,
  calendars, and richer eligibility or evidence scoring are deferred.
- Saved strategies preserve entry evidence. Active boundary monitoring,
  entry-versus-current comparisons, adjustments, fills, and order lifecycle
  workflows are deferred.
- The local TWS adapter remains diagnostic-handshake only. Current IBKR
  collection uses the agent's connected tools and the reusable snapshot importer.
- The dashboard and API run locally; there is no hosted ArgusFinance service.
- Paper and live order staging and placement are not implemented or permitted.
- Any future OptionStrat handoff requires explicit user takeover. ArgusFinance
  does not open, prefill, or operate OptionStrat.

The approved architecture and deferred phases are described in
[`docs/superpowers/specs/2026-08-30-argusfinance-design.md`](docs/superpowers/specs/2026-08-30-argusfinance-design.md).
