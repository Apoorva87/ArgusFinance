# Phase 2 start: snapshot-backed Strategy Lab

This implements the first useful part of Phase 2 of the approved architecture.
The user authorized repo improvements and starting missing Phase 2 on 2026-09-07.
It does not claim completion of all Phase 2 requirements.

## Product decision

Build one local workflow: capture/open NVDA evidence, select up to four option
legs from one expiration, inspect deterministic expiration payoff and quoted
Greeks, save the exact evaluation with thesis and review boundaries, then reopen
it after restart. Keep the existing market explorer available. WATCH, PAPER,
REAL_MANUAL, and SHADOW are record labels only, with no fill or order simulation.

## Reuse decision

Use existing Decimal/Pydantic value objects, SQLAlchemy/Alembic storage, FastAPI,
Typer/MCP interfaces and Plotly charts. Exact expiration payoff is the sum of
contract intrinsic values less premiums/fees; it needs no stochastic model or
new quantitative dependency. No library is adopted to reproduce this arithmetic.
Quoted Greeks are aggregated from snapshot data, not repriced or fabricated.
Pre-expiration price/time/IV surfaces and calendars are deferred until a pricing
adapter with tested dividend/American-exercise assumptions is selected. Adding a
large backtesting platform for this slice would increase maintenance without
enabling this workflow. No services, queues, orchestration frameworks, new roles,
or always-running agents are added.

## Contracts

StrategyDraft: snapshot_id UUID; name (nonblank, <=120 chars); status enum
WATCH/PAPER/REAL_MANUAL/SHADOW; thesis <=4000 chars; pricing NATURAL/MIDPOINT;
fee_per_contract finite nonnegative Decimal default 0; legs (1..4) with
expiration date, positive finite strike, CALL/PUT, BUY/SELL, quantity integer
1..100; boundaries (0..10) with kind PRICE_BELOW/PRICE_ABOVE/REVIEW_DATE, value
(positive finite decimal string or ISO date), and nonblank note <=500 chars.
All option contracts must exist in the selected stored snapshot and share one
expiration. Duplicate contract+side rows and netting the same contract both ways
are rejected. Evaluate against snapshot time, with real current staleness shown
as a warning; mock/frozen evidence is always identified as hypothetical.

StrategyEvaluation: snapshot id; ticker; expiration; spot; pricing label;
resolved legs with entry premium; net_debit in dollars (credit negative);
entry_fees in dollars; maximum_profit/maximum_loss (positive dollar magnitudes,
null only for unbounded); breakevens; payoff_points of spot and pnl; net_greeks
(delta/gamma/theta/vega, each nullable if any required input is missing);
warnings; eligible bool; analytics_version; source timestamp/status; boundaries.
One standard equity option contract is explicitly 100 shares. No adjusted
contracts supported. NATURAL prices BUY at ask and SELL at bid; MIDPOINT is an
explicit hypothetical choice. Fees charged once per contract at entry.
Portfolio Greeks are share-scaled signed sums; source units preserved.

Exact extrema and breakevens come from piecewise-linear payoff on spot>=0,
all strikes, and the asymptotic call slope, never from the plotted grid alone.
Include zero, strikes, breakevens and spot in the plot grid; graph bounds do not
imply finite tail risk. Avoid JSON Infinity/NaN. Validate finite inputs. Missing
Greeks remain null and display unavailable. Reject mixed expirations, unknown
contracts, expired-at-snapshot contracts, negative fees and empty selections.
Eligibility is structural/data admissibility, never an investment ranking.

SavedStrategy: id, created_at UTC, draft, immutable entry evaluation. Keep
strategy document, creation event and evaluation atomically in SQLite with an
Alembic migration, not Base.create_all. List/get survive fresh containers and
provide exact snapshot provenance. Store entry evaluation rather than silently
recomputing against latest data when opened. A 'review' in this slice means
reopening saved evidence and reviewing the recorded boundaries; active trigger
monitoring, adjustments, fills and entry/current comparison remain Phase 3.

API: POST /api/strategies/evaluate (draft -> evaluation);
POST /api/strategies (draft -> saved strategy, 201);
GET /api/strategies (saved strategy list, newest first);
GET /api/strategies/{id} (saved strategy or 404).
CLI strategy evaluate/save <json-file>, list, get <uuid> and additive MCP tools
evaluate_strategy/save_strategy/list_strategies/get_strategy use the same service.
Validation errors use 422; absent snapshots/strategies 404; CLI errors are concise.

## UI

Keep the existing dark market-workbench palette. Use a large payoff plot as the
central object, a compact editable leg table beside it, and a quiet lower panel
for thesis and boundaries. Left aligned text, tabular numbers, cyan for profit,
muted red for loss, amber for frozen evidence. Navigation: Market, Strategy Lab,
Saved Strategies. A missing snapshot offers an explicit 'Load demo snapshot'
action, labeled deterministic data, using the existing capture endpoint.
Disable save until the displayed evaluation matches the current inputs; protect
against stale async responses. Show empty, loading, failure and success states.
Saved details display original entry evaluation and timestamp, thesis, boundaries,
and status. No empty placeholder tabs. Responsive layout and keyboard labels.

## Scope and acceptance

Use the packaged NVDA canonical fixture in tests. The natural bull call vertical
(buy 175 call ask 8.80, sell 185 call bid 3.75) has net debit $505, maximum loss
$505, maximum profit $495 and breakeven $180.05 before fees. Correctly distinguish
unbounded long-call profit and naked short-call loss. Test fees, quantities,
missing Greeks, invalid selections and restart persistence. Integration tests
prove API/CLI/MCP see the same saved ID and evaluation. Browser smoke should load
demo, evaluate the spread, save, and reopen. Document remaining Phase 2 work:
pre-expiration surfaces, model Greeks, calendars, richer eligibility/evidence.
