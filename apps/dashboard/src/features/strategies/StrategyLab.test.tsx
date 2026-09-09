import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nvdaSnapshot } from "../../test/nvdaSnapshot";
import type { StrategyEvaluation } from "../../api/strategies";
import { StrategyLab } from "./StrategyLab";

vi.mock("react-plotly.js", () => ({ default: () => <div aria-label="Expiration payoff chart" /> }));

const evaluation: StrategyEvaluation = {
  snapshot_id: nvdaSnapshot.snapshot_id,
  ticker: "NVDA",
  expiration: "2026-09-18",
  spot: "180.25",
  pricing: "NATURAL",
  legs: [
    { expiration: "2026-09-18", strike: "175", option_type: "CALL", side: "BUY", quantity: 1, entry_premium: "8.80", delta: "0.64", gamma: "0.012", theta: "-0.15", vega: "0.21" },
    { expiration: "2026-09-18", strike: "185", option_type: "CALL", side: "SELL", quantity: 1, entry_premium: "3.75", delta: "0.42", gamma: "0.013", theta: "-0.14", vega: "0.22" },
  ],
  net_debit: "505",
  entry_fees: "0",
  maximum_profit: "495",
  maximum_loss: "505",
  breakevens: ["180.05"],
  payoff_points: [{ spot: "0", pnl: "-505" }, { spot: "175", pnl: "-505" }, { spot: "180.05", pnl: "0" }, { spot: "180.25", pnl: "20" }, { spot: "185", pnl: "495" }],
  net_greeks: { delta: "22", gamma: "-0.1", theta: "-1", vega: "-1" },
  warnings: ["FROZEN/mock snapshot: hypothetical analysis, not live market evidence"],
  eligible: true,
  analytics_version: "expiration-payoff-v1",
  source_timestamp: "2026-08-28T20:00:00Z",
  source_status: "FROZEN",
  boundaries: [],
};

afterEach(() => vi.unstubAllGlobals());

