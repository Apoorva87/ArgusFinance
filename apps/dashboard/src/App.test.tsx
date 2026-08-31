import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import App from "./App";

vi.mock("react-plotly.js", () => ({
  default: () => <div aria-label="Liquidity chart" />,
}));

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("shows an explicit loading state while the market request is pending", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));

    render(<App />);

    expect(screen.getByText("Loading the latest NVDA market snapshot…")).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveAttribute("aria-busy", "true");
  });

  it("invites the operator to capture a snapshot after a 404", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "No latest market snapshot found" }), { status: 404 })));

    render(<App />);

    expect(await screen.findByRole("heading", { name: "No NVDA snapshot yet" })).toBeInTheDocument();
    expect(screen.getByText("Capture a local NVDA snapshot, then refresh this observatory.")).toBeInTheDocument();
  });

  it("shows an actionable generic error state when the API request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Service unavailable" }), { status: 500 })));

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Market snapshot unavailable" })).toBeInTheDocument();
    expect(screen.getByText("Service unavailable")).toBeInTheDocument();
    expect(screen.getByText("Confirm the local API is running, then refresh.")).toBeInTheDocument();
  });
});
