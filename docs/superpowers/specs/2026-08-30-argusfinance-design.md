# ArgusFinance Design Specification

- **Date:** 2026-08-30
- **Status:** Approved architecture baseline
- **Deployment model:** Local-first, single-user
- **Primary orchestration surface:** Codex/ChatGPT plugin and local Codex clients
- **Primary decision surface:** Local React web application
**Brokerage boundary:** Read-only Interactive Brokers integration in V1

## 1. Product intent

ArgusFinance is a local investment research and options decision workbench. It
combines current market and options data, company evidence, saved theses,
strategy history, deterministic analytics, and role-separated AI research into
one auditable workflow.

The central user question is:

> Given current market conditions, company evidence, option structure, known
> events, and prior decisions, which strategies deserve attention, what argues
> against them, and what price, time, volatility, or evidence boundary should
> trigger the next review?

The product supports both discovery and lifecycle management. A user can
explore option structures for one or more tickers, save a watch or paper/manual
position, return later, compare the original and current state, and evaluate
hold, reduce, roll, adjust, or exit alternatives visually.

ArgusFinance is a decision-support system. It does not promise predictive
alpha, autonomously trade, or silently convert recommendations into orders.

## 2. Design principles

1. **Local-first.** Application services, operational state, historical data,
   agent playbooks, and the web UI run on the user's machine.
2. **One shared state.** Codex, MCP tools, CLI commands, scheduled observation,
   and the browser use the same backend and persistence layer.
3. **Deterministic facts, assisted judgment.** Pricing, Greeks, payoffs,
   ranking components, triggers, and state transitions are deterministic. AI
   interprets evidence, handles contradictions, and explains decisions.
4. **Persistent strategy intent.** A strategy is not inferred from a brokerage
   position. It preserves thesis, entry assumptions, risk boundaries, and
   lifecycle even when execution occurs elsewhere.
5. **Visual decisions.** Important conclusions must be inspectable through
   charts, scenario surfaces, boundaries, timelines, and source-linked factors.
6. **Reuse before build.** Mature libraries and referenced projects are
   evaluated before implementing quantitative, ingestion, or simulation code.
7. **Adapters contain dependencies.** External schemas and APIs do not leak
   through the domain model.
8. **Visible uncertainty.** Stale, delayed, incomplete, or contradictory data
   reduces confidence and appears in the UI.
9. **Temporal correctness.** Historical evaluation may use only information
   available at the simulated timestamp.
10. **No hidden self-modification.** Agent lessons are reviewable, versioned,
    and promoted through an explicit process.

## 3. Scope and non-goals

### 3.1 V1 scope

- Local startup and operation on the user's workstation.
- Read-only Interactive Brokers market and option-chain access.
- An approximately eight-week option horizon for the initial market explorer.
- Saved `WATCH`, `PAPER`, `REAL_MANUAL`, `SHADOW`, and `CLOSED` strategies.
- Deterministic payoff, Greek, scenario, eligibility, and trigger calculations.
- Visual candidate comparison and saved-position adjustment analysis.
- Company financial and filing research with source provenance.
- Date-bounded news and event research.
- Fixed-role Codex subagent orchestration with durable playbooks.
- A local MCP server, equivalent CLI commands, and a React dashboard.
- Optional OptionStrat visual handoff through an approved browser session.

### 3.2 Non-goals

- Live or autonomous order placement.
- High-frequency or tick-level infrastructure.
- Reinforcement-learning trading agents.
- A dynamically expanding multi-agent swarm.
- Recreating all of OptionStrat, a broker terminal, or a general-purpose
  financial data platform.
- Treating IBKR positions as the strategy database.
- Treating a single AI-generated score as an explanation.

## 4. Architectural approach

ArgusFinance uses a plugin-driven modular monolith. A Codex/ChatGPT plugin
packages reusable skills and a local MCP server. Those entry points call the
same FastAPI application used by the local web UI and CLI.

```text
ChatGPT Desktop / Codex / supported local agent host
                         |
                  ArgusFinance plugin
                  /                 \
             reusable skills      local MCP tools
                  \                 /
                    FastAPI application
                            |
     +----------------------+----------------------+
     |                      |                      |
 provider adapters    domain services       agent orchestration
     |                      |                      |
 IBKR / SEC / web     analytics / state      fixed role roster
     \______________________|______________________/
                            |
             SQLite + DuckDB/partitioned Parquet
                            |
                   React decision surface
```

