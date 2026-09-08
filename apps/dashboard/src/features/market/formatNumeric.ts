import type { NumericValue } from "../../api/market";

// The API serves exact decimal text at the scale the Parquet store declares,
// so "180.25" arrives as "180.2500000000". That precision is correct on the
// wire and is trimmed here, at the presentation boundary, rather than upstream.
const priceFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const strikeFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 3,
});

function parsed(value: NumericValue): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const text = value.trim();
  if (text === "") return null;
  const candidate = Number(text);
  return Number.isFinite(candidate) ? candidate : null;
}

function format(value: NumericValue, formatter: Intl.NumberFormat): string {
  const numeric = parsed(value);
  // An unreadable value stays visible as written; the dashboard never infers one.
  return numeric === null ? String(value) : formatter.format(numeric);
}

/** Money for display: two decimals, grouped thousands. */
export function formatPrice(value: NumericValue): string {
  return format(value, priceFormatter);
}

/** Strike for display: insignificant trailing zeros removed. */
export function formatStrike(value: NumericValue): string {
  return format(value, strikeFormatter);
}
