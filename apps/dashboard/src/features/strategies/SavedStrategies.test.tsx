import { act, fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { SavedStrategy } from "../../api/strategies";
import { SavedStrategies } from "./SavedStrategies";

vi.mock("react-plotly.js", () => ({ default: () => <div aria-label="Expiration payoff chart" /> }));

const saved: SavedStrategy = {
  id: "8f2d60cf-2ba8-4529-b9d9-b4852cd4ce14",
  created_at: "2026-09-08T12:00:00Z",
  draft: {
    snapshot_id: "00000000-0000-0000-0000-000000000001",
    name: "NVDA defined-risk upside",
    status: "PAPER",
    thesis: "Upside is plausible while price holds the review floor.",
    pricing: "NATURAL",
    fee_per_contract: "0",
    legs: [{ expiration: "2026-09-18", strike: "175", option_type: "CALL", side: "BUY", quantity: 1 }],
    boundaries: [{ kind: "PRICE_BELOW", value: "170", note: "Revisit the thesis" }],
  },
  evaluation: {
    snapshot_id: "00000000-0000-0000-0000-000000000001",
    ticker: "NVDA", expiration: "2026-09-18", spot: "180.25", pricing: "NATURAL",
    legs: [{ expiration: "2026-09-18", strike: "175", option_type: "CALL", side: "BUY", quantity: 1, entry_premium: "8.80", delta: "0.64", gamma: "0.012", theta: "-0.15", vega: "0.21" }],
    net_debit: "880", entry_fees: "0", maximum_profit: null, maximum_loss: "880", breakevens: ["183.8"],
    payoff_points: [{ spot: "0", pnl: "-880" }, { spot: "183.8", pnl: "0" }, { spot: "220", pnl: "3620" }],
    net_greeks: { delta: "64", gamma: "1.2", theta: "-15", vega: "21" },
    warnings: ["FROZEN/mock snapshot: hypothetical analysis, not live market evidence"], eligible: true,
    analytics_version: "expiration-payoff-v1", source_timestamp: "2026-08-28T20:00:00Z", source_status: "FROZEN",
    boundaries: [{ kind: "PRICE_BELOW", value: "170", note: "Revisit the thesis" }],
  },
};

afterEach(() => vi.unstubAllGlobals());

describe("SavedStrategies", () => {
  it("invites the operator to evaluate a strategy when the saved list is empty", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("[]", { status: 200 })));
    render(<SavedStrategies />);
    expect(await screen.findByRole("heading", { name: "No saved strategies" })).toBeInTheDocument();
    expect(screen.getByText(/Evaluate and save a snapshot-backed strategy/i)).toBeInTheDocument();
  });

  it("retries a failed list request", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Database unavailable" }), { status: 500 }))
      .mockResolvedValueOnce(new Response("[]", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<SavedStrategies />);
    expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry saved strategies" }));
    expect(await screen.findByRole("heading", { name: "No saved strategies" })).toBeInTheDocument();
  });

  it("reopens the original saved evidence from the detail endpoint", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([saved]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(saved), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<SavedStrategies />);
    fireEvent.click(await screen.findByRole("button", { name: /Open NVDA defined-risk upside/i }));

    expect(await screen.findByRole("heading", { name: "NVDA defined-risk upside" })).toBeInTheDocument();
    expect(screen.getByText("PAPER")).toBeInTheDocument();
    expect(screen.getByText("Upside is plausible while price holds the review floor.")).toBeInTheDocument();
    expect(screen.getByText("Revisit the thesis")).toBeInTheDocument();
    expect(screen.getByText(/Aug 28, 2026/i)).toBeInTheDocument();
    expect(screen.getByText("Snapshot 00000000-0000-0000-0000-000000000001")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Entry legs" })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /BUY 1 175 CALL 2026-09-18 \$8.80/i })).toBeInTheDocument();
    expect(screen.getByText("Natural quotes")).toBeInTheDocument();
    expect(screen.getByText("Unlimited")).toBeInTheDocument();
  });

  it("keeps the list available when opening one saved detail fails", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([saved]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Saved strategy was not found" }), { status: 404 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<SavedStrategies />);
    fireEvent.click(await screen.findByRole("button", { name: /Open NVDA defined-risk upside/i }));

    expect(await screen.findByText("Saved strategy was not found")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Open NVDA defined-risk upside/i })).toBeInTheDocument();
  });

  it("does not let an older detail response replace the newest selection", async () => {
    const newer = { ...saved, id: "newer-id", draft: { ...saved.draft, name: "Newer thesis" } };
    let resolveOlder!: (value: Response) => void;
    let resolveNewer!: (value: Response) => void;
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([saved, newer]), { status: 200 }))
      .mockImplementationOnce(() => new Promise<Response>((resolve) => { resolveOlder = resolve; }))
      .mockImplementationOnce(() => new Promise<Response>((resolve) => { resolveNewer = resolve; }));
    vi.stubGlobal("fetch", fetchMock);
    render(<SavedStrategies />);
    fireEvent.click(await screen.findByRole("button", { name: /Open NVDA defined-risk upside/i }));
    fireEvent.click(screen.getByRole("button", { name: /Open Newer thesis/i }));
    await act(async () => resolveNewer(new Response(JSON.stringify(newer), { status: 200 })));
    expect(await screen.findByRole("heading", { name: "Newer thesis" })).toBeInTheDocument();
    await act(async () => resolveOlder(new Response(JSON.stringify(saved), { status: 200 })));
    expect(screen.getByRole("heading", { name: "Newer thesis" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "NVDA defined-risk upside" })).not.toBeInTheDocument();
  });
});
