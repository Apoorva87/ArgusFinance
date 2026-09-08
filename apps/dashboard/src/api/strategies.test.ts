import { afterEach, describe, expect, it, vi } from "vitest";
import {
  evaluateStrategy,
  getStrategy,
  listStrategies,
  saveStrategy,
  StrategyApiError,
  type StrategyDraft,
} from "./strategies";

const draft: StrategyDraft = {
  snapshot_id: "00000000-0000-0000-0000-000000000001",
  name: "NVDA 175 / 185 call spread",
  status: "WATCH",
  thesis: "Defined-risk upside through expiration.",
  pricing: "NATURAL",
  fee_per_contract: "0",
  legs: [
    { expiration: "2026-09-18", strike: "175", option_type: "CALL", side: "BUY", quantity: 1 },
    { expiration: "2026-09-18", strike: "185", option_type: "CALL", side: "SELL", quantity: 1 },
  ],
  boundaries: [],
};

afterEach(() => vi.unstubAllGlobals());

describe("strategy API", () => {
  it("posts the exact draft to evaluation and save endpoints", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ ticker: "NVDA" }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "saved-1" }), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(evaluateStrategy(draft)).resolves.toEqual({ ticker: "NVDA" });
    await expect(saveStrategy(draft)).resolves.toEqual({ id: "saved-1" });

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/strategies/evaluate", expect.objectContaining({
      method: "POST", body: JSON.stringify(draft),
    }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/strategies", expect.objectContaining({
      method: "POST", body: JSON.stringify(draft),
    }));
  });

  it("lists and gets immutable saved evaluations", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([{ id: "saved-1" }]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "saved/1" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(listStrategies()).resolves.toEqual([{ id: "saved-1" }]);
    await expect(getStrategy("saved/1")).resolves.toEqual({ id: "saved/1" });

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/strategies", { signal: undefined });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/strategies/saved%2F1", { signal: undefined });
  });

  it("surfaces API detail for validation failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "selected contracts must share one expiration" }), { status: 422 })));

    await expect(evaluateStrategy(draft)).rejects.toEqual(new StrategyApiError(422, "selected contracts must share one expiration"));
  });
});
