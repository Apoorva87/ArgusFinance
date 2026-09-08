import type { MarketSnapshot } from "../api/market";
import canonicalSnapshot from "../../../../src/argusfinance/adapters/fixtures/nvda_snapshot.json";

// Keep dashboard tests and local UI evidence on the exact backend fixture.
// The type assertion is limited to the JSON boundary; runtime values remain
// untouched, including null Greek values.
export const nvdaSnapshot = canonicalSnapshot as unknown as MarketSnapshot;
