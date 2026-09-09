import { render, screen, within } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";
import { MarketSnapshotView } from "./MarketSnapshotView";
import { nvdaSnapshot } from "../../test/nvdaSnapshot";

vi.mock("react-plotly.js", () => ({
  default: () => <div data-testid="liquidity-plot" />,
}));

describe("MarketSnapshotView", () => {
  it("renders exact provenance, a sorted expiration rail, and accessible liquidity text", () => {
    render(<MarketSnapshotView snapshot={nvdaSnapshot} />);

    expect(screen.getByRole("heading", { name: "NVDA" })).toBeInTheDocument();
    expect(screen.getByText("$180.25")).toBeInTheDocument();
    expect(screen.getAllByText("FROZEN")).not.toHaveLength(0);
    expect(screen.getByText(/source mock/i)).toBeInTheDocument();
    expect(screen.getAllByText(/2026-08-28 20:00 UTC/i)).not.toHaveLength(0);
    expect(screen.getByRole("heading", { name: "Expiration horizon" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Available option expirations" })).toHaveTextContent("Sep 18, 2026");
    expect(screen.getByRole("list", { name: "Available option expirations" })).toHaveTextContent("Oct 16, 2026");
    expect(screen.getByRole("heading", { name: "Liquidity by strike" })).toBeInTheDocument();
    expect(screen.getByTestId("liquidity-plot")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Open interest by strike" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "175" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "185" })).toBeInTheDocument();
  });

  it("warns when data is delayed or frozen", () => {
    render(<MarketSnapshotView snapshot={nvdaSnapshot} />);

    expect(screen.getByRole("status")).toHaveTextContent(/frozen/i);
    expect(screen.getByRole("status")).toHaveTextContent(/2026-08-28 20:00 UTC/i);
  });

  it("shows Greeks unavailable without replacing null values", () => {
    render(
      <MarketSnapshotView
        snapshot={{
          ...nvdaSnapshot,
          underlying: { ...nvdaSnapshot.underlying, status: "UNAVAILABLE" },
          options: nvdaSnapshot.options.map((option) => ({ ...option, delta: null, gamma: null, theta: null, vega: null, status: "UNAVAILABLE" })),
        }}
      />,
    );

    expect(screen.getByText(/Greeks unavailable/i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/unavailable/i);
  });

  it("discloses frozen options even when the underlying quote is realtime", () => {
    render(
      <MarketSnapshotView
        snapshot={{
          ...nvdaSnapshot,
          notes: ["Attempted three standard expirations; two contained usable quotes."],
          underlying: { ...nvdaSnapshot.underlying, status: "REALTIME" },
          options: nvdaSnapshot.options.map((option) => ({
            ...option,
            status: "FROZEN_DELAYED",
            source_timestamp: null,
            implied_volatility: null,
            delta: null,
            gamma: null,
            theta: null,
            vega: null,
          })),
        }}
      />,
    );

    expect(screen.getByText(/All 8 option quotes are frozen\/delayed; the underlying was reported realtime/i)).toBeInTheDocument();
    expect(screen.getByText(/Option bid\/ask source times are unavailable/i)).toBeInTheDocument();
    expect(screen.getByText("Attempted three standard expirations; two contained usable quotes.")).toBeInTheDocument();
    expect(screen.getByText("Snapshot age")).toBeInTheDocument();
    expect(screen.getByText("Option retrieval")).toBeInTheDocument();
    expect(screen.getByText("Implied volatility")).toBeInTheDocument();
  });

  it("reports the exact frozen option count for a mixed-status chain", () => {
    render(
      <MarketSnapshotView
        snapshot={{
          ...nvdaSnapshot,
          underlying: { ...nvdaSnapshot.underlying, status: "REALTIME" },
          options: nvdaSnapshot.options.map((option, index) => ({
            ...option,
            status: index < 3 ? "FROZEN_DELAYED" : "REALTIME",
          })),
        }}
      />,
    );

    expect(screen.getByText(/3 of 8 option quotes are frozen\/delayed; the underlying was reported realtime/i)).toBeInTheDocument();
    expect(screen.queryByText(/All 8 option quotes are frozen\/delayed/i)).not.toBeInTheDocument();
  });

  it("labels liquidity totals partial and leaves wholly missing open interest unavailable", () => {
    const option = nvdaSnapshot.options[0];
    const options = [
      { ...option, expiration: "2026-09-18", strike: "175", option_type: "CALL" as const, open_interest: 120 },
      { ...option, expiration: "2026-10-16", strike: "175", option_type: "CALL" as const, open_interest: null },
      { ...option, expiration: "2026-09-18", strike: "185", option_type: "CALL" as const, open_interest: null },
    ];

    render(<MarketSnapshotView snapshot={{ ...nvdaSnapshot, options }} />);

    const partialRow = screen.getByRole("rowheader", { name: "175" }).parentElement;
    const missingRow = screen.getByRole("rowheader", { name: "185" }).parentElement;
    expect(within(partialRow!).getAllByRole("cell")[0]).toHaveTextContent(/^120 \(partial\)$/);
    expect(within(missingRow!).getAllByRole("cell")[0]).toHaveTextContent(/^Unavailable$/);
    expect(screen.getByText(/Missing open interest is excluded/i)).toBeInTheDocument();
  });
});
