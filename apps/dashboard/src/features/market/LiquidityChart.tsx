import Plot from "react-plotly.js";
import type { MarketSnapshot, NumericValue } from "../../api/market";

interface LiquidityChartProps {
  options: MarketSnapshot["options"];
}

interface StrikeLiquidity {
  strike: NumericValue;
  calls: number;
  puts: number;
}

function numericValue(value: NumericValue): number {
  return Number(value);
}

export function liquidityByStrike(options: MarketSnapshot["options"]): StrikeLiquidity[] {
  const grouped = new Map<string, StrikeLiquidity>();
  for (const option of options) {
    const key = String(option.strike);
    const existing = grouped.get(key) ?? { strike: option.strike, calls: 0, puts: 0 };
    if (option.option_type === "CALL") existing.calls += option.open_interest;
    else existing.puts += option.open_interest;
    grouped.set(key, existing);
  }
  return [...grouped.values()].sort((left, right) => numericValue(left.strike) - numericValue(right.strike));
}

export function LiquidityChart({ options }: LiquidityChartProps) {
  const rows = liquidityByStrike(options);
  const strikes = rows.map((row) => String(row.strike));

  return (
    <section className="liquidity-section" aria-labelledby="liquidity-heading">
      <div className="section-heading">
        <h2 id="liquidity-heading">Liquidity by strike</h2>
        <span>Open interest · all listed expirations</span>
      </div>
      <div className="plot-frame" aria-label="Grouped bar chart of call and put open interest by strike">
        <Plot
          data={[
            { type: "bar", name: "Calls", x: strikes, y: rows.map((row) => row.calls), marker: { color: "#4fd1c5" } },
            { type: "bar", name: "Puts", x: strikes, y: rows.map((row) => row.puts), marker: { color: "#f4b942" } },
          ]}
          layout={{
            barmode: "group",
            autosize: true,
            margin: { l: 52, r: 12, t: 16, b: 44 },
            paper_bgcolor: "#0f2233",
            plot_bgcolor: "#0f2233",
            font: { color: "#d9e7ef", family: "SFMono-Regular, Consolas, monospace" },
            xaxis: { title: { text: "Strike" }, gridcolor: "#19364b", linecolor: "#8097a8" },
            yaxis: { title: { text: "Open interest" }, gridcolor: "#19364b", linecolor: "#8097a8", rangemode: "tozero" },
            legend: { orientation: "h", y: 1.12 },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%", height: "330px" }}
          useResizeHandler
        />
      </div>
      <div className="table-wrap">
        <table aria-label="Open interest by strike">
          <caption>Text alternative: open interest summed across all listed expirations.</caption>
          <thead>
            <tr><th scope="col">Strike</th><th scope="col">Calls</th><th scope="col">Puts</th></tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={String(row.strike)}><th scope="row">{row.strike}</th><td>{row.calls.toLocaleString()}</td><td>{row.puts.toLocaleString()}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
