# Task 2 report: seven-ticker dashboard and truthful provenance

## Result

The dashboard now loads saved snapshots for NVDA, AAPL, MSFT, AMZN, GOOGL,
META, and TSLA. An accessible ticker control and ticker-specific reload action
sit below the existing primary navigation. Saved Strategies remains a separate
view and stays available when market evidence is missing.

Ticker changes, reloads, and NVDA demo loading invalidate and abort older work.
Both request identity and selected-ticker guards protect success, missing, and
error paths. The NVDA demo is labeled as demo evidence and is offered only when
NVDA is missing. Strategy Lab is keyed by ticker and snapshot ID, so a draft
cannot carry into different evidence.

## Evidence presentation

The UI contract accepts nullable option source timestamps, volume, open
interest, and implied volatility, plus `FROZEN_DELAYED` and optional snapshot
notes. The market view shows:

- underlying and option status separately;
- underlying source/retrieval time, option retrieval range, snapshot creation
  time, and snapshot age;
- availability counts for bid/ask source time, open interest, volume, implied
  volatility, and Greeks;
- frozen/delayed option warnings even beside a realtime underlying quote;
- the imported coverage/skipped-row notes verbatim, including the actual MSFT
  two-expiry result rather than a three-expiry claim.

Liquidity aggregation excludes missing open interest. A wholly unknown total is
shown as `Unavailable`; a total containing both measured and missing contracts
is explicitly labeled `partial`. Measured zero remains zero.

## Focused usability fixes

The established dark options-workbench palette and typography are preserved.
The ticker control is keyboard focus-visible, horizontally scrollable where
needed, and responsive on narrow screens. Fixed-scale Parquet strike values now
have compact labels while their exact values remain unchanged. The expiration
field has enough width for its full date, payoff marker labels anchor inside the
plot, and a local SVG favicon removes the missing-icon request.

## TDD and verification evidence

Initial dashboard/market RED: 9 failed and 7 passed. The failures covered the
missing seven-ticker control, non-NVDA missing state, stale response rejection,
reload, lab reset, NVDA demo labeling, frozen option disclosure, and partial
open-interest handling.

Focused visual regressions were also observed RED: fixed-scale strike labels and
payoff annotation anchoring each failed before their production changes. The
demo-unmount abort regression failed independently before its cleanup was added.

Targeted GREEN:

- `npm test -- --run src/App.test.tsx src/features/market/MarketSnapshotView.test.tsx src/features/strategies/StrategyLab.test.tsx src/features/strategies/PayoffChart.test.tsx`
  — 28 passed.

Fresh final verification:

- `npm test -- --run` — 48 passed in 9 files.
- `npm run build` — TypeScript and Vite production build passed.
- `git diff --check` — clean.

Vite reports the existing Plotly bundle-size warning during production builds;
this task adds no dependencies and does not increase the app's Plotly surface.

## Scope and runtime notes

Only `apps/dashboard` and this required task report are included in the task
commit. Concurrent README and review-document changes are intentionally left
uncommitted. The controller owns final browser screenshots against the already
running API and dashboard; baseline and live-HMR inspection informed the small
layout fixes above.
