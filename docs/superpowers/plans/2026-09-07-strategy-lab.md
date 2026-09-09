# Strategy Lab Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Start Phase 2 with a working local evaluate/save/reopen option-strategy workflow and fix verified prerequisite defects.

**Architecture:** Extend the existing modular Python backend and React app. All interfaces use one strategy service and SQLite-backed saved evaluations. Backend owns every numerical series.

**Tech Stack:** Existing Pydantic, Decimal, SQLAlchemy/Alembic, FastAPI, Typer/MCP, React and Plotly.

**Spec:** docs/superpowers/specs/2026-09-07-strategy-lab-design.md

## Global Constraints

- Local-first, single-user; no order actions or new agent roles.
- Every leg references a stored snapshot contract; one expiration, 100-share multiplier.
- Quote provenance, frozen/mock warnings and missing Greeks remain visible.
- SQLite changes through Alembic only; saved evaluation/events immutable and atomic.
- Charts use backend series; no frontend numerical analytics duplication.
- Start of Phase 2 only: model repricing/time-IV surfaces and active monitoring remain deferred.
- Do not modify global skills/configuration. Preserve concurrent work; no worker spawns agents.

### Task 2: Strategy backend and deterministic analytics

**Files:** create `src/argusfinance/domain/strategy.py`, `src/argusfinance/services/strategies.py`, `src/argusfinance/analytics/__init__.py`, `src/argusfinance/analytics/payoff.py`, `src/argusfinance/storage/strategies.py`, `src/argusfinance/api/routes/strategies.py`, next Alembic revision, focused tests under domain/services/api/storage plus `tests/test_strategy_interfaces.py`. Modify bootstrap, API app/dependencies, CLI/MCP, storage models and affected test registration expectations only as required.

**Interfaces:** Implement exact domain/API contracts in the linked spec. Service `evaluate(draft)`, `save(draft)`, `list()`, `get(uuid)`. Share via `Container.strategy_service`. New `StrategyMcpTools` and CLI `strategy` group; preserve existing market tools.

- [x] Write real golden tests before implementation. Use exact fixture quotes. Sample assertion:

```python
assert evaluation.net_debit == Decimal('505')
assert evaluation.maximum_loss == Decimal('505')
assert evaluation.maximum_profit == Decimal('495')
assert evaluation.breakevens == [Decimal('180.05')]
```

- [x] Run focused pytest to record genuine missing-feature RED, then implement typed validation and piecewise payoff with finite inputs and explicit unlimited tails. Test quantity scaling, commissions, put/call long/short, missing Greek propagation, no break-even/zero flat intervals, contract selection errors, mixed expiry rejection. Any plateau of zero P&L needs explicit representation or warning, not a made-up isolated root.
- [x] Add migration and transactional save repository; test downgrade/upgrade without losing snapshot metadata and fresh-container reads. Test API validation/not-found, one stored evaluation plus creation event, and CLI/MCP saved ID agreement. Use migrated temporary databases.
- [x] Add an explicit read-by-ID market service method if needed; no reaching into other service private attributes. Keep existing fake containers/interfaces compatible in tests by constructing real services or narrowing registration assertions appropriately.
- [x] Run focused checks, full Python suite, `.venv/bin/ruff check src tests scripts migrations`, `.venv/bin/mypy src/argusfinance`, diff check; commit `feat: add snapshot-backed strategy evaluation and persistence`.

### Task 3: Strategy Lab and saved-strategy UI

**Files:** create `apps/dashboard/src/api/strategies.ts`, feature files under `features/strategies/`, corresponding tests; modify `App.tsx`, `App.test.tsx`, styles and market API helper if needed. Update README with actual delivered/deferred scope and quick workflow.

**Interfaces:** Consume Task 2 HTTP types exactly. Import canonical snapshot fixture; mock network boundaries only. Use existing plot dependency; no new browser/global tools or dependencies.

- [x] Read the design and Task 2 report/OpenAPI types. Test nav, selecting same-expiration fixture legs, evaluation loading/errors, returned risk/provenance, saving, list/get and re-opening original evidence. Sample flow expectation:

```typescript
expect(await screen.findByText('Maximum loss')).toBeInTheDocument();
expect(screen.getByRole('button', { name: 'Save strategy' })).toBeEnabled();
```

