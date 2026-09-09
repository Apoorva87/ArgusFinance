import { useCallback, useEffect, useRef, useState } from "react";
import { getStrategy, listStrategies, type SavedStrategy } from "../../api/strategies";
import { EvaluationPanel } from "./EvaluationPanel";

type ListState =
  | { kind: "loading" }
  | { kind: "error"; detail: string }
  | { kind: "ready"; strategies: SavedStrategy[] };

function detail(error: unknown): string { return error instanceof Error ? error.message : "Saved strategies could not be loaded."; }
function date(value: string): string { return new Intl.DateTimeFormat("en-CA", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(value)); }

export function SavedStrategies() {
  const [state, setState] = useState<ListState>({ kind: "loading" });
  const [selected, setSelected] = useState<SavedStrategy | null>(null);
  const [detailState, setDetailState] = useState<"idle" | "loading">("idle");
  const [detailError, setDetailError] = useState("");
  const listController = useRef<AbortController | null>(null);
  const detailController = useRef<AbortController | null>(null);

  const load = useCallback(async () => {
    listController.current?.abort();
    const controller = new AbortController(); listController.current = controller;
    setState({ kind: "loading" });
    try {
      const strategies = await listStrategies(controller.signal);
      if (!controller.signal.aborted) setState({ kind: "ready", strategies });
    }
    catch (error) { if (!controller.signal.aborted) setState({ kind: "error", detail: detail(error) }); }
  }, []);

  useEffect(() => {
    void load();
    return () => { listController.current?.abort(); detailController.current?.abort(); };
  }, [load]);

  async function open(id: string) {
    detailController.current?.abort();
    const controller = new AbortController(); detailController.current = controller;
    setSelected(null); setDetailState("loading"); setDetailError("");
    try {
      const strategy = await getStrategy(id, controller.signal);
      if (!controller.signal.aborted) { setSelected(strategy); setDetailState("idle"); }
    }
    catch (error) { if (!controller.signal.aborted) { setDetailState("idle"); setDetailError(detail(error)); } }
  }

  return (
    <main className="saved-workbench">
      <header className="strategy-header"><div><p className="eyebrow">Immutable entry evidence</p><h1>Saved Strategies</h1></div></header>
      {state.kind === "loading" && <section className="inline-state" aria-busy="true">Loading saved strategies…</section>}
      {state.kind === "error" && <section className="inline-state"><h2>Saved strategies unavailable</h2><p role="alert">{state.detail}</p><button className="primary-button" type="button" onClick={() => void load()}>Retry saved strategies</button></section>}
      {state.kind === "ready" && state.strategies.length === 0 && <section className="inline-state"><h2>No saved strategies</h2><p>Evaluate and save a snapshot-backed strategy to preserve its entry evidence here.</p></section>}
      {state.kind === "ready" && state.strategies.length > 0 && (
        <div className="saved-layout">
          <aside className="saved-index" aria-label="Saved strategy list">
            {state.strategies.map((strategy) => (
              <button type="button" key={strategy.id} onClick={() => void open(strategy.id)} aria-label={`Open ${strategy.draft.name}`} className={selected?.id === strategy.id ? "selected" : ""}>
                <strong>{strategy.draft.name}</strong><span>{strategy.draft.status} · {strategy.evaluation.ticker}</span><time dateTime={strategy.created_at}>{date(strategy.created_at)} UTC</time>
              </button>
            ))}
          </aside>
          <section className="saved-detail" aria-live="polite">
            {detailState === "loading" && <p aria-busy="true">Opening original evaluation…</p>}
            {detailError && <p className="detail-error" role="alert">{detailError}</p>}
            {!selected && detailState === "idle" && !detailError && <div className="saved-prompt"><h2>Select a saved strategy</h2><p>Open an entry to review the evidence recorded when it was saved.</p></div>}
            {selected && <>
              <header className="saved-detail-header"><div><h2>{selected.draft.name}</h2><p className="saved-status">{selected.draft.status}</p></div><p>{selected.draft.thesis || "No thesis recorded."}</p></header>
              {selected.draft.boundaries.length > 0 && <section className="saved-boundaries" aria-labelledby="saved-boundaries-heading"><h3 id="saved-boundaries-heading">Review boundaries</h3><ul>{selected.draft.boundaries.map((boundary, index) => <li key={`${boundary.kind}-${index}`}><strong>{boundary.kind.replace("_", " ")}: {boundary.value}</strong><span>{boundary.note}</span></li>)}</ul></section>}
              <EvaluationPanel evaluation={selected.evaluation} savedAt={selected.created_at} />
            </>}
          </section>
        </div>
      )}
    </main>
  );
}
