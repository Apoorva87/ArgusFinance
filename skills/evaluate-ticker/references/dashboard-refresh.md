# Refresh the local ArgusFinance dashboard

This is a snapshot operation, not full analytical research. The dashboard reads
saved backend state. Its Reload saved data action does not contact IBKR.

## Prerequisites

Work from the checkout containing the current dashboard and import command.
Use `make install` and `make migrate` on a new machine. CLI, API and MCP must
use the same `ARGUS_DATABASE_URL` and `ARGUS_STATE_DIR` (including `.env`).
The connected IBKR tools must be available to the agent. They are not exposed
as an HTTP service the local app can call. If unavailable, report that capture
is unavailable and offer existing saved evidence with its original timestamps.

The seven dashboard tickers are NVDA, AAPL, MSFT, AMZN, GOOGL, META and TSLA.
Resolve APPL to AAPL when the user means Apple.

## Collect source evidence

1. Call IBKR `search_contracts` for each ticker. Select the exact symbol, US
   primary listing, with STK and OPT sections. Never use a similarly named ETF
   or an adjusted/leveraged root. Use the returned underlying contract identifier
   internally; do not display broker contract identifiers to the user.
2. Call `get_price_snapshot` for the underlying (`last`, `bid_ask`, `top_status`)
   and `get_option_parameters`. Preserve each response and actual retrieval time.
   A usable underlying requires a positive last price and its source `last.ts`.
3. Select three standard-root expirations within approximately eight
   weeks: first regular monthly (`regular: true`), first available at least four weeks out, and
   last available inside eight weeks. If fewer exist, collect those and disclose
   the count. Exclude trading classes other than the exact root. Pass expiration
   IDs verbatim, never reconstruct them or disambiguate by date alone. Deduplicate
   the three choices by ID; if choices coincide, disclose the smaller sample.
   The bundle's `expiration` is the returned calendar `date`, reformatted from
   YYYYMMDD to YYYY-MM-DD; it is distinct from the opaque expiration ID used in
   tool calls.
4. Call `get_option_data` for each selected expiry, bounding the strike search
   around the fetched spot with room for five strikes on either side (start with
   ±15%; widen if necessary). Confirm USD currency and SMART exchange. From the
   returned contracts select up to three strikes on either side of spot. Collect
   both calls and puts with `get_price_snapshot`, requesting `bid_ask`,
   `top_status`, `volume`, `option_open_interest`, `option_midpoint_iv`.
   This samples at most 36 contracts per ticker; it is not the complete chain.
5. Save raw responses and retrieval timestamps in ignored `data/connector-captures/`.
   Retain contract search results, expiration parameters and chain responses
   alongside quote bundles to audit root, trading class, currency and contract IDs.
   Record failed calls explicitly. Raw response keys are hyphenated. Retain raw
   numbers and statuses; the adapter validates, normalizes storage precision and
   preserves unavailable fields. Do not substitute last-trade timestamps for
   bid/ask timestamps. Do not infer IV units or derive Greeks.

## Import and display

For each ticker, write this raw bundle (response objects are the actual tool
payloads, not MCP text wrappers). Include only successfully fetched option rows;
record failures and exact sampled expiry/strike coverage in notes.

```json
{
  "schema_version": 1,
  "ticker": "NVDA",
  "underlying": {"response": {}, "retrieved_at": "2026-09-09T06:00:00Z"},
  "options": [
    {"expiration": "2026-09-18", "strike": "225", "option_type": "CALL",
     "response": {}, "retrieved_at": "2026-09-09T06:01:00Z"}
  ],
  "notes": ["Sampled standard USD equity options; not the complete chain."]
}
```

The dates above show the format; always use actual collected identities and times.
An empty response in the template is invalid and must be replaced by evidence.

```bash
uv run argusfinance market import-ibkr data/connector-captures/NVDA.json
uv run argusfinance market latest NVDA
make dev
```

The first command validates and persists one immutable snapshot through the shared
service. Save its returned snapshot ID. Subsequent refreshes create new snapshots;
existing saved strategy entry evidence remains unchanged. Alternatively, a caller
with an already normalized MarketSnapshot can use MCP `import_market_snapshot`
or HTTP `POST /api/market/import` with that normalized object.

Open the dashboard URL printed by `make dev`, select each ticker, and use Reload
saved data if it is already open. Confirm the ticker, snapshot ID, timestamp,
notes and status match the imported data. Disclose frozen/delayed option quotes,
missing fields and sampling. If capture or import fails, keep previously saved
evidence visible with its age and report the failure; never fabricate a replacement.

End with the local URL, tickers available, snapshot coverage and data limitations.
For a full evaluation, return to the skill's full research workflow and run all
required evidence lanes, strategy analyst and risk critic in the specified order.
