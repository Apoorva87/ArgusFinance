import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import type { StrategyEvaluation } from "../../api/strategies";
import { PayoffChart } from "./PayoffChart";

let capturedLayout: Record<string, unknown> = {};
vi.mock("react-plotly.js", () => ({
  default: (props: { layout: Record<string, unknown> }) => {
    capturedLayout = props.layout;
    return <div aria-label="Rendered payoff plot" />;
  },
}));

const evaluation = {
  spot: "180.25",
  breakevens: ["180.05"],
  boundaries: [],
  payoff_points: [{ spot: "175", pnl: "-505" }, { spot: "185", pnl: "495" }],
} as unknown as StrategyEvaluation;

describe("PayoffChart", () => {
  it("anchors vertical marker labels inside the visible plot", () => {
    render(<PayoffChart evaluation={evaluation} />);

    expect(screen.getByLabelText("Rendered payoff plot")).toBeInTheDocument();
    const annotations = capturedLayout.annotations as Array<{ y: number; yanchor: string }>;
    expect(annotations.every((annotation) => annotation.y <= 1 && annotation.yanchor === "top")).toBe(true);
  });
});
