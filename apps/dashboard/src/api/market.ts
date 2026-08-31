export type NumericValue = string | number;

export type MarketDataStatus = "REALTIME" | "DELAYED" | "FROZEN" | "UNAVAILABLE";

export interface UnderlyingQuote {
  ticker: string;
  price: NumericValue;
  source: string;
  source_timestamp: string;
  retrieved_at: string;
  status: MarketDataStatus;
}

export interface OptionQuote {
  ticker: string;
  expiration: string;
  strike: NumericValue;
  option_type: "CALL" | "PUT";
  bid: NumericValue;
  ask: NumericValue;
  volume: number;
  open_interest: number;
  implied_volatility: NumericValue;
  delta: NumericValue | null;
  gamma: NumericValue | null;
  theta: NumericValue | null;
  vega: NumericValue | null;
  source: string;
  source_timestamp: string;
  retrieved_at: string;
  status: MarketDataStatus;
}

export interface MarketSnapshot {
  snapshot_id: string;
  underlying: UnderlyingQuote;
  options: readonly OptionQuote[];
  created_at: string;
}

export class MarketApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = "MarketApiError";
  }
}

function errorDetail(payload: unknown): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = payload.detail;
    if (typeof detail === "string") return detail;
  }
  return "The market snapshot could not be loaded.";
}

export async function fetchLatestSnapshot(ticker: string, signal?: AbortSignal): Promise<MarketSnapshot> {
  const response = await fetch(`/api/market/${encodeURIComponent(ticker.trim().toUpperCase())}/latest`, { signal });
  if (!response.ok) {
    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      payload = undefined;
    }
    throw new MarketApiError(response.status, errorDetail(payload));
  }
  return (await response.json()) as MarketSnapshot;
}
