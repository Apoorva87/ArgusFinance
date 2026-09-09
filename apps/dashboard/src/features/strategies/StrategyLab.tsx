import { useEffect, useMemo, useRef, useState } from "react";
import type { MarketSnapshot, OptionQuote } from "../../api/market";
import {
  evaluateStrategy,
  saveStrategy,
  type BoundaryKind,
  type SavedStrategy,
  type StrategyBoundary,
  type StrategyDraft,
  type StrategyEvaluation,
  type StrategyLeg,
} from "../../api/strategies";
import { EvaluationPanel } from "./EvaluationPanel";

interface StrategyLabProps { snapshot: MarketSnapshot; onSaved?: (saved: SavedStrategy) => void }

function normalizedDecimal(value: string | number): string {
  const text = String(value);
  if (!text.includes(".")) return text;
  return text.replace(/0+$/, "").replace(/\.$/, "");
}

function identity(option: Pick<OptionQuote, "strike" | "option_type">): string { return `${normalizedDecimal(option.strike)}|${option.option_type}`; }

function initialLegs(snapshot: MarketSnapshot, expiration: string): StrategyLeg[] {
  const options = snapshot.options.filter((option) => option.expiration === expiration);
  const buy = options.find((option) => normalizedDecimal(option.strike) === "175" && option.option_type === "CALL");
  const sell = options.find((option) => normalizedDecimal(option.strike) === "185" && option.option_type === "CALL");
  if (buy && sell) return [
    { expiration, strike: String(buy.strike), option_type: buy.option_type, side: "BUY", quantity: 1 },
    { expiration, strike: String(sell.strike), option_type: sell.option_type, side: "SELL", quantity: 1 },
  ];
  const first = options[0];
  return first ? [{ expiration, strike: String(first.strike), option_type: first.option_type, side: "BUY", quantity: 1 }] : [];
}

function initialDraft(snapshot: MarketSnapshot): StrategyDraft {
  const expirations = [...new Set(snapshot.options.map((option) => option.expiration))].sort();
  const preferred = expirations.find((expiration) => {
    const options = snapshot.options.filter((option) => option.expiration === expiration);
    return options.some((option) => normalizedDecimal(option.strike) === "175" && option.option_type === "CALL") && options.some((option) => normalizedDecimal(option.strike) === "185" && option.option_type === "CALL");
  }) ?? expirations[0] ?? "";
  const hasCanonicalSpread = snapshot.options.some((option) => option.expiration === preferred && normalizedDecimal(option.strike) === "175" && option.option_type === "CALL")
    && snapshot.options.some((option) => option.expiration === preferred && normalizedDecimal(option.strike) === "185" && option.option_type === "CALL");
  return {
    snapshot_id: snapshot.snapshot_id,
    name: hasCanonicalSpread ? `${snapshot.underlying.ticker} 175 / 185 call spread` : `${snapshot.underlying.ticker} strategy`,
    status: "WATCH",
    thesis: "",
    pricing: "NATURAL",
    fee_per_contract: "0",
    legs: initialLegs(snapshot, preferred),
    boundaries: [],
  };
}

function message(error: unknown): string { return error instanceof Error ? error.message : "The strategy request could not be completed."; }

