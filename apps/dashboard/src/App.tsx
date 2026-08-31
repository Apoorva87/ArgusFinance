import { useEffect, useState } from "react";
import { fetchLatestSnapshot, MarketApiError, type MarketSnapshot } from "./api/market";
import { MarketSnapshotView } from "./features/market/MarketSnapshotView";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; snapshot: MarketSnapshot }
  | { kind: "missing"; detail: string }
  | { kind: "error"; detail: string };

export default function App() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    fetchLatestSnapshot("NVDA", controller.signal)
      .then((snapshot) => setState({ kind: "ready", snapshot }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (error instanceof MarketApiError && error.status === 404) setState({ kind: "missing", detail: error.detail });
        else setState({ kind: "error", detail: error instanceof Error ? error.message : "The market snapshot could not be loaded." });
      });
    return () => controller.abort();
  }, []);

  if (state.kind === "ready") return <MarketSnapshotView snapshot={state.snapshot} />;
  if (state.kind === "loading") return <main className="state-view" aria-busy="true"><p>Loading the latest NVDA market snapshot…</p></main>;
  if (state.kind === "missing") return <main className="state-view"><h1>No NVDA snapshot yet</h1><p>{state.detail}</p><p>Capture a local NVDA snapshot, then refresh this observatory.</p></main>;
  return <main className="state-view"><h1>Market snapshot unavailable</h1><p>{state.detail}</p><p>Confirm the local API is running, then refresh.</p></main>;
}
