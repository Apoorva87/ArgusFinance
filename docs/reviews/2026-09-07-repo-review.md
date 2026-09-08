# Repository review: Strategy Lab prerequisites

Reviewed 2026-09-07 as the prerequisite audit for the first Phase 2 slice.
This review covers the four verified foundation defects assigned to Task 1; it
is not a claim that Phase 2 is complete.

## Foundation present before this change

- Provider-neutral, immutable Pydantic market quotes and snapshots, including
  Decimal prices, timezone-aware provenance, market-data status, and nullable
  quoted Greeks.
- Partitioned Parquet snapshot persistence with SQLite metadata owned by an
  Alembic migration.
- One shared market service exposed through FastAPI, CLI, MCP, and the local
  React market explorer.
- Deterministic packaged NVDA data, offline replay support, and a read-only IBKR
  diagnostic boundary. There is no broker capture or order authority.

## Verified defects and corrections

1. UUID-addressed Parquet writes performed their existence check and atomic
   replace without a shared lock. Separate processes could race on one fixed
   temporary filename: identical writes raised `FileNotFoundError`, while
   differing writes could bypass the immutability check and replace content.
   Snapshot operations now take a UUID-scoped advisory lock beneath the local
   snapshot root and publish from a unique temporary file. A process-local
   reentrant layer lets nested service/store operations use the same lock safely.
2. Capture checked file existence, wrote Parquet, inserted metadata, and
   compensated failed metadata in separate unlocked steps. One service could
   therefore delete a file after another service had successfully committed
   metadata for it. Capture now holds the same UUID lock through metadata commit,
   duplicate handling, and compensation.
3. `MarketSnapshot` accepted an empty chain, mixed underlying/option tickers,
   and duplicate normalized contract identities. Construction now rejects those
   states and orders admitted options canonically by expiration, strike, and
   type. Nullable Greeks remain unchanged.
4. Runtime settings loaded the environment and `.env`, but Alembic only read a
   process environment variable and ignored `.env`. Alembic now resolves the
   runtime `Settings` value. Programmatic migration callers can mark an injected
   URL explicitly so ambient configuration cannot redirect test migrations.

## Product cuts retained

- Locking remains local filesystem coordination using the standard library;
  there is no distributed lock, queue, service, or new dependency.
- Snapshots represent usable option-chain evidence, so an empty-chain storage
  format is not introduced.
- This prerequisite task adds no strategy analytics, UI, broker capture, fill
  simulation, monitoring, or order action.

## Remaining Phase 2 slice

The next scoped work is the snapshot-backed Strategy Lab: deterministic
expiration payoff and exact extrema/breakevens, quoted-Greek aggregation,
immutable SQLite-backed saved evaluations, shared API/CLI/MCP interfaces, and a
UI that can evaluate, save, and reopen the recorded evidence. Pre-expiration
repricing/time-IV surfaces, model Greeks, calendars, richer eligibility and
evidence, active monitoring, adjustments, fills, and entry/current comparisons
remain deferred beyond this slice.

## Residual constraints

- Advisory locking coordinates cooperating ArgusFinance processes on the same
  macOS/Linux filesystem. It does not claim network-filesystem or hostile-writer
  protection.
- Parquet and SQLite are still separate persistence systems; the per-UUID lock
  and compensation make the current local capture workflow coherent, not a
  general cross-database transaction protocol.

## Recommended priorities and cuts

1. Finish a trustworthy evaluate/save/reopen loop before expanding agent
   orchestration. The existing fixed-role definitions and checked-in playbooks
   are a suitable starting point, but do not yet constitute the analytical
   workflow described in Phase 4. Reusable memory means loading reviewed lessons
   on each invocation, not relying on an immortal agent process. Keep lesson
   promotion explicitly reviewed rather than automatically accumulating advice.
2. Make read-only IBKR snapshot capture the next data milestone. A polished
   analysis of a frozen NVDA fixture is still a demonstration, not a current
   market decision tool. Preserve mock/replay as regression evidence and make
   source, age, permissions, and missing fields visible in the live adapter.
3. Keep expiration payoff distinct from pre-expiration estimates. The former is
   exact intrinsic-value arithmetic; the latter needs an explicit pricing
   adapter and tested exercise/dividend assumptions. Do not label quoted-Greek
   aggregation as a pricing model or structural validity as a recommendation.
4. Defer generalized backtesting, extra services, autonomous agent loops, and
   a clone of OptionStrat. None is necessary to prove this first local workflow.
   Retain OptionStrat as an optional, explicit visual handoff once saved strategy
   inputs and provenance are reliable.
5. Keep saved research records separate from positions. Status labels and
   written review boundaries do not establish fills, current P&L, monitoring,
   or adjustment recommendations. Those need refreshed evidence and the Phase 3
   lifecycle, with explicit comparisons to the immutable entry evaluation.