- [x] Implement leg selection (BUY/SELL, quantity, strike, CALL/PUT, shared expiry), pricing choice and fee input. Default to NVDA 175/185 bull call vertical only when matching contracts exist. Changing inputs invalidates prior evaluation and disables save until reevaluated; guard stale responses. Use exact response numerical values and warning strings.
- [x] Plot payoff, break-even/spot/price boundary annotations and a text scenario table. Display unlimited tail risk accurately. Show Greek units and missing values. Add thesis/status/boundary controls. Saved list/detail preserves original evaluation and source timestamp; graceful empty state and error recovery.
- [x] Add explicit demo capture action in missing-market state and preserve current market explorer behavior. Avoid placeholder pages and unrelated visual redesign. Accessible labels, keyboard focus, mobile usable.
- [x] Verify focused then full Vitest and build; update README and commit `feat: add visual strategy lab and saved evaluations`.

### Task 1: Audit fixes (execute before Tasks 2 and 3)

**Files:** `src/argusfinance/domain/market.py`, `src/argusfinance/storage/snapshots.py`, `src/argusfinance/services/market.py`, `migrations/env.py`, relevant tests and `docs/reviews/2026-09-07-repo-review.md`; amend README if a fix changes documented behavior.

**Interfaces:** Preserve market/strategy semantics and migration ownership; fix issues with demonstrated impact rather than speculative redesign.

- [x] Reproduce concurrent conflicting and identical snapshot writes. Serialize read-check-publish and capture metadata/compensation for a UUID with a cross-process lock scoped under local snapshot root (stdlib advisory locks on the supported macOS/Linux platform are acceptable). Use unique temporary files; never replace different immutable contents. A regression must exercise separate processes or separate store/service instances. No distributed service or new lock dependency.
- [x] Reject empty options, options for a ticker different from underlying, and duplicate normalized `(ticker, expiration, strike, option_type)` identities at normal Pydantic validation. Preserve canonical ordering and null Greeks.
- [x] Make Alembic resolve the same `.env`/environment database settings as runtime while preserving explicit programmatic URL overrides in tests. Test actual upgrades to a temporary `.env`-only URL and to an explicitly injected URL. No secret configuration in logs.
- [x] Record RED/GREEN per concern. Run full Python, Ruff/mypy and existing frontend baseline if relevant. Record what exists, fixed defects, proposed product cuts and remaining Phase 2 scope in review summary. Commit `fix: harden local research workflow`.

## Completion

Every task has a scoped independent review; final integration review covers the branch once. Reports/briefs live in this plan's ignored SDD workspace. Retain useful checked-in review summary and exact test evidence. No claim of completed Phase 2: this milestone is the expiration-payoff and persistence slice.


## Delivery evidence — 2026-09-08

- Task 1 prerequisite audit: `73c274d`; independent scoped review approved.
- Task 2 backend: `7460402`; independent review and fix re-review approved.
  Expired-at-snapshot contracts are rejected; frozen/mock/stale warnings include
  the underlying and selected options. Hand-checked payoff cases, invalid-input
  API responses, transaction rollback, migration round-trip, and CLI/MCP shared
  saved-record identity are covered.
- Task 3 UI: checkpoint `d504099`, completed by `ddea23e`; independent scoped
  review approved. The editor and saved-detail views use backend evaluation
  values and preserve original evidence. Fixed-scale contract selection and
  stale saved-detail responses have regressions.
- Portable agent installation: `9bd7d3b` and `37f45c0` integrate the previously
  separate install work. The six role paths now resolve from the declaring
  config directory; install and quality checks validate portable mappings.
- Integrated Python verification: **127 tests passed**; Ruff passed; strict mypy
  passed for 32 source files. Agent install succeeded, including 14 focused
  roster tests; actual Codex diagnostics reported no startup warnings.
- Dashboard verification: **39 tests passed** in eight files; TypeScript and
  Vite production build passed. Vite retains the existing Plotly bundle-size
  warning (approximately 4.34 MB minified / 1.32 MB gzip).
- Final independent branch review of `28ee8f3..ddea23e`: no Important or
  Critical findings; ready to integrate this scoped milestone. Browser visual
  acceptance remains unverified, as disclosed below.
- Real local HTTP capture/evaluate/save/list/get passed through the API and Vite
  proxy. The original saved evaluation, thesis, and boundaries survived an API
  restart against an isolated local database.
- Browser discovery and retry reported no available browser. Visual browser
  smoke is outstanding, including inspection of potentially clipped rotated
  chart annotations. Accessible text retains the corresponding values. CSS,
  interaction tests, and the build were checked; screenshot QA is not claimed.

This completes the implemented expiration-payoff and persistence slice, with
visual acceptance still outstanding. It does not complete all Phase 2:
pre-expiration models/time-IV surfaces, calendars, richer eligibility/evidence,
live capture, active monitoring, fills, and order actions remain deferred.
