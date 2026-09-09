import { render, screen } from "@testing-library/react";
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

    expect(screen.getByText(/Options are frozen\/delayed while the underlying is realtime/i)).toBeInTheDocument();
    expect(screen.getByText(/Option bid\/ask source times are unavailable/i)).toBeInTheDocument();
    expect(screen.getByText("Attempted three standard expirations; two contained usable quotes.")).toBeInTheDocument();
    expect(screen.getByText("Snapshot age")).toBeInTheDocument();
    expect(screen.getByText("Option retrieval")).toBeInTheDocument();
    expect(screen.getByText("Implied volatility")).toBeInTheDocument();
  });

  it("labels liquidity totals partial and leaves wholly missing open interest unavailable", () => {
    const options = nvdaSnapshot.options.slice(0, 3).map((option, index) => ({
      ...option,
      strike: index < 2 ? "175" : "185",
      option_type: index === 1 ? "PUT" as const : "CALL" as const,
      open_interest: index === 0 ? 120 : null,
    }));

    render(<MarketSnapshotView snapshot={{ ...nvdaSnapshot, options }} />);

    const table = screen.getByRole("table", { name: "Open interest by strike" });
    expect(table).toHaveTextContent("120");
    expect(table).toHaveTextContent("partial");
    expect(screen.getByRole("rowheader", { name: "185" }).parentElement).toHaveTextContent("Unavailable");
    expect(screen.getByText(/Missing open interest is excluded/i)).toBeInTheDocument();
  });
});