export function StrategyLab({ snapshot, onSaved }: StrategyLabProps) {
  const [draft, setDraft] = useState(() => initialDraft(snapshot));
  const [evaluation, setEvaluation] = useState<StrategyEvaluation | null>(null);
  const [phase, setPhase] = useState<"idle" | "evaluating" | "saving">("idle");
  const [notice, setNotice] = useState("");
  const [dirtyAfterEvaluation, setDirtyAfterEvaluation] = useState(false);
  const draftRef = useRef(draft);
  const requestVersion = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const expirations = useMemo(() => [...new Set(snapshot.options.map((option) => option.expiration))].sort(), [snapshot]);
  const expiration = draft.legs[0]?.expiration ?? expirations[0] ?? "";
  const contracts = useMemo(() => snapshot.options.filter((option) => option.expiration === expiration), [snapshot, expiration]);
  const strikes = [...new Set(contracts.map((option) => String(option.strike)))].sort((a, b) => Number(a) - Number(b));

  useEffect(() => () => controller.current?.abort(), []);

  function change(transform: (current: StrategyDraft) => StrategyDraft) {
    setDraft((current) => {
      const next = transform(current);
      draftRef.current = next;
      return next;
    });
    requestVersion.current += 1;
    controller.current?.abort();
    setDirtyAfterEvaluation((value) => value || evaluation !== null || phase === "evaluating" || phase === "saving");
    setEvaluation(null);
    setPhase("idle");
    setNotice("");
  }

  function patchLeg(index: number, patch: Partial<StrategyLeg>) {
    change((current) => ({ ...current, legs: current.legs.map((leg, legIndex) => legIndex === index ? { ...leg, ...patch } : leg) }));
  }

  async function evaluate() {
    const version = ++requestVersion.current;
    const selected = draftRef.current;
    const fingerprint = JSON.stringify(selected);
    controller.current?.abort();
    const nextController = new AbortController();
    controller.current = nextController;
    setPhase("evaluating"); setNotice(""); setDirtyAfterEvaluation(false);
    try {
      const result = await evaluateStrategy(selected, nextController.signal);
      if (version !== requestVersion.current || fingerprint !== JSON.stringify(draftRef.current)) return;
      setEvaluation(result); setPhase("idle");
    } catch (error) {
      if (nextController.signal.aborted || version !== requestVersion.current) return;
      setPhase("idle"); setNotice(message(error));
    }
  }

  async function save() {
    if (!evaluation) return;
    const version = ++requestVersion.current;
    const selected = draftRef.current;
    const fingerprint = JSON.stringify(selected);
    const nextController = new AbortController();
    controller.current = nextController;
    setPhase("saving"); setNotice("");
    try {
      const saved = await saveStrategy(selected, nextController.signal);
      if (version !== requestVersion.current || fingerprint !== JSON.stringify(draftRef.current)) return;
      setPhase("idle"); setNotice(`Saved strategy ${saved.id}.`); onSaved?.(saved);
    } catch (error) {
      if (nextController.signal.aborted || version !== requestVersion.current) return;
      setPhase("idle"); setNotice(message(error));
    }
  }

  function addBoundary() {
    const boundary: StrategyBoundary = { kind: "PRICE_BELOW", value: String(snapshot.underlying.price), note: "Review thesis" };
    change((current) => ({ ...current, boundaries: [...current.boundaries, boundary] }));
  }

  return (
    <main className="strategy-workbench">
      <header className="strategy-header">
        <div><p className="eyebrow">Snapshot-backed research</p><h1>Strategy Lab</h1></div>
        <div className="provenance-line"><span>{snapshot.underlying.ticker} · ${Number(snapshot.underlying.price).toFixed(2)}</span><span>snapshot {snapshot.snapshot_id.slice(0, 8)}…</span></div>
      </header>
      <div className="strategy-builder">
      <div className="strategy-editor"><section className="draft-panel" aria-labelledby="draft-heading">
        <div className="section-heading"><h2 id="draft-heading">Strategy draft</h2><span>1–4 contracts · shared expiration</span></div>
        <div className="draft-fields">
          <label>Name<input value={draft.name} maxLength={120} onChange={(event) => change((current) => ({ ...current, name: event.target.value }))} /></label>
          <label>Status<select value={draft.status} onChange={(event) => change((current) => ({ ...current, status: event.target.value as StrategyDraft["status"] }))}><option>WATCH</option><option>PAPER</option><option>REAL_MANUAL</option><option>SHADOW</option></select></label>
          <label>Expiration<select value={expiration} onChange={(event) => change((current) => ({ ...current, legs: initialLegs(snapshot, event.target.value) }))}>{expirations.map((value) => <option key={value}>{value}</option>)}</select></label>
          <label>Pricing<select value={draft.pricing} onChange={(event) => change((current) => ({ ...current, pricing: event.target.value as StrategyDraft["pricing"] }))}><option>NATURAL</option><option>MIDPOINT</option></select></label>
          <label>Fee per contract<input aria-label="Fee per contract" type="number" min="0" step="0.01" value={draft.fee_per_contract} onChange={(event) => change((current) => ({ ...current, fee_per_contract: event.target.value }))} /></label>
        </div>
        {draft.pricing === "MIDPOINT" && <p className="pricing-caution" role="status">Midpoint pricing is hypothetical and may not be executable.</p>}
        <div className="leg-table-wrap">
          <table className="leg-table" aria-label="Strategy legs">
            <thead><tr><th scope="col">Side</th><th scope="col">Qty</th><th scope="col">Strike</th><th scope="col">Type</th><th scope="col">Contract</th></tr></thead>
            <tbody>{draft.legs.map((leg, index) => (
              <tr key={index}>
                <td><label className="sr-only" htmlFor={`side-${index}`}>Side for leg {index + 1}</label><select id={`side-${index}`} value={leg.side} onChange={(event) => patchLeg(index, { side: event.target.value as StrategyLeg["side"] })}><option>BUY</option><option>SELL</option></select></td>
                <td><label className="sr-only" htmlFor={`quantity-${index}`}>Quantity for leg {index + 1}</label><input id={`quantity-${index}`} type="number" min="1" max="100" value={leg.quantity} onChange={(event) => patchLeg(index, { quantity: Number(event.target.value) })} /></td>
                <td><label className="sr-only" htmlFor={`strike-${index}`}>Strike for leg {index + 1}</label><select id={`strike-${index}`} value={leg.strike} onChange={(event) => patchLeg(index, { strike: event.target.value })}>{strikes.map((value) => <option key={value}>{value}</option>)}</select></td>
                <td><label className="sr-only" htmlFor={`type-${index}`}>Option type for leg {index + 1}</label><select id={`type-${index}`} value={leg.option_type} onChange={(event) => patchLeg(index, { option_type: event.target.value as StrategyLeg["option_type"] })}><option>CALL</option><option>PUT</option></select></td>
                <td><button className="quiet-button" type="button" onClick={() => change((current) => ({ ...current, legs: current.legs.filter((_, legIndex) => legIndex !== index) }))} disabled={draft.legs.length === 1}>Remove leg {index + 1}</button></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <button className="quiet-button" type="button" disabled={draft.legs.length >= 4 || contracts.length <= draft.legs.length} onClick={() => {
          const used = new Set(draft.legs.map(identity));
          const option = contracts.find((candidate) => !used.has(identity(candidate)));
          if (option) change((current) => ({ ...current, legs: [...current.legs, { expiration, strike: String(option.strike), option_type: option.option_type, side: "BUY", quantity: 1 }] }));
        }}>Add leg</button>
      </section>
      <div className="strategy-actions">
        <button className="primary-button" type="button" onClick={evaluate} disabled={phase !== "idle" || draft.legs.length === 0 || !draft.name.trim()}>{phase === "evaluating" ? "Evaluating…" : "Evaluate strategy"}</button>
        <button className="secondary-button" type="button" onClick={save} disabled={!evaluation || phase !== "idle"}>{phase === "saving" ? "Saving…" : "Save strategy"}</button>
        {dirtyAfterEvaluation && <p role="status">Inputs changed. Evaluate again before saving.</p>}
        {notice && <p role="status">{notice}</p>}
      </div></div>
      <section className="strategy-analysis" aria-label="Strategy evaluation">
        {evaluation ? <EvaluationPanel evaluation={evaluation} /> : <div className="analysis-empty"><div className="payoff-axis" aria-hidden="true"><span /><span /></div><h2>Expiration payoff</h2><p>Evaluate the selected snapshot contracts to draw the exact payoff and risk limits.</p></div>}
      </section>
      </div>
      <section className="research-notes" aria-labelledby="notes-heading">
        <div className="section-heading"><h2 id="notes-heading">Thesis and review boundaries</h2><span>Saved with original evidence</span></div>
        <label>Thesis<textarea value={draft.thesis} maxLength={4000} onChange={(event) => change((current) => ({ ...current, thesis: event.target.value }))} /></label>
        <div className="boundaries">
          {draft.boundaries.map((boundary, index) => <div className="boundary-row" key={index}>
            <label>Boundary {index + 1}<select value={boundary.kind} onChange={(event) => change((current) => ({ ...current, boundaries: current.boundaries.map((item, itemIndex) => itemIndex === index ? { ...item, kind: event.target.value as BoundaryKind, value: event.target.value === "REVIEW_DATE" ? new Date().toISOString().slice(0, 10) : String(snapshot.underlying.price) } : item) }))}><option value="PRICE_BELOW">Price below</option><option value="PRICE_ABOVE">Price above</option><option value="REVIEW_DATE">Review date</option></select></label>
            <label>Value<input type={boundary.kind === "REVIEW_DATE" ? "date" : "number"} min={boundary.kind === "REVIEW_DATE" ? undefined : "0.01"} step={boundary.kind === "REVIEW_DATE" ? undefined : "0.01"} value={boundary.value} onChange={(event) => change((current) => ({ ...current, boundaries: current.boundaries.map((item, itemIndex) => itemIndex === index ? { ...item, value: event.target.value } : item) }))} /></label>
            <label>Review note<input value={boundary.note} maxLength={500} onChange={(event) => change((current) => ({ ...current, boundaries: current.boundaries.map((item, itemIndex) => itemIndex === index ? { ...item, note: event.target.value } : item) }))} /></label>
            <button className="quiet-button" type="button" onClick={() => change((current) => ({ ...current, boundaries: current.boundaries.filter((_, itemIndex) => itemIndex !== index) }))}>Remove boundary {index + 1}</button>
          </div>)}
          <button className="quiet-button" type="button" disabled={draft.boundaries.length >= 10} onClick={addBoundary}>Add review boundary</button>
        </div>
      </section>
    </main>
  );
}