The modular monolith keeps deployment and local debugging simple while
preserving clear boundaries. Modules communicate through typed domain
interfaces rather than direct access to another module's provider models.

## 5. Repository boundaries

The target repository structure is:

```text
ArgusFinance/
├── .codex/
│   ├── config.toml
│   └── agents/
├── .codex-plugin/
│   └── plugin.json
├── apps/
│   ├── api/
│   └── dashboard/
├── packages/
│   ├── common/
│   ├── market_data/
│   ├── company_intelligence/
│   ├── strategies/
│   ├── analytics/
│   ├── paper_trading/
│   ├── research/
│   └── evaluation/
├── integrations/
│   ├── ibkr/
│   ├── sec_edgar/
│   ├── options_sim/
│   ├── historical_options/
│   └── web_research/
├── mcp/argusfinance/
├── skills/
├── agents/
├── scripts/
├── tests/
├── docs/
├── data/                 # ignored local runtime data
└── db/                   # ignored local runtime databases
```

Logical modules may begin as Python packages in one workspace. They should not
be split into independent services unless measured operational needs justify
the additional complexity.

## 6. Runtime and persistence

### 6.1 Operational state

SQLite stores:

- strategies, legs, theses, factors, and decision boundaries;
- immutable strategy events and evaluation records;
- paper fills and reconciliation metadata;
- company research freshness and source provenance;
- agent run metadata and reviewed lessons;
- scheduled observation state and trigger events.

Database writes pass through domain repositories and transactions. Agents do
not edit the database directly.

### 6.2 Historical analytical state

Normalized market snapshots are written to partitioned Parquet and queried via
DuckDB. Every datum carries a provider identifier, source timestamp, retrieval
timestamp, and market-data status such as `REALTIME`, `DELAYED`, or `FROZEN`.

Snapshots used by an evaluation are immutable references. Re-running an old
evaluation should be possible against the same evidence packet and analytics
version.

### 6.3 Local processes

The local launcher starts the API, dashboard, MCP server, and optional
observation worker. The observation worker performs cheap deterministic checks;
it does not run a continuous AI swarm. Full AI evaluation occurs on user
request or after a meaningful configured trigger.

## 7. Provider and reuse policy

Downstream code depends on normalized contracts, not provider schemas.

```text
MarketDataProvider
  get_underlying
  get_expirations
  get_option_chain
  get_option_quotes
  get_history
  get_market_status

FundamentalProvider
  get_company_profile
  get_financial_statements
  get_filings
  get_filing_sections
  get_earnings_state
```

Initial adapters target Interactive Brokers for current market/options data and
EdgarTools/SEC EDGAR for filings and structured company financials. A mock
market provider and replay provider are mandatory for deterministic tests and
offline development.

Before implementing a quantitative, simulation, or ingestion subsystem, the
team records a short reuse decision covering capability fit, activity,
licensing, correctness, maintenance risk, and adapter cost. Referenced projects
such as options-sim, optopsy-mcp, OpenBB, LEAN, and other suitable libraries are
used only where they reduce verified custom work. External models remain behind
ArgusFinance-owned interfaces.

Undocumented third-party endpoints are not production dependencies.

## 8. Domain model

### 8.1 Strategy

A `Strategy` records identity and intent independently of broker positions:

```text
id, ticker, name, strategy_type
status: WATCH | PAPER | REAL_MANUAL | SHADOW | CLOSED
thesis_ids, expected_market_behavior, invalidating_conditions
target_holding_period, risk_budget, current_state
created_at, updated_at
```

A `StrategyLeg` records expiration, strike, option type, side, quantity, entry
price, entry Greeks, and entry timestamp. Multi-leg structures are evaluated as
combos where possible.

### 8.2 Thesis and evidence

A `Thesis` is separate from a strategy so company conviction and the quality of
a particular option expression can change independently. `Factor` records are
structured as supporting, opposing, muted, or unavailable, with strength,
confidence, observed/reference values, source, timestamp, explanation, and
horizon applicability.

### 8.3 Events and evaluations

