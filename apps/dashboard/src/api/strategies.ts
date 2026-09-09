import type { MarketDataStatus, NumericValue } from "./market";

export type StrategyStatus = "WATCH" | "PAPER" | "REAL_MANUAL" | "SHADOW";
export type StrategyPricing = "NATURAL" | "MIDPOINT";
export type OptionType = "CALL" | "PUT";
export type LegSide = "BUY" | "SELL";
export type BoundaryKind = "PRICE_BELOW" | "PRICE_ABOVE" | "REVIEW_DATE";

export interface StrategyLeg {
  expiration: string;
  strike: string;
  option_type: OptionType;
  side: LegSide;
  quantity: number;
}

export interface StrategyBoundary {
  kind: BoundaryKind;
  value: string;
  note: string;
}

export interface StrategyDraft {
  snapshot_id: string;
  name: string;
  status: StrategyStatus;
  thesis: string;
  pricing: StrategyPricing;
  fee_per_contract: string;
  legs: StrategyLeg[];
  boundaries: StrategyBoundary[];
}

export interface ResolvedStrategyLeg extends StrategyLeg {
  entry_premium: string;
  delta: string | null;
  gamma: string | null;
  theta: string | null;
  vega: string | null;
}

export interface StrategyEvaluation {
  snapshot_id: string;
  ticker: string;
  expiration: string;
  spot: string;
  pricing: StrategyPricing;
  legs: ResolvedStrategyLeg[];
  net_debit: string;
  entry_fees: string;
  maximum_profit: string | null;
  maximum_loss: string | null;
  breakevens: string[];
  payoff_points: Array<{ spot: string; pnl: string }>;
  net_greeks: { delta: string | null; gamma: string | null; theta: string | null; vega: string | null };
  warnings: string[];
  eligible: boolean;
  analytics_version: string;
  source_timestamp: string;
  source_status: MarketDataStatus;
  boundaries: StrategyBoundary[];
}

export interface SavedStrategy {
  id: string;
  created_at: string;
  draft: StrategyDraft;
  evaluation: StrategyEvaluation;
}

export class StrategyApiError extends Error {
  constructor(public readonly status: number, public readonly detail: string) {
    super(detail);
    this.name = "StrategyApiError";
  }
}

function errorDetail(payload: unknown): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = payload.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail.flatMap((item) => {
        if (typeof item !== "object" || item === null || !("msg" in item) || typeof item.msg !== "string") return [];
        const location = "loc" in item && Array.isArray(item.loc)
          ? item.loc.filter((part: unknown) => part !== "body").map(String).join(".")
          : "Input";
        return `${location || "Input"}: ${item.msg}`;
      });
      if (messages.length) return messages.join("; ");
    }
  }
  return "The strategy request could not be completed.";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let payload: unknown;
    try { payload = await response.json(); } catch { payload = undefined; }
    throw new StrategyApiError(response.status, errorDetail(payload));
  }
  return (await response.json()) as T;
}

function post<T>(path: string, draft: StrategyDraft, signal?: AbortSignal): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(draft),
    signal,
  });
}

export function evaluateStrategy(draft: StrategyDraft, signal?: AbortSignal): Promise<StrategyEvaluation> {
  return post("/api/strategies/evaluate", draft, signal);
}

export function saveStrategy(draft: StrategyDraft, signal?: AbortSignal): Promise<SavedStrategy> {
  return post("/api/strategies", draft, signal);
}

export function listStrategies(signal?: AbortSignal): Promise<SavedStrategy[]> {
  return request("/api/strategies", { signal });
}

export function getStrategy(id: string, signal?: AbortSignal): Promise<SavedStrategy> {
  return request(`/api/strategies/${encodeURIComponent(id)}`, { signal });
}

export function numeric(value: NumericValue): number {
  return Number(value);
}
