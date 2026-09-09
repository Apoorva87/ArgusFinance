# Seven-stock ArgusFinance dashboard

User requested the installed ArgusFinance workflow for NVDA, AAPL, MSFT, AMZN,
GOOGL, META, and TSLA and selected extension of the ArgusFinance dashboard.
This slice implements that request within the approved local-first architecture.

## Workflow

The existing Market and Strategy Lab views gain a seven-ticker selector and a
reload-saved-data action. Changing ticker resets draft state and aborts stale
requests. Saved Strategies remains available independently of market availability.
NVDA demo capture remains explicitly labeled and is offered only for missing NVDA.
Real imported evidence is never replaced by an automatic demo capture.

The connected IBKR tools collect underlying quotes, standard USD equity option
contracts and individual quotes. Codex saves the raw responses and retrieval
times locally, then imports them using a validated backend operation. The web
app reads the same SQLite/Parquet state as CLI and MCP. This is a snapshot
workflow: it does not claim streaming data or direct browser-to-connector access.
Repeated capture/import through the skill supplies subsequent refreshes.

## Evidence and missing data

Current connector evidence proves option IV may be invalid and option quote
source timestamps absent. Option source_timestamp, volume, open_interest and
implied_volatility therefore support null, preserved through Parquet and JSON.
Underlying source_timestamp remains required, from the underlying last-price ts.
Never substitute retrieval time or last-trade time for a missing bid/ask timestamp.
Recognize FROZEN_DELAYED explicitly. Greeks remain null unless supplied.
Snapshot notes disclose sampled coverage, skipped invalid quotes and missing data.
Old snapshots without notes load with an empty tuple. UI displays missing values
and option freshness even if the underlying status is REALTIME.

Raw connector bundle v1:
```json
{"schema_version":1,"ticker":"NVDA","underlying":{"response":{},"retrieved_at":"ISO UTC"},"options":[{"expiration":"YYYY-MM-DD","strike":"225","option_type":"CALL","response":{},"retrieved_at":"ISO UTC"}],"notes":["Sampled standard USD equity options; not the complete chain."]}
```
The caller resolves an exact US equity root with OPT, excludes adjusted trading
classes, and validates USD currency/SMART exchange before collecting option rows.
Raw data stays in ignored data/connector-captures. A reusable normalizer converts
bundles to immutable MarketSnapshot instances. Reject malformed underlying price,
timestamp, status or ticker; skip option rows with missing/invalid/crossed quotes,
report the skipped count, and reject a result with no usable contracts. Invalid
IV sentinel values become null, never zero. OI uses the correct call/put field.
Finite/nonnegative constraints apply to optional market fields.

## Shared interfaces

MarketService.import_snapshot(snapshot: MarketSnapshot) -> MarketSnapshot shares
the existing locked publication path with capture. CLI market import-ibkr <file>
normalizes a bundle and persists it. MCP import_market_snapshot accepts a normalized
snapshot object; HTTP POST /api/market/import does likewise. UUID conflicts remain
immutable and return an explicit input error at boundaries. Existing evaluation
requires quoted bid/ask but does not require IV or OI; missing timestamp and data
status generate warnings. Same-day option expiry is allowed, earlier dates rejected.

## Delivery and acceptance

No new runtime dependencies. No undocumented provider endpoints. No automatic
orders or external publication. Use the existing feature worktree. Preserve all
existing fixtures, saved evaluations and role definitions.

Populate all seven tickers using actual connector results, selecting three
standard expirations inside approximately eight weeks and a bounded set of
near-spot strikes (both calls and puts), with exact coverage described in notes.
If a ticker cannot be captured, show the real failure; never synthesize prices.
Verify nullable fields round-trip, shared import boundaries, ticker races, and
truthful chart missing-data presentation. Run Python and dashboard checks, inspect
the running app if a browser is available, then leave a usable local dashboard URL.

Full company/historical/strategy/risk agent synthesis is separate from this narrow
capture-and-display operation; do not claim those research lanes have run.
