import { describe, expect, it } from "vitest";
import canonicalSnapshot from "../../../../src/argusfinance/adapters/fixtures/nvda_snapshot.json";
import { nvdaSnapshot } from "./nvdaSnapshot";

describe("canonical NVDA dashboard fixture", () => {
  it("uses the packaged backend fixture without manually duplicated values", () => {
    expect(nvdaSnapshot).toEqual(canonicalSnapshot);
  });
});