Strategy history is event-sourced. Events such as creation, entry signal,
paper fill, hold, trigger, adjust, roll, partial exit, close, expiration, and
assignment are appended rather than overwritten.

An `Evaluation` references the exact evidence and market snapshots used, the
analytics and prompt versions, the agent runs, recommendation alternatives,
confidence decomposition, and next decision conditions.

### 8.4 Decision boundaries

A typed `DecisionBoundary` can monitor:

- underlying price or expected-move levels;
- profit, loss, or return-on-risk thresholds;
- days to expiration or event proximity;
- IV, skew, spread, or liquidity changes;
- delta, gamma, theta, or vega thresholds;
- thesis invalidators and evidence changes;
- stale, missing, or conflicting data.

Boundaries are both machine-evaluable triggers and visual annotations.

## 9. Fixed agent roster and orchestration

Codex is the primary orchestrator and final synthesizer. The project defines a
fixed roster of six custom roles:

1. `company_analyst` — financials, filings, company evidence, and thesis.
2. `market_options_analyst` — underlying, chain, volatility, liquidity, and
   market regime.
3. `historical_evidence_analyst` — snapshots, replay, comparable history, and
   backtesting evidence.
4. `strategy_analyst` — eligibility, payoff, triggers, scenarios, and candidate
   comparison.
5. `risk_critic` — counter-evidence, data quality, execution risk, and temporal
   correctness.
6. `optionstrat_operator` — scoped browser handoff of an already-defined
   strategy; it performs no independent investment analysis.

A full ticker evaluation uses the five analytical roles. Narrow workflows may
use a documented subset. The browser operator runs only on explicit visual
handoff. No invocation invents additional roles.

Read-heavy research can run in parallel. Writes to shared application state are
serialized through the orchestrator and backend APIs. Every delegated task has
an explicit input contract, output schema, and ownership boundary.

## 10. Durable agent playbooks and learning

Stable behavior comes from project-scoped agent definitions and checked-in
playbooks, not an assumption that an agent process remains alive forever.

```text
agents/<role>/
├── PLAYBOOK.md
├── CHECKLIST.md
├── SOURCES.md
├── lessons/
│   ├── pending.md
│   └── approved.md
└── evals/
```

An agent may append a candidate lesson with evidence from a completed run.
Candidate lessons are not authoritative. Promotion to `approved.md` requires a
human review or a repeatable evaluation showing improvement without regression.
Secrets, transient market facts, and ticker-specific conclusions are not
promoted as general instructions.

The application stores agent run IDs, role/version, inputs, outputs, tool calls,
sources, and evaluation outcome. This supports audit and later playbook tuning.

## 11. Primary eight-week discovery workflow

For one or more tickers, the user invokes a skill or CLI/MCP operation. The
system:

1. Loads saved thesis, strategy, and prior evaluation state.
2. Retrieves the underlying and approximately eight weeks of expirations from
   IBKR.
3. Normalizes quotes, Greeks, volume, open interest, IV, and provider status.
4. Saves a timestamped market snapshot.
5. Refreshes company, filing, event, and recent-news evidence as required.
6. Computes expected move, term structure, skew, liquidity, payoff, Greeks,
   scenario surfaces, eligibility components, and deterministic triggers.
7. Runs the fixed analytical agents over the structured evidence packet.
8. Produces candidate strategies with supporting, opposing, muted, unavailable,
   and change-trigger factors.
9. Saves the immutable evaluation and refreshes the local UI.

Monthly, weekly, earnings-adjacent, and macro-adjacent expirations are visually
distinct. Data freshness and provider status are visible throughout the flow.

## 12. Strategy laboratory and saved-position management

The strategy laboratory supports prebuilt and custom structures. Editing a leg
or assumption recalculates:

- expiration and pre-expiration P&L curves;
- breakevens, maximum profit/loss, and return on risk;
- spot-by-time and spot-by-IV surfaces;
- current and future Greeks;
- expected-move and event overlays;
- liquidity, commission, fee, and fill assumptions;
- decision-boundary and trigger annotations.

A candidate can be saved as `WATCH`, `PAPER`, `REAL_MANUAL`, or `SHADOW`. The
saved record captures the original thesis, entry market state, legs, pricing
assumptions, expected behavior, invalidators, and monitoring boundaries.

