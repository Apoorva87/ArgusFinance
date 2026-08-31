import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchLatestSnapshot } from "./market";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchLatestSnapshot", () => {
  it("uppercases and URL-encodes the ticker in a relative latest-snapshot request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ snapshot_id: "snapshot-1" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchLatestSnapshot(" nv da/? ")).resolves.toEqual({ snapshot_id: "snapshot-1" });

    expect(fetchMock).toHaveBeenCalledWith("/api/market/NV%20DA%2F%3F/latest", { signal: undefined });
  });

  it("throws a typed status and API detail for a non-success response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "No latest market snapshot found" }), { status: 404 })));

    await expect(fetchLatestSnapshot("nvda")).rejects.toMatchObject({
      name: "MarketApiError",
      status: 404,
      detail: "No latest market snapshot found",
    });
  });
});
