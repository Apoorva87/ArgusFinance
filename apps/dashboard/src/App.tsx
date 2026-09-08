import { useEffect, useState } from "react";
import { captureSnapshot, fetchLatestSnapshot, MarketApiError, type MarketSnapshot } from "./api/market";
import { MarketSnapshotView } from "./features/market/MarketSnapshotView";
import { SavedStrategies } from "./features/strategies/SavedStrategies";
import { StrategyLab } from "./features/strategies/StrategyLab";

type View = "market" | "lab" | "saved";
type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; snapshot: MarketSnapshot }
  | { kind: "missing"; detail: string }
  | { kind: "error"; detail: string };

function AppNav({ view, onChange }: { view: View; onChange: (view: View) => void }) {
  const items: Array<[View, string]> = [["market", "Market"], ["lab", "Strategy Lab"], ["saved", "Saved Strategies"]];
  return <nav className="app-nav" aria-label="Primary"><a className="wordmark" href="#market" onClick={(event) => { event.preventDefault(); onChange("market"); }}>ARGUS</a><div>{items.map(([key, label]) => <button key={key} type="button" aria-current={view === key ? "page" : undefined} onClick={() => onChange(key)}>{label}</button>)}</div></nav>;
}

function MissingMarket({ title, detail, capturePhase, onCapture }: { title: string; detail: string; capturePhase: "idle" | "loading" | "error"; onCapture: () => void }) {
  return <main className="state-view"><h1>{title}</h1><p>{detail}</p><p>Load the packaged deterministic snapshot to use the local research workflow.</p><button className="primary-button" type="button" onClick={onCapture} disabled={capturePhase === "loading"}>{capturePhase === "loading" ? "Loading demo snapshot…" : "Load demo snapshot"}</button>{capturePhase === "error" && <p role="alert">The demo snapshot could not be loaded. Confirm the local API is running, then try again.</p>}</main>;
}

export default function App() {
  const [view, setView] = useState<View>("market");
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [capturePhase, setCapturePhase] = useState<"idle" | "loading" | "error">("idle");

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

  async function loadDemo() {
    setCapturePhase("loading");
    try { const snapshot = await captureSnapshot("NVDA"); setState({ kind: "ready", snapshot }); setCapturePhase("idle"); }
    catch { setCapturePhase("error"); }
  }

  let content;
  if (view === "saved") content = <SavedStrategies />;
  else if (state.kind === "ready") content = view === "market" ? <MarketSnapshotView snapshot={state.snapshot} /> : <StrategyLab snapshot={state.snapshot} />;
  else if (state.kind === "loading") content = <main className="state-view" aria-busy="true"><p>Loading the latest NVDA market snapshot…</p></main>;
  else if (state.kind === "missing") content = <MissingMarket title={view === "lab" ? "Strategy Lab needs market evidence" : "No NVDA snapshot yet"} detail={state.detail} capturePhase={capturePhase} onCapture={() => void loadDemo()} />;
  else content = <main className="state-view"><h1>Market snapshot unavailable</h1><p>{state.detail}</p><p>Confirm the local API is running, then refresh.</p></main>;

  return <div className="app-shell"><AppNav view={view} onChange={setView} />{content}</div>;
}
