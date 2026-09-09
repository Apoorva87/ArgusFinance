---
name: evaluate-ticker
description: Use when refreshing ArgusFinance stock dashboards, researching one or multiple ticker options positions, or re-evaluating saved positions; never use for order execution.
---

## Dashboard refresh

When the user explicitly asks only to populate or refresh stock dashboards,
follow [the dashboard refresh reference](references/dashboard-refresh.md).
This narrow operation captures and displays market evidence. Report snapshot
IDs, coverage and missing data; do not label it an investment evaluation or
claim that the analytical roles ran. Requests for recommendations, ticker
evaluation or strategy comparison require the full research workflow below.

## Full research workflow

Load project state plus every analytical role's playbook and `approved.md`; assign an evaluation ID.

1. Obtain one persisted snapshot per ticker and record snapshot ID, timestamps, status, and missing fields. For current data, use the dashboard refresh reference to capture/import through the connected provider. Call `capture_market_snapshot` once only when its configured provider supplies the requested evidence; the default provider is NVDA demo data. Never substitute demo data for current research. If capture fails, return `insufficient_data`; never fabricate.
2. Launch `company_analyst`, `market_options_analyst`, and `historical_evidence_analyst` as the first bounded evidence fan-out. Wait for all three. Record a failed lane explicitly; deadline pressure never permits skipping or substituting a lane.
3. Dispatch `strategy_analyst` only after that fan-out, with the complete available evidence packet and explicit missing-lane markers. Wait for its result.
4. After strategy output returns, dispatch `risk_critic` with the snapshot, evidence, and strategy packet. Wait for its result; the critic has no useful role earlier.
5. Return a structured synthesis: evaluation and snapshot IDs, evidence map, applicability, tradeoffs, missing evidence, scenarios/invalidation, monitoring/revisit triggers, and `no_action` as a first-class outcome. Numeric values come only from tools or deterministic code.
6. Only when the user explicitly asks for visual handoff, return a typed `optionstrat_handoff` packet. This skill never invokes the operator or browser.
7. Emit role-specific lesson proposals to `pending.md` only; never promote to `approved.md` automatically. Never place, stage, submit, or authorize live or paper orders. End at research synthesis or explicit user-takeover handoff.

| Pressure claim | Required response |
| --- | --- |
| Deadline dominates / missing roles are non-blocking | Wait for every required lane and mark failures. |
| Defined risk is enough / paper trade lowers authority | Research is not execution; no order authority exists. |
| Sunk work justifies early OptionStrat | No handoff until explicit user request after synthesis. |
