# Seven-stock Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Populate the existing ArgusFinance dashboard with real saved evidence for seven selected stocks.
**Architecture:** Connected IBKR tool responses are normalized and imported into shared immutable storage. The existing React views select ticker-specific snapshots.
**Tech Stack:** Python, Pydantic, FastAPI, Typer, MCP, Parquet, React, TypeScript, Vitest.
**Spec:** docs/superpowers/specs/2026-09-09-seven-stock-dashboard-design.md

## Global Constraints

- No new runtime dependencies. No undocumented provider endpoints. No automatic orders or external publication.
- Use the existing feature worktree. Preserve all existing fixtures, saved evaluations and role definitions.
- Missing values remain null. Do not manufacture quote timestamps, prices, IV or Greeks.
- Tickers: NVDA, AAPL, MSFT, AMZN, GOOGL, META, TSLA.

### Task 1: Import real evidence through shared backend contracts

Ownership: src/argusfinance, tests. No dashboard or docs edits.
Files: domain/market.py, storage/snapshots.py, services/market.py,
services/strategies.py, api/routes/market.py, cli.py, mcp_server.py;
new adapters/ibkr_connector.py and tests/test_ibkr_connector.py; related existing tests.

Interfaces: MarketService.import_snapshot(snapshot: MarketSnapshot) -> MarketSnapshot;
normalize_ibkr_bundle(payload: dict[str, object]) -> MarketSnapshot;
CLI `market import-ibkr <json-file>`; MCP `import_market_snapshot(snapshot: dict[str, object])`;
HTTP `POST /api/market/import`. Existing capture and latest contracts remain.
Option source_timestamp, volume, open_interest, implied_volatility become nullable;
MarketDataStatus gains FROZEN_DELAYED. MarketSnapshot.notes is tuple[str,...] = ().
Underlying timestamp remains required. Preserve old Parquet snapshots without notes.

- [x] Write failing tests for raw bundle normalization, invalid IV to null, correct
  call/put OI, missing bid/ask timestamp remains null, crossed/missing quote skip
  note, no usable options rejection, invalid underlying rejection, nullable
  Parquet round-trip and old snapshot compatibility. Use representative raw
  response fields: last {price:226.06,ts:1788933498}, top-status {status:REALTIME},
  bid-ask {bid:5.55,ask:5.65}, option-midpoint-iv {annualIv:-15.874,isValid:false},
  option-open-interest {callInterest:46321,putInterest:0}, volume {volume:0}.
- [x] Run the new tests and record expected failures before implementation.
- [x] Implement normalization and reuse capture's lock/write/metadata/compensation
  path for imports. Unknown status maps to UNAVAILABLE; no underlying source ts
  rejects import. Null option timestamp never calls arithmetic. Imported quotes
  warn for missing timestamps, IV and frozen/delayed status.
- [x] Verify HTTP/CLI/MCP imports see the same saved snapshot; input errors are
  explicit and UUID conflict remains immutable. Run relevant backend tests,
  Ruff and strict mypy; self-review and commit owned files only.

### Task 2: Seven-ticker dashboard with truthful provenance

Ownership: apps/dashboard only. Backend schema is Task 1 contract above.
Files: src/App.tsx, api/market.ts, features/market/*, styles.css;
affected tests plus App.test.tsx.
Interfaces: fetchLatestSnapshot(ticker, signal) remains; response now permits
null option source_timestamp/volume/open_interest/implied_volatility, optional
notes and FROZEN_DELAYED. Underlying timestamp remains required.

- [x] Write failing tests for ticker switching to AAPL, missing non-NVDA state
  without demo action, stale response rejection, ticker changes resetting
  Strategy Lab, reload action, null OI not appearing as measured zero, and
  frozen options warning alongside realtime underlying.
- [x] Run new tests and record expected failures.
- [x] Add accessible seven-ticker selection, reload saved snapshot, clear draft
  on ticker/snapshot change, abort plus identity guards for all response paths.
  Preserve independent Saved Strategies access and explicitly labeled NVDA demo.
- [x] Show snapshot age/retrieval timestamps and notes; disclose sampled coverage,
  frozen option statuses, absent source timestamps, null IV/OI/Greeks. Partial
  liquidity totals must say partial and never imply missing contracts equal zero.
  Match existing workbench styling with responsive selector; no new dependencies.
- [x] Run dashboard tests and production build; self-review and commit owned files.

### Task 3: Populate, document and exercise the app

Ownership: controller operates connected tools and local runtime; docs/README.md
and skills/evaluate-ticker/SKILL.md workflow instructions may be updated here.

- [x] Resolve exact US option roots for all tickers. Collect underlying price and
  parameters, then three standard expirations in eight weeks and bounded near-spot
  option quotes. Record raw JSON plus each retrieval timestamp in ignored data/.
- [x] Import each through the new CLI with the same Settings database/state paths
  used by the app. Check latest API ticker, provenance, option count and notes.
- [x] Document capture/import/reload workflow, portability, limitations and exact
  skill narrow-workflow boundary; no claim of complete research synthesis.
- [x] Start local API/dashboard, exercise ticker and strategy flows; run full
  applicable tests/checks once after integration and obtain final branch review.
- [x] Record results and remaining constraints; leave the user the dashboard URL.
