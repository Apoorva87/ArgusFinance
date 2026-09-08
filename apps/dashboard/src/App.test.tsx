import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import App from "./App";
import { nvdaSnapshot } from "./test/nvdaSnapshot";

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
    expect(screen.getByText(/Load the packaged deterministic snapshot/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load demo snapshot" })).toBeInTheDocument();
  });

  it("shows an actionable generic error state when the API request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Service unavailable" }), { status: 500 })));

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Market snapshot unavailable" })).toBeInTheDocument();
    expect(screen.getByText("Service unavailable")).toBeInTheDocument();
    expect(screen.getByText("Confirm the local API is running, then refresh.")).toBeInTheDocument();
  });

  it("navigates between the market explorer, Strategy Lab, and saved research", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      if (String(input) === "/api/strategies") return Promise.resolve(new Response("[]", { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify(nvdaSnapshot), { status: 200 }));
    }));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "NVDA" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Strategy Lab" }));
    expect(screen.getByRole("heading", { name: "Strategy Lab" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Saved Strategies" }));
    expect(await screen.findByRole("heading", { name: "No saved strategies" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Market" }));
    expect(screen.getByRole("heading", { name: "NVDA" })).toBeInTheDocument();
  });

  it("loads demo evidence from the missing-market state", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "No latest market snapshot found" }), { status: 404 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(nvdaSnapshot), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Load demo snapshot" }));
    expect(await screen.findByRole("heading", { name: "NVDA" })).toBeInTheDocument();
  });

  it("opens Saved Strategies even when there is no latest market evidence", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "No latest market snapshot found" }), { status: 404 }))
      .mockResolvedValueOnce(new Response("[]", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await screen.findByRole("heading", { name: "No NVDA snapshot yet" });
    fireEvent.click(screen.getByRole("button", { name: "Saved Strategies" }));
    expect(await screen.findByRole("heading", { name: "No saved strategies" })).toBeInTheDocument();
  });
});