function response(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

describe("StrategyLab", () => {
  it("evaluates the canonical same-expiration vertical and renders returned evidence", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => response(evaluation)));
    render(<StrategyLab snapshot={nvdaSnapshot} />);

    expect(screen.getByRole("combobox", { name: "Expiration" })).toHaveValue("2026-09-18");
    expect(screen.getByRole("combobox", { name: "Strike for leg 1" })).toHaveValue("175");
    expect(screen.getByRole("combobox", { name: "Strike for leg 2" })).toHaveValue("185");
    expect(screen.getByRole("button", { name: "Save strategy" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Evaluate strategy" }));

    expect(await screen.findByText("Maximum loss")).toBeInTheDocument();
    expect(screen.getAllByText("$505.00")).not.toHaveLength(0);
    expect(screen.getAllByText("$495.00")).not.toHaveLength(0);
    expect(screen.getAllByText("$180.05")).not.toHaveLength(0);
    expect(screen.getByText(/hypothetical analysis, not live market evidence/i)).toBeInTheDocument();
    expect(screen.getByText("Delta (share-equivalent)")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Expiration payoff scenarios" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save strategy" })).toBeEnabled();
  });

  it("invalidates evaluation and save when any draft input changes", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => response(evaluation)));
    render(<StrategyLab snapshot={nvdaSnapshot} />);
    fireEvent.click(screen.getByRole("button", { name: "Evaluate strategy" }));
    expect(await screen.findByRole("button", { name: "Save strategy" })).toBeEnabled();

    fireEvent.change(screen.getByRole("textbox", { name: "Thesis" }), { target: { value: "Changed after evaluation" } });

    expect(screen.getByText(/Inputs changed. Evaluate again before saving./i)).toBeInTheDocument();
    expect(screen.queryByText("Maximum loss")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save strategy" })).toBeDisabled();
  });

  it("ignores an evaluation response that arrives after the draft changes", async () => {
    let resolveRequest!: (value: Response) => void;
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => { resolveRequest = resolve; })));
    render(<StrategyLab snapshot={nvdaSnapshot} />);
    fireEvent.click(screen.getByRole("button", { name: "Evaluate strategy" }));
    expect(screen.getByRole("button", { name: "Evaluating…" })).toBeDisabled();

    fireEvent.change(screen.getByRole("spinbutton", { name: "Fee per contract" }), { target: { value: "1" } });
    resolveRequest(new Response(JSON.stringify(evaluation), { status: 200 }));

    await waitFor(() => expect(screen.queryByText("Maximum loss")).not.toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Save strategy" })).toBeDisabled();
  });

  it("shows unavailable Greek values and unbounded risk without inventing numbers", async () => {
    const unbounded = {
      ...evaluation,
      maximum_profit: null,
      net_greeks: { ...evaluation.net_greeks, vega: null },
    };
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => response(unbounded)));
    render(<StrategyLab snapshot={nvdaSnapshot} />);
    fireEvent.click(screen.getByRole("button", { name: "Evaluate strategy" }));

    expect(await screen.findByText("Unlimited")).toBeInTheDocument();
    expect(screen.getByText("Vega ($ / volatility point)").nextElementSibling).toHaveTextContent("Unavailable");
  });

  it("saves only the evaluated draft and reports the immutable saved record", async () => {
    const fetchMock = vi.fn()
      .mockImplementationOnce(() => response(evaluation))
      .mockImplementationOnce(() => response({ id: "saved-1", created_at: "2026-09-08T12:00:00Z", draft: {}, evaluation }, 201));
    vi.stubGlobal("fetch", fetchMock);
    render(<StrategyLab snapshot={nvdaSnapshot} />);
    fireEvent.click(screen.getByRole("button", { name: "Evaluate strategy" }));
    fireEvent.click(await screen.findByRole("button", { name: "Save strategy" }));

    expect(await screen.findByText("Saved strategy saved-1.")).toBeInTheDocument();
  });

  it("recognizes canonical spread strikes serialized with fixed decimal scale", () => {
    const scaled = {
      ...nvdaSnapshot,
      options: nvdaSnapshot.options.map((option) => ({
        ...option,
        strike: `${option.strike}.000000`,
      })),
    };
    vi.stubGlobal("fetch", vi.fn());
    render(<StrategyLab snapshot={scaled} />);

    expect(screen.getByRole("textbox", { name: "Name" })).toHaveValue("NVDA 175 / 185 call spread");
    expect(screen.getByRole("combobox", { name: "Strike for leg 1" })).toHaveValue("175.000000");
    expect(screen.getByRole("combobox", { name: "Strike for leg 2" })).toHaveValue("185.000000");
  });

  it("uses a neutral strategy name when the canonical spread is unavailable", () => {
    const otherChain = {
      ...nvdaSnapshot,
      options: nvdaSnapshot.options.map((option) => ({ ...option, strike: String(Number(option.strike) + 10) })),
    };
    vi.stubGlobal("fetch", vi.fn());
    render(<StrategyLab snapshot={otherChain} />);

    expect(screen.getByRole("textbox", { name: "Name" })).toHaveValue("NVDA strategy");
  });

  it("labels midpoint pricing as hypothetical before evaluation", () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<StrategyLab snapshot={nvdaSnapshot} />);
    fireEvent.change(screen.getByRole("combobox", { name: "Pricing" }), { target: { value: "MIDPOINT" } });
    expect(screen.getByText(/Midpoint pricing is hypothetical/i)).toBeInTheDocument();
  });

  it("explains that an unlimited tail continues beyond the finite chart", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => response({ ...evaluation, maximum_profit: null })));
    render(<StrategyLab snapshot={nvdaSnapshot} />);
    fireEvent.click(screen.getByRole("button", { name: "Evaluate strategy" }));
    expect(await screen.findByText(/Unlimited profit continues beyond the plotted range/i)).toBeInTheDocument();
  });

  it("shows a readable evaluation error and allows another attempt", async () => {
    const fetchMock = vi.fn()
      .mockImplementationOnce(() => response({ detail: "duplicate contract rows are not allowed" }, 422))
      .mockImplementationOnce(() => response(evaluation));
    vi.stubGlobal("fetch", fetchMock);
    render(<StrategyLab snapshot={nvdaSnapshot} />);
    fireEvent.click(screen.getByRole("button", { name: "Evaluate strategy" }));
    expect(await screen.findByText("duplicate contract rows are not allowed")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Evaluate strategy" }));
    expect(await screen.findByText("Maximum loss")).toBeInTheDocument();
  });
});