When revisiting a position, ArgusFinance compares entry, last-review, and
current state. It then presents `HOLD`, `REDUCE`, `ADD_WITHIN_BOUNDARY`, `ROLL`,
`ADJUST`, and `EXIT` alternatives. Every alternative includes its cost/credit,
risk and Greek change, payoff curve, scenario surfaces, decision conditions,
and strongest counterargument. No alternative is executed automatically.

## 13. Visual decision surface

The local React application contains:

- **Overview:** triggered reviews, actionable candidates, watches, avoids, and
  data-quality failures.
- **Market Explorer:** eight-week expirations, IV term structure, skew, volume,
  open interest, expected moves, and events.
- **Strategy Lab:** interactive legs, assumptions, payoff curves, and scenario
  surfaces.
- **Saved Strategies:** watches, paper/manual positions, shadows, and closed
  history.
- **Strategy Detail:** entry/current comparison, P&L and Greeks, decision map,
  trigger timeline, evidence, and adjustment alternatives.
- **Company Research:** sourced statements, trends, filings, commentary diffs,
  earnings, valuation, peers, news, and thesis history.
- **Research & Evidence:** factor attribution, source links, freshness, and
  changes since the previous review.
- **System/Data:** provider status, snapshot health, latency, storage, versions,
  and visible failures.

Charts render deterministic, stored series rather than model-generated values.
AI explanations reference chart data and evaluation IDs.

## 14. OptionStrat visual handoff

OptionStrat is an optional communication and exploration surface, not a source
of truth. The `optionstrat-handoff` skill loads a typed packet:

```text
ticker, underlying_reference_price, strategy_type
legs[]: expiration, strike, option_type, side, quantity
entry_or_reference_price, evaluation_timestamp
scenario_date, scenario_spot, scenario_iv_change
```

The `optionstrat_operator` uses an explicitly approved browser or Computer Use
session to open OptionStrat, enter the ticker and exact legs, configure relevant
assumptions, verify ticker/expiration/strike/side/quantity, and stop with the
page ready for user takeover.

The operator does not enter credentials, purchase subscriptions, submit broker
orders, save or publicly share a trade without a separate request, or continue
when the configured legs are ambiguous. It records the handoff and any visible
calculation differences. Differences are not silently forced to match because
market timestamps, IV assumptions, commissions, and pricing models can differ.

A dashboard action can prepare the handoff packet and copy the corresponding
Codex command. Browser control remains initiated from an approved local agent
session rather than from the web backend.

## 15. MCP and CLI contracts

MCP tools and CLI commands call the same application services. Representative
operations include:

```text
workspace: get_summary, list_actionable, list_triggered
market: get_state, get_chain, snapshot
company: get_overview, refresh_research, get_factors
strategy: create, get, compare, record_decision, adjust, roll, close
paper: enter, portfolio, create_shadow
quant: scenario_analysis, compare_strategies, backtest
evaluation: evaluate_ticker, evaluate_workspace, get_evaluation
visual: prepare_optionstrat_handoff, refresh_dashboard
```

Tools expose business operations rather than raw IBKR calls. This preserves the
contract if provider libraries change.

## 16. Failure handling and safety

Failures are typed, persisted where relevant, and shown to the user. Examples:

- option data delayed, frozen, or unavailable;
- mixed underlying and option timestamps;
- Greeks unavailable or pricing assumptions invalid;
- market snapshot or historical evidence missing;
- company source stale or research retrieval failed;
- strategy legs do not reconcile with a broker position;
- paper fill model has low confidence;
- historical evidence has uncertain temporality;
- browser handoff cannot verify the configured legs.

Failures reduce confidence. The system never substitutes guessed data silently.
V1 brokerage access is read-only, and all actions remain recommendations or
paper/manual records.

## 17. Testing strategy

### 17.1 Deterministic tests

- Unit tests for payoff, Greeks, expected move, ranking components, triggers,
  state transitions, fees, fills, P&L, and expiration handling.
- Provider contract tests with deterministic fixtures.
- Replay tests using stored Parquet snapshots.
- Look-ahead tests for market, filing, earnings, and news evidence.
- Database transaction and immutable-event tests.

### 17.2 Golden scenarios

