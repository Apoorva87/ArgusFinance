import type { MarketSnapshot } from "../../api/market";
import { ExpirationTimeline } from "./ExpirationTimeline";
import { LiquidityChart } from "./LiquidityChart";

interface MarketSnapshotViewProps {
  snapshot: MarketSnapshot;
}

const timestampFormatter = new Intl.DateTimeFormat("en-CA", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: "UTC",
  timeZoneName: "short",
});

function displayTimestamp(timestamp: string): string {
  return timestampFormatter.format(new Date(timestamp)).replace(",", "");
}

function hasUnavailableGreeks(snapshot: MarketSnapshot): boolean {
  return snapshot.underlying.status === "UNAVAILABLE" || snapshot.options.some((option) =>
    option.status === "UNAVAILABLE" || [option.delta, option.gamma, option.theta, option.vega].some((greek) => greek === null),
  );
}

export function MarketSnapshotView({ snapshot }: MarketSnapshotViewProps) {
  const { underlying } = snapshot;
  const caution = underlying.status === "DELAYED" || underlying.status === "FROZEN";
  const greeksUnavailable = hasUnavailableGreeks(snapshot);

  return (
    <main className="market-observatory">
      <header className="instrument-header">
        <p className="eyebrow">Argus / market observatory</p>
        <div className="provenance-line" aria-label="Snapshot provenance">
          <span>source {underlying.source}</span><span>{displayTimestamp(underlying.source_timestamp)}</span><strong className={`status status-${underlying.status.toLowerCase()}`}>{underlying.status}</strong>
        </div>
      </header>
      <section className="snapshot-identification" aria-labelledby="ticker-heading">
        <div>
          <h1 id="ticker-heading">{underlying.ticker}</h1>
          <p className="spot">${underlying.price}</p>
        </div>
        <p className="snapshot-id">Snapshot {snapshot.snapshot_id.slice(0, 8)}…</p>
      </section>
      {caution && (
        <aside className="data-caution" role="status">
          {underlying.status.toLowerCase()} data: source timestamp {displayTimestamp(underlying.source_timestamp)}; retrieved {displayTimestamp(underlying.retrieved_at)}.
        </aside>
      )}
      {greeksUnavailable && <aside className="greeks-unavailable" role="status">Greeks unavailable — the source did not provide values for this snapshot.</aside>}
      <ExpirationTimeline options={snapshot.options} />
      <div className="analysis-grid">
        <LiquidityChart options={snapshot.options} />
        <aside className="chain-readout" aria-labelledby="readout-heading">
          <h2 id="readout-heading">Chain readout</h2>
          <dl>
            <div><dt>Source</dt><dd>{underlying.source}</dd></div>
            <div><dt>Source timestamp</dt><dd>{displayTimestamp(underlying.source_timestamp)}</dd></div>
            <div><dt>Retrieved</dt><dd>{displayTimestamp(underlying.retrieved_at)}</dd></div>
            <div><dt>Snapshot created</dt><dd>{displayTimestamp(snapshot.created_at)}</dd></div>
            <div><dt>Contracts</dt><dd>{snapshot.options.length}</dd></div>
          </dl>
        </aside>
      </div>
      <footer>Local evidence only · Missing values remain visible rather than inferred.</footer>
    </main>
  );
}
