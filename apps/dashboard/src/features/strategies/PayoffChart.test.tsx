import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import type { StrategyEvaluation } from "../../api/strategies";
import { PayoffChart } from "./PayoffChart";

vi.mock("react-plotly.js", () => ({
  default: () => <div aria-label="Rendered payoff plot" />,
}));

const evaluation = {
  spot: "180.25",
  breakevens: ["180.05"],
  boundaries: [],
  payoff_points: [{ spot: "175", pnl: "-505" }, { spot: "185", pnl: "495" }],
} as unknown as StrategyEvaluation;

describe("PayoffChart", () => {
  it("shows close payoff marker values in a readable list outside the plot", () => {
    render(<PayoffChart evaluation={evaluation} />);

    expect(screen.getByLabelText("Rendered payoff plot")).toBeInTheDocument();
    const markers = screen.getByRole("list", { name: "Payoff markers" });
    expect(markers).toHaveTextContent("Spot $180.25");
    expect(markers).toHaveTextContent("Break-even $180.05");
  });
});
