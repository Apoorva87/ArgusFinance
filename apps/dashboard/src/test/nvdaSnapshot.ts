// Captured verbatim from GET /api/market/NVDA/latest.
// Decimal values keep the storage scale the API actually serves, so the
// dashboard tests exercise the same text a browser receives.
export const nvdaSnapshot = {
  snapshot_id: "00000000-0000-0000-0000-000000000001",
  underlying: {
    ticker: "NVDA",
    price: "180.2500000000",
    source: "mock",
    source_timestamp: "2026-08-28T20:00:00Z",
    retrieved_at: "2026-08-28T20:00:00Z",
    status: "FROZEN",
  },
  options: [
    { ticker: "NVDA", expiration: "2026-09-18", strike: "175.0000000000", option_type: "CALL", bid: "8.6000000000", ask: "8.8000000000", volume: 1200, open_interest: 8500, implied_volatility: "0.440000000000", delta: "0.640000000000", gamma: "0.012000000000", theta: "-0.150000000000", vega: "0.210000000000", source: "mock", source_timestamp: "2026-08-28T20:00:00Z", retrieved_at: "2026-08-28T20:00:00Z", status: "FROZEN" },
    { ticker: "NVDA", expiration: "2026-09-18", strike: "175.0000000000", option_type: "PUT", bid: "3.1500000000", ask: "3.3000000000", volume: 780, open_interest: 6100, implied_volatility: "0.450000000000", delta: "-0.360000000000", gamma: "0.012000000000", theta: "-0.130000000000", vega: "0.200000000000", source: "mock", source_timestamp: "2026-08-28T20:00:00Z", retrieved_at: "2026-08-28T20:00:00Z", status: "FROZEN" },
    { ticker: "NVDA", expiration: "2026-09-18", strike: "185.0000000000", option_type: "CALL", bid: "3.7500000000", ask: "3.9000000000", volume: 960, open_interest: 7200, implied_volatility: "0.460000000000", delta: "0.420000000000", gamma: "0.013000000000", theta: "-0.140000000000", vega: "0.220000000000", source: "mock", source_timestamp: "2026-08-28T20:00:00Z", retrieved_at: "2026-08-28T20:00:00Z", status: "FROZEN" },
    { ticker: "NVDA", expiration: "2026-09-18", strike: "185.0000000000", option_type: "PUT", bid: "7.7500000000", ask: "7.9500000000", volume: 650, open_interest: 5900, implied_volatility: "0.470000000000", delta: "-0.580000000000", gamma: "0.013000000000", theta: "-0.160000000000", vega: "0.210000000000", source: "mock", source_timestamp: "2026-08-28T20:00:00Z", retrieved_at: "2026-08-28T20:00:00Z", status: "FROZEN" },
    { ticker: "NVDA", expiration: "2026-10-16", strike: "175.0000000000", option_type: "CALL", bid: "11.2000000000", ask: "11.4500000000", volume: 540, open_interest: 4300, implied_volatility: "0.455000000000", delta: "0.630000000000", gamma: "0.009000000000", theta: "-0.110000000000", vega: "0.320000000000", source: "mock", source_timestamp: "2026-08-28T20:00:00Z", retrieved_at: "2026-08-28T20:00:00Z", status: "FROZEN" },
    { ticker: "NVDA", expiration: "2026-10-16", strike: "175.0000000000", option_type: "PUT", bid: "5.7000000000", ask: "5.9500000000", volume: 430, open_interest: 3900, implied_volatility: "0.465000000000", delta: "-0.370000000000", gamma: "0.009000000000", theta: "-0.100000000000", vega: "0.310000000000", source: "mock", source_timestamp: "2026-08-28T20:00:00Z", retrieved_at: "2026-08-28T20:00:00Z", status: "FROZEN" },
    { ticker: "NVDA", expiration: "2026-10-16", strike: "185.0000000000", option_type: "CALL", bid: "6.1000000000", ask: "6.3500000000", volume: 480, open_interest: 4100, implied_volatility: "0.475000000000", delta: "0.450000000000", gamma: "0.010000000000", theta: "-0.120000000000", vega: "0.330000000000", source: "mock", source_timestamp: "2026-08-28T20:00:00Z", retrieved_at: "2026-08-28T20:00:00Z", status: "FROZEN" },
    { ticker: "NVDA", expiration: "2026-10-16", strike: "185.0000000000", option_type: "PUT", bid: "9.9500000000", ask: "10.2000000000", volume: 390, open_interest: 3600, implied_volatility: "0.485000000000", delta: "-0.550000000000", gamma: "0.010000000000", theta: "-0.130000000000", vega: "0.320000000000", source: "mock", source_timestamp: "2026-08-28T20:00:00Z", retrieved_at: "2026-08-28T20:00:00Z", status: "FROZEN" },
  ],
  created_at: "2026-08-28T20:00:00Z",
} as const;
