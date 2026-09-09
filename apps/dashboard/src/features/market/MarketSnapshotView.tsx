import type { MarketSnapshot, OptionQuote } from "../../api/market";
import { ExpirationTimeline } from "./ExpirationTimeline";
import { formatPrice } from "./formatNumeric";
import { LiquidityChart } from "./LiquidityChart";

interface MarketSnapshotViewProps { snapshot: MarketSnapshot }

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

function displayAge(timestamp: string): string {
  const elapsed = Date.now() - new Date(timestamp).getTime();
  if (!Number.isFinite(elapsed)) return "Unavailable";
  const minutes = Math.max(0, Math.floor(elapsed / 60_000));
  if (minutes < 1) return "Under 1 minute";
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"}`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `${hours} hour${hours === 1 ? "" : "s"}`;
  const days = Math.floor(hours / 24);
  return `${days} days`;
}

function coverage(options: readonly OptionQuote[], available: (option: OptionQuote) => boolean): string {
  const measured = options.filter(available).length;
  if (measured === 0) return `Unavailable for all ${options.length}`;
  if (measured === options.length) return `Available for all ${options.length}`;
  return `${measured} of ${options.length} available (partial)`;
}

function optionRetrieval(options: readonly OptionQuote[]): string {
  const timestamps = [...new Set(options.map((option) => option.retrieved_at))].sort();
  if (timestamps.length === 0) return "Unavailable";
  if (timestamps.length === 1) return displayTimestamp(timestamps[0]);
  return `${displayTimestamp(timestamps[0])} to ${displayTimestamp(timestamps[timestamps.length - 1])}`;
}

export function MarketSnapshotView({ snapshot }: MarketSnapshotViewProps) {
  const { underlying } = snapshot;
  const underlyingCaution = ["DELAYED", "FROZEN", "FROZEN_DELAYED"].includes(underlying.status);
  const frozenOptionCount = snapshot.options.filter((option) => ["DELAYED", "FROZEN", "FROZEN_DELAYED"].includes(option.status)).length;
  const missingOptionTimes = snapshot.options.filter((option) => option.source_timestamp === null).length;
  const greeksUnavailable = snapshot.options.some((option) => [option.delta, option.gamma, option.theta, option.vega].some((greek) => greek === null));
  const optionStatuses = [...new Set(snapshot.options.map((option) => option.status))].join(", ");
  const cautions: string[] = [];
  if (underlyingCaution) cautions.push(`${underlying.status.toLowerCase().replace("_", "/")} underlying quote: source timestamp ${displayTimestamp(underlying.source_timestamp)}; retrieved ${displayTimestamp(underlying.retrieved_at)}.`);
  if (frozenOptionCount > 0) {
    const affected = frozenOptionCount === snapshot.options.length ? `All ${frozenOptionCount}` : `${frozenOptionCount} of ${snapshot.options.length}`;
    const noun = frozenOptionCount === 1 ? "option quote is" : "option quotes are";
    const underlyingStatus = underlying.status.toLowerCase().replace("_", "/");
    cautions.push(`${affected} ${noun} frozen/delayed; the underlying was reported ${underlyingStatus} when this snapshot was saved. Treat affected option prices as saved historical evidence.`);
  }
  if (missingOptionTimes > 0) cautions.push(missingOptionTimes === snapshot.options.length
    ? "Option bid/ask source times are unavailable. Retrieval times show when these saved quotes were collected."
    : `${missingOptionTimes} option bid/ask source times are unavailable. Retrieval times show when those saved quotes were collected.`);
  if (greeksUnavailable) cautions.push("Greeks unavailable for some or all contracts; missing values remain unfilled.");

  return (
    <main className="market-observatory">
      <header className="instrument-header">
        <p className="eyebrow">Argus / market observatory</p>
        <div className="provenance-line" aria-label="Snapshot provenance">
          <span>source {underlying.source}</span><span>{displayTimestamp(underlying.source_timestamp)}</span><strong className={`status status-${underlying.status.toLowerCase()}`}>{underlying.status}</strong>
        </div>
      </header>
      <section className="snapshot-identification" aria-labelledby="ticker-heading">
        <div><h1 id="ticker-heading">{underlying.ticker}</h1><p className="spot">${formatPrice(underlying.price)}</p></div>
        <p className="snapshot-id">Snapshot {snapshot.snapshot_id.slice(0, 8)}…</p>
      </section>
      {cautions.length > 0 && <aside className="data-cautions" role="status">{cautions.map((caution) => <p key={caution}>{caution}</p>)}</aside>}
      <ExpirationTimeline options={snapshot.options} />
      <div className="analysis-grid">
        <LiquidityChart options={snapshot.options} />
        <aside className="chain-readout" aria-labelledby="readout-heading">
          <h2 id="readout-heading">Chain readout</h2>
          <dl>
            <div><dt>Source</dt><dd>{underlying.source}</dd></div>
            <div><dt>Underlying status</dt><dd>{underlying.status}</dd></div>
            <div><dt>Option status</dt><dd>{optionStatuses || "Unavailable"}</dd></div>
            <div><dt>Underlying source time</dt><dd>{displayTimestamp(underlying.source_timestamp)}</dd></div>
            <div><dt>Underlying retrieval</dt><dd>{displayTimestamp(underlying.retrieved_at)}</dd></div>
            <div><dt>Option retrieval</dt><dd>{optionRetrieval(snapshot.options)}</dd></div>
            <div><dt>Snapshot created</dt><dd>{displayTimestamp(snapshot.created_at)}</dd></div>
            <div><dt>Snapshot age</dt><dd>{displayAge(snapshot.created_at)}</dd></div>
            <div><dt>Contracts</dt><dd>{snapshot.options.length}</dd></div>
            <div><dt>Bid/ask source time</dt><dd>{coverage(snapshot.options, (option) => option.source_timestamp !== null)}</dd></div>
            <div><dt>Open interest</dt><dd>{coverage(snapshot.options, (option) => option.open_interest !== null)}</dd></div>
            <div><dt>Volume</dt><dd>{coverage(snapshot.options, (option) => option.volume !== null)}</dd></div>
            <div><dt>Implied volatility</dt><dd>{coverage(snapshot.options, (option) => option.implied_volatility !== null)}</dd></div>
            <div><dt>Greeks</dt><dd>{coverage(snapshot.options, (option) => [option.delta, option.gamma, option.theta, option.vega].every((greek) => greek !== null))}</dd></div>
          </dl>
        </aside>
      </div>
      {(snapshot.notes?.length ?? 0) > 0 && (
        <section className="snapshot-notes" aria-labelledby="snapshot-notes-heading">
          <h2 id="snapshot-notes-heading">Snapshot notes</h2>
          <ul>{snapshot.notes?.map((note, index) => <li key={`${index}-${note}`}>{note}</li>)}</ul>
        </section>
      )}
      <footer>Saved local evidence · Missing values remain visible rather than inferred.</footer>
    </main>
  );
}
