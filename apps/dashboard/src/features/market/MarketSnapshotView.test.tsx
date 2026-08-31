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
    expect(screen.getByText("FROZEN")).toBeInTheDocument();
    expect(screen.getByText(/source mock/i)).toBeInTheDocument();
    expect(screen.getAllByText(/2026-08-28 20:00 UTC/i)).not.toHaveLength(0);
    expect(screen.getByRole("heading", { name: "Expiration horizon" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Available option expirations" })).toHaveTextContent("Sep 18, 2026");
    expect(screen.getByRole("list", { name: "Available option expirations" })).toHaveTextContent("Oct 16, 2026");
    expect(screen.getByRole("heading", { name: "Liquidity by strike" })).toBeInTheDocument();
    expect(screen.getByTestId("liquidity-plot")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Open interest by strike" })).toBeInTheDocument();
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
});
