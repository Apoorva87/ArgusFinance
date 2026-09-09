import { useEffect, useRef, useState } from "react";
import { captureSnapshot, fetchLatestSnapshot, MarketApiError, type MarketSnapshot } from "./api/market";
import { MarketSnapshotView } from "./features/market/MarketSnapshotView";
import { SavedStrategies } from "./features/strategies/SavedStrategies";
import { StrategyLab } from "./features/strategies/StrategyLab";

type View = "market" | "lab" | "saved";
const TICKERS = ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA"] as const;
type Ticker = typeof TICKERS[number];
type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; snapshot: MarketSnapshot }
  | { kind: "missing"; detail: string }
  | { kind: "error"; detail: string };

function AppNav({ view, onChange }: { view: View; onChange: (view: View) => void }) {
  const items: Array<[View, string]> = [["market", "Market"], ["lab", "Strategy Lab"], ["saved", "Saved Strategies"]];
  return <nav className="app-nav" aria-label="Primary"><a className="wordmark" href="#market" onClick={(event) => { event.preventDefault(); onChange("market"); }}>ARGUS</a><div>{items.map(([key, label]) => <button key={key} type="button" aria-current={view === key ? "page" : undefined} onClick={() => onChange(key)}>{label}</button>)}</div></nav>;
}

function MarketControls({ ticker, loading, onSelect, onReload }: { ticker: Ticker; loading: boolean; onSelect: (ticker: Ticker) => void; onReload: () => void }) {
  return (
    <section className="market-controls" aria-label="Market snapshot controls">
      <div className="ticker-selector" role="group" aria-label="Ticker">
        {TICKERS.map((candidate) => <button key={candidate} type="button" aria-pressed={ticker === candidate} onClick={() => onSelect(candidate)}>{candidate}</button>)}
      </div>
      <button className="reload-button" type="button" onClick={onReload} disabled={loading} aria-label={`Reload ${ticker} saved data`}>
        {loading ? "Loading…" : "Reload saved data"}
      </button>
    </section>
  );
}

function MissingMarket({ ticker, title, detail, capturePhase, onCapture }: { ticker: Ticker; title: string; detail: string; capturePhase: "idle" | "loading" | "error"; onCapture?: () => void }) {
  return (
    <main className="state-view">
      <h1>{title}</h1>
      <p>{detail}</p>
      {onCapture ? (
        <>
          <p>Load the packaged NVDA demo snapshot to use the local research workflow.</p>
          <button className="primary-button" type="button" onClick={onCapture} disabled={capturePhase === "loading"}>{capturePhase === "loading" ? "Loading NVDA demo snapshot…" : "Load NVDA demo snapshot"}</button>
          {capturePhase === "error" && <p role="alert">The NVDA demo snapshot could not be loaded. Confirm the local API is running, then try again.</p>}
        </>
      ) : <p>Select another ticker or reload the saved snapshot after importing {ticker} evidence.</p>}
    </main>
  );
}

export default function App() {
  const [view, setView] = useState<View>("market");
  const [ticker, setTicker] = useState<Ticker>("NVDA");
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [capturePhase, setCapturePhase] = useState<"idle" | "loading" | "error">("idle");
  const [reloadVersion, setReloadVersion] = useState(0);
  const selectedTicker = useRef<Ticker>("NVDA");
  const requestVersion = useRef(0);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    const version = ++requestVersion.current;
    const nextController = new AbortController();
    controller.current = nextController;
    setState({ kind: "loading" });
    setCapturePhase("idle");

    fetchLatestSnapshot(ticker, nextController.signal)
      .then((snapshot) => {
        if (nextController.signal.aborted || version !== requestVersion.current || selectedTicker.current !== ticker) return;
        setState({ kind: "ready", snapshot });
      })
      .catch((error: unknown) => {
        if (nextController.signal.aborted || version !== requestVersion.current || selectedTicker.current !== ticker) return;
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (error instanceof MarketApiError && error.status === 404) setState({ kind: "missing", detail: error.detail });
        else setState({ kind: "error", detail: error instanceof Error ? error.message : "The market snapshot could not be loaded." });
      });
    return () => nextController.abort();
  }, [ticker, reloadVersion]);

  useEffect(() => () => {
    requestVersion.current += 1;
    controller.current?.abort();
  }, []);

  function selectTicker(nextTicker: Ticker) {
    if (nextTicker === selectedTicker.current) return;
    requestVersion.current += 1;
    controller.current?.abort();
    selectedTicker.current = nextTicker;
    setCapturePhase("idle");
    setState({ kind: "loading" });
    setTicker(nextTicker);
  }

  function reloadSnapshot() {
    requestVersion.current += 1;
    controller.current?.abort();
    setCapturePhase("idle");
    setState({ kind: "loading" });
    setReloadVersion((version) => version + 1);
  }

  async function loadDemo() {
    const version = ++requestVersion.current;
    controller.current?.abort();
    const nextController = new AbortController();
    controller.current = nextController;
    setCapturePhase("loading");
    try {
      const snapshot = await captureSnapshot("NVDA", nextController.signal);
      if (nextController.signal.aborted || version !== requestVersion.current || selectedTicker.current !== "NVDA") return;
      setState({ kind: "ready", snapshot });
      setCapturePhase("idle");
    } catch {
      if (nextController.signal.aborted || version !== requestVersion.current || selectedTicker.current !== "NVDA") return;
      setCapturePhase("error");
    }
  }

  let content;
  if (view === "saved") content = <SavedStrategies />;
  else if (state.kind === "ready") content = view === "market"
    ? <MarketSnapshotView snapshot={state.snapshot} />
    : <StrategyLab key={`${ticker}:${state.snapshot.snapshot_id}`} snapshot={state.snapshot} />;
  else if (state.kind === "loading") content = <main className="state-view" aria-busy="true"><p>Loading the latest {ticker} saved snapshot…</p></main>;
  else if (state.kind === "missing") content = <MissingMarket ticker={ticker} title={view === "lab" ? `Strategy Lab needs ${ticker} market evidence` : `No ${ticker} snapshot yet`} detail={state.detail} capturePhase={capturePhase} onCapture={ticker === "NVDA" ? () => void loadDemo() : undefined} />;
  else content = <main className="state-view"><h1>Market snapshot unavailable</h1><p>{state.detail}</p><p>Confirm the local API is running, then reload the saved snapshot.</p></main>;

  return <div className="app-shell"><AppNav view={view} onChange={setView} />{view !== "saved" && <MarketControls ticker={ticker} loading={state.kind === "loading"} onSelect={selectTicker} onReload={reloadSnapshot} />}{content}</div>;
}
