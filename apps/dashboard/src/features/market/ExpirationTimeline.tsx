import type { MarketSnapshot } from "../../api/market";

interface ExpirationTimelineProps {
  options: MarketSnapshot["options"];
}

const expirationFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

export function ExpirationTimeline({ options }: ExpirationTimelineProps) {
  const expirations = [...new Set(options.map((option) => option.expiration))].sort();

  return (
    <section className="expiration-horizon" aria-labelledby="expiration-heading">
      <div className="section-heading">
        <h2 id="expiration-heading">Expiration horizon</h2>
        <span>{expirations.length} dates available</span>
      </div>
      <ol className="expiration-rail" aria-label="Available option expirations">
        {expirations.map((expiration) => (
          <li key={expiration}>
            <time dateTime={expiration}>{expirationFormatter.format(new Date(`${expiration}T00:00:00Z`))}</time>
          </li>
        ))}
      </ol>
    </section>
  );
}
