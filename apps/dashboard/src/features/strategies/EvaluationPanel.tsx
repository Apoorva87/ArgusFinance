import type { StrategyEvaluation } from "../../api/strategies";
import { PayoffChart } from "./PayoffChart";

interface EvaluationPanelProps { evaluation: StrategyEvaluation; savedAt?: string }

function money(value: string | null): string {
  if (value === null) return "Unlimited";
  return Number(value).toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
}

function timestamp(value: string): string {
  return new Intl.DateTimeFormat("en-CA", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(value));
}

export function EvaluationPanel({ evaluation, savedAt }: EvaluationPanelProps) {
  const greeks = [
    ["Delta (share-equivalent)", evaluation.net_greeks.delta],
    ["Gamma (delta / $1 move)", evaluation.net_greeks.gamma],
    ["Theta ($ / day)", evaluation.net_greeks.theta],
    ["Vega ($ / volatility point)", evaluation.net_greeks.vega],
  ] as const;
  return (
    <div className="evaluation-panel">
      <div className="evidence-strip" aria-label="Evaluation provenance">
        <span>Source {evaluation.source_status}</span>
        <span>{timestamp(evaluation.source_timestamp)} UTC</span>
        <span>{evaluation.analytics_version}</span>
        {savedAt && <span>Saved {timestamp(savedAt)} UTC</span>}
      </div>
      {evaluation.warnings.map((warning) => <aside className="strategy-warning" role="status" key={warning}>{warning}</aside>)}
      <div className="strategy-results-grid">
        <PayoffChart evaluation={evaluation} />
        <aside className="risk-readout" aria-labelledby="risk-heading">
          <h2 id="risk-heading">Risk at expiration</h2>
          <dl>
            <div><dt>Net entry debit / credit (including fees)</dt><dd>{money(evaluation.net_debit)}</dd></div>
            <div><dt>Entry fees</dt><dd>{money(evaluation.entry_fees)}</dd></div>
            <div><dt>Maximum profit</dt><dd className="profit">{money(evaluation.maximum_profit)}</dd></div>
            <div><dt>Maximum loss</dt><dd className="loss">{money(evaluation.maximum_loss)}</dd></div>
            <div><dt>Break-even{evaluation.breakevens.length === 1 ? "" : "s"}</dt><dd>{evaluation.breakevens.length ? evaluation.breakevens.map(money).join(", ") : "None isolated"}</dd></div>
          </dl>
          <h3>Quoted net Greeks</h3>
          <dl>{greeks.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value ?? "Unavailable"}</dd></div>)}</dl>
          <p className="eligibility-note">{evaluation.eligible ? "Structurally eligible for research." : "Not eligible for research."} This is not an investment ranking.</p>
        </aside>
      </div>
    </div>
  );
}
