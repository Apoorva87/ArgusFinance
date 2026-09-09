# Seven-stock dashboard delivery evidence

## Scope

Extend the existing ArgusFinance Market/Strategy Lab with NVDA, AAPL, MSFT,
AMZN, GOOGL, META and TSLA. Read-only connected IBKR snapshot collection feeds
the shared local backend. This is capture and display, not a completed
company/historical/strategy/risk research evaluation or streaming quote service.

## Captured evidence

On September 9, 2026 UTC (September 8 Pacific), exact US equity roots and
standard-root SMART/USD options were resolved with the connected IBKR tools.
Three expirations were requested: September 18, October 9 and October 23, 2026.
Each requested expiry sampled up to three strikes on either side of underlying
spot, both calls and puts. Selected contract-search records, raw parameter/chain/
quote responses and retrieval times are retained locally in ignored
`data/connector-captures/2026-09-09/`.

All 252 individual option quote calls eventually returned (one transient failure
was retried). Validation omitted 27 unusable bid/ask pairs. Each omission count
is attached to the imported snapshot; no quotes were fabricated.

| Stock | Usable option quotes | Expirations with usable quotes |
| --- | ---: | --- |
| NVDA | 36 | September 18, October 9, October 23 |
| AAPL | 29 | September 18, October 9, October 23 |
| MSFT | 24 | October 9, October 23 |
| AMZN | 36 | September 18, October 9, October 23 |
| GOOGL | 28 | September 18, October 9, October 23 |
| META | 36 | September 18, October 9, October 23 |
| TSLA | 36 | September 18, October 9, October 23 |

All retained options report `FROZEN_DELAYED`. Their bid/ask source timestamps
and Greeks were absent. IV is not imported because its units are not documented
by the connected tool. Underlying source timestamps and reported REALTIME status
are preserved separately; that label does not imply fresh option prices.

## Shared-service verification

The CLI imported all seven bundles into the default local database. Actual HTTP
checks through the API on port 8765 and Vite proxy on port 5173 matched each
normalized snapshot exactly. For a selected long call per ticker, checks verified
maximum loss equals quoted ask times 100, unlimited maximum profit, null net
Greeks and missing timestamp/frozen-delayed warnings. These checks evaluate only;
they did not create saved strategy records.

Backend verification at `9b281ec`: 151 Python tests pass, Ruff passes across
source/tests/scripts/migrations, and strict type checking passes for 33 files.
Task review found one Greek precision issue; its focused regression passed and
the scoped re-review confirmed it addressed, with no new important findings.

## Reusable workflow and design rulings

- Use the connected tools plus reusable importer, retaining the local-first
  architecture. Refresh through the skill, then reload saved data in the dashboard.
  The browser cannot invoke the chat connector directly.
- Preserve unavailable fields as null. Do not guess IV units. Monetary source
  artifacts round half-even to ten fractional digits; quoted Greeks use twelve.
- Preserve raw lookup and quote evidence, including skipped rows. Report sampled
  coverage rather than imply a complete chain.
- The explicit dashboard-refresh mode is a documented narrow workflow. Full
  evaluation/recommendation requests still require all five analytical roles.

Skill verification used a read-only baseline probe: the old instructions lacked
the seven-stock capture/import path. The updated reference passed the same probe;
expiry deduplication, regular-monthly identification, opaque IDs versus calendar
dates, and retained lookup evidence were also checked. The existing 14 agent-roster
tests pass with the updated skill.

## Visual verification

The primary browser runtime reported no connected browser, but the standalone
Playwright test browser successfully reached the local app. Initial checks rendered
the actual NVDA Market snapshot and evaluated its default Strategy Lab draft.
Viewport screenshots exposed clipped payoff labels, a truncated expiration date,
a mobile sticky-header collision and overlapping nearby payoff markers. The
frontend fixes passed a second browser inspection at 1440px and 390px widths.
Neither viewport has document horizontal overflow. The marker labels now wrap
outside the plot; their exact price lines remain in the chart.

All seven ticker buttons displayed the matching imported snapshot and available
expirations. Switching tickers reset the Strategy Lab draft, AAPL evaluation
rendered the payoff and evidence warnings, and Reload saved data loaded the
persisted AAPL snapshot successfully. Browser tests did not save strategies.
Fresh navigation reported zero console errors or warnings. The isolated test tab
was closed, leaving the original dashboard tab and local development server open.

The full frontend suite passed 48 tests across nine files at `ad6ad57`. Following
review and visual fixes, all 29 affected tests across four files and the production
build passed at `f044ab9`. Vite retains the existing Plotly chunk-size warning;
no dependencies were added.

## Design decisions and tradeoffs

1. The user's request to use ArgusFinance authorized the required ticker UI and
   import workflow. This adds a reusable capability to the existing app.
2. Connected IBKR tools collect snapshots, and a shared importer publishes them.
   Refresh therefore needs the skill; the browser's reload action reads local
   saved data and does not independently contact IBKR.
3. Undocumented IV units remain unavailable. Prices and optional quoted Greeks
   use the existing storage precision, avoiding float artifacts at the cost of
   rounding beyond ten and twelve fractional places respectively.
4. One sticky header uses its actual content height. Payoff labels wrap in an
   adjacent list, trading inline annotation placement for readable nearby values.
