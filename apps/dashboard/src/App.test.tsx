import { afterEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

    expect(screen.getByText("Loading the latest NVDA saved snapshot…")).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveAttribute("aria-busy", "true");
  });

  it("offers the explicitly labeled NVDA demo after a missing NVDA snapshot", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "No latest market snapshot found" }), { status: 404 })));

    render(<App />);

    expect(await screen.findByRole("heading", { name: "No NVDA snapshot yet" })).toBeInTheDocument();
    expect(screen.getByText(/packaged NVDA demo snapshot/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load NVDA demo snapshot" })).toBeInTheDocument();
  });

  it("shows an actionable generic error state when the API request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Service unavailable" }), { status: 500 })));

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Market snapshot unavailable" })).toBeInTheDocument();
    expect(screen.getByText("Service unavailable")).toBeInTheDocument();
    expect(screen.getByText("Confirm the local API is running, then reload the saved snapshot.")).toBeInTheDocument();
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
    fireEvent.click(await screen.findByRole("button", { name: "Load NVDA demo snapshot" }));
    expect(await screen.findByRole("heading", { name: "NVDA" })).toBeInTheDocument();
  });

  it("cancels a pending demo load when the dashboard closes", async () => {
    let demoSignal: AbortSignal | undefined;
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "No latest market snapshot found" }), { status: 404 }))
      .mockImplementationOnce((_input: RequestInfo | URL, init?: RequestInit) => {
        demoSignal = init?.signal ?? undefined;
        return new Promise<Response>(() => undefined);
      });
    vi.stubGlobal("fetch", fetchMock);
    const { unmount } = render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Load NVDA demo snapshot" }));

    unmount();

    expect(demoSignal?.aborted).toBe(true);
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

  it("switches among all seven supported tickers", async () => {
    const aaplSnapshot = {
      ...nvdaSnapshot,
      snapshot_id: "aapl-snapshot",
      underlying: { ...nvdaSnapshot.underlying, ticker: "AAPL", price: "241.50" },
      options: nvdaSnapshot.options.map((option) => ({ ...option, ticker: "AAPL" })),
    };
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => Promise.resolve(
      new Response(JSON.stringify(String(input).includes("/AAPL/") ? aaplSnapshot : nvdaSnapshot), { status: 200 }),
    )));

    render(<App />);
    await screen.findByRole("heading", { name: "NVDA" });

    const selector = screen.getByRole("group", { name: "Ticker" });
    for (const ticker of ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA"]) {
      expect(selector).toContainElement(screen.getByRole("button", { name: ticker }));
    }
    fireEvent.click(screen.getByRole("button", { name: "AAPL" }));

    expect(await screen.findByRole("heading", { name: "AAPL" })).toBeInTheDocument();
    expect(screen.getByText("$241.50")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "AAPL" })).toHaveAttribute("aria-pressed", "true");
  });

  it("does not offer NVDA demo evidence for a missing non-NVDA ticker", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      if (String(input).includes("/AAPL/")) {
        return Promise.resolve(new Response(JSON.stringify({ detail: "No latest market snapshot found" }), { status: 404 }));
      }
      return Promise.resolve(new Response(JSON.stringify(nvdaSnapshot), { status: 200 }));
    }));
    render(<App />);
    await screen.findByRole("heading", { name: "NVDA" });

    fireEvent.click(screen.getByRole("button", { name: "AAPL" }));

    expect(await screen.findByRole("heading", { name: "No AAPL snapshot yet" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /demo snapshot/i })).not.toBeInTheDocument();
    expect(screen.getByText(/Select another ticker or reload the saved snapshot/i)).toBeInTheDocument();
  });

  it("rejects an older ticker response that arrives after the selected ticker", async () => {
    let resolveNvda!: (response: Response) => void;
    const nvdaRequest = new Promise<Response>((resolve) => { resolveNvda = resolve; });
    const aaplSnapshot = {
      ...nvdaSnapshot,
      snapshot_id: "aapl-newer",
      underlying: { ...nvdaSnapshot.underlying, ticker: "AAPL", price: "242.00" },
      options: nvdaSnapshot.options.map((option) => ({ ...option, ticker: "AAPL" })),
    };
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => String(input).includes("/AAPL/")
      ? Promise.resolve(new Response(JSON.stringify(aaplSnapshot), { status: 200 }))
      : nvdaRequest));
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "AAPL" }));
    expect(await screen.findByRole("heading", { name: "AAPL" })).toBeInTheDocument();

    await act(async () => resolveNvda(new Response(JSON.stringify(nvdaSnapshot), { status: 200 })));
    expect(screen.getByRole("heading", { name: "AAPL" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "NVDA" })).not.toBeInTheDocument();
  });

  it("reloads the selected saved snapshot and shows the replacement", async () => {
    const revised = { ...nvdaSnapshot, snapshot_id: "reloaded-snapshot", underlying: { ...nvdaSnapshot.underlying, price: "183.75" } };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(nvdaSnapshot), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(revised), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await screen.findByText("$180.25");

    fireEvent.click(screen.getByRole("button", { name: "Reload NVDA saved data" }));

    expect(await screen.findByText("$183.75")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("resets the Strategy Lab draft when ticker evidence changes", async () => {
    const aaplSnapshot = {
      ...nvdaSnapshot,
      snapshot_id: "aapl-lab-snapshot",
      underlying: { ...nvdaSnapshot.underlying, ticker: "AAPL" },
      options: nvdaSnapshot.options.map((option) => ({ ...option, ticker: "AAPL" })),
    };
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => Promise.resolve(
      new Response(JSON.stringify(String(input).includes("/AAPL/") ? aaplSnapshot : nvdaSnapshot), { status: 200 }),
    )));
    render(<App />);
    await screen.findByRole("heading", { name: "NVDA" });
    fireEvent.click(screen.getByRole("button", { name: "Strategy Lab" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Name" }), { target: { value: "Keep out of AAPL" } });

    fireEvent.click(screen.getByRole("button", { name: "AAPL" }));

    await waitFor(() => expect(screen.getByRole("textbox", { name: "Name" })).toHaveValue("AAPL 175 / 185 call spread"));
    expect(screen.getByRole("textbox", { name: "Name" })).not.toHaveValue("Keep out of AAPL");
  });
});