- NVDA bull call spread.
- AMD calendar spread.
- TSLA high-IV straddle.
- AAPL expiration-management case.
- Saved-position roll and partial-exit cases.

Each golden scenario verifies numeric outputs, chart-series data, factors,
decision boundaries, and state transitions.

### 17.3 Agent and UI tests

- Schema validation for every agent input and output.
- Recommendation regression tests against stored evidence packets.
- Risk-critic tests requiring explicit counter-evidence.
- Playbook evaluations before lesson promotion.
- Browser-operator tests that verify exact legs and stop safely on UI drift.
- End-to-end UI tests for discovery, save, revisit, compare, and handoff flows.

## 18. Observability

Structured logs carry evaluation, strategy, provider request, agent run, and
snapshot IDs. Metrics include provider latency/failure, data freshness, snapshot
volume, storage growth, trigger activity, LLM/tool usage, analytics version,
prompt/playbook version, evaluation latency, and browser-handoff outcome.

Local logs avoid secrets and sensitive browser/session data.

## 19. Delivery sequence

### Phase 1: Foundation and thin NVDA slice

- Repository, local launcher, FastAPI, React, SQLite, DuckDB/Parquet.
- Typed domain skeleton and database migrations.
- Mock/replay providers and IBKR connection diagnostics.
- Fixed agent definitions, playbook structure, plugin manifest, MCP shell.
- NVDA eight-week snapshot displayed consistently through API, CLI/MCP, and UI.

### Phase 2: Strategy and visual core

- Strategy, leg, thesis, event, evaluation, and boundary persistence.
- Eligibility engine, payoff/Greek calculations, scenario surfaces.
- Strategy Lab, save/revisit workflow, paper/manual states.

### Phase 3: Position lifecycle

- Observation worker, deterministic triggers, entry/current comparison.
- Hold, reduce, roll, adjust, and exit alternative modeling.
- Paper fills, fees, shadow candidates, and performance history.

### Phase 4: Company and research evidence

- EdgarTools integration, financial analytics, filings, earnings, and factors.
- Date-bounded news, event clustering, evidence deltas, and thesis propagation.
- Fixed analytical agent workflow and risk critique.

### Phase 5: Historical evidence and external handoff

- Historical adapter evaluation, replay/backtesting, and comparison panels.
- OptionStrat browser operator, handoff packet, UI action, and drift tests.

### Phase 6: Decision-surface polish

- Multi-ticker workspace review, opportunity ordering, richer comparisons,
  observability, backups, and usability refinement.

Each phase delivers a demonstrable local workflow. Dependencies are adopted only
after a reuse decision and focused adapter test.

## 20. Initial acceptance criteria

The architecture is validated when one NVDA strategy can be evaluated across
multiple refreshed days and:

1. IBKR market/options data is normalized, provenance-tagged, and persisted.
2. The CLI/MCP and browser display the same saved market and strategy state.
3. At least one paper or manual strategy survives restart.
4. The eight-week explorer and Strategy Lab render deterministic visualizations.
5. The strategy can be revisited against current data with explicit hold,
   adjustment, roll, and exit alternatives.
6. Decision boundaries are visible and produce deterministic trigger events.
7. Company and recent-event evidence is sourced and time-bounded.
8. Recommendations expose supporting, opposing, muted, and unavailable factors.
9. The risk critic returns concrete counter-evidence.
10. The user can request an OptionStrat handoff and receive a correctly prepared
    browser page without any order submission.
11. All facts used in a recommendation are reproducible from saved evidence or
    source metadata.
12. No live order is placed.

## 21. Key architectural decisions

- Use a local plugin-driven modular monolith rather than an always-on agent
  platform or a collection of disconnected scripts.
- Keep one authoritative backend and persistence layer for all interfaces.
- Use a fixed five-agent analytical team plus one scoped OptionStrat operator.
- Store durable role guidance in version-controlled playbooks and promote
  lessons explicitly.
- Treat visual scenario and lifecycle management as the primary product loop.
- Use provider and quantitative libraries behind narrow adapters.
- Keep OptionStrat optional and human-facing; do not depend on undocumented
  endpoints or use it as the calculation source of truth.
- Keep V1 brokerage access read-only and require human control over decisions.
