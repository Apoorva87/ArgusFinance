import Plot from "react-plotly.js";
import type { StrategyEvaluation } from "../../api/strategies";

interface PayoffChartProps { evaluation: StrategyEvaluation }

function money(value: string): string {
  return Number(value).toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
}

export function PayoffChart({ evaluation }: PayoffChartProps) {
  const priceBoundaries = evaluation.boundaries.filter((boundary) => boundary.kind !== "REVIEW_DATE");
  const annotations = [
    { x: Number(evaluation.spot), text: `Spot ${money(evaluation.spot)}`, color: "#d9e7ef" },
    ...evaluation.breakevens.map((value) => ({ x: Number(value), text: `Break-even ${money(value)}`, color: "#4fd1c5" })),
    ...priceBoundaries.map((boundary) => ({ x: Number(boundary.value), text: `${boundary.kind === "PRICE_BELOW" ? "Below" : "Above"} ${money(boundary.value)}`, color: "#f4b942" })),
  ];

  return (
    <section className="payoff-section" aria-labelledby="payoff-heading">
      <div className="section-heading">
        <h2 id="payoff-heading">Expiration payoff</h2>
        <span>Backend-calculated · one contract = 100 shares</span>
      </div>
      <div className="plot-frame" aria-label="Expiration payoff chart">
        <Plot
          data={[{
            type: "scatter",
            mode: "lines+markers",
            x: evaluation.payoff_points.map((point) => Number(point.spot)),
            y: evaluation.payoff_points.map((point) => Number(point.pnl)),
            line: { color: "#4fd1c5", width: 3 },
            marker: { color: evaluation.payoff_points.map((point) => Number(point.pnl) < 0 ? "#db6b72" : "#4fd1c5"), size: 6 },
            hovertemplate: "$%{x:.2f}<br>P/L $%{y:.2f}<extra></extra>",
          }]}
          layout={{
            autosize: true,
            margin: { l: 64, r: 22, t: 24, b: 52 },
            paper_bgcolor: "#0f2233",
            plot_bgcolor: "#0f2233",
            font: { color: "#d9e7ef", family: "SFMono-Regular, Consolas, monospace" },
            xaxis: { title: { text: "Underlying price at expiration ($)" }, gridcolor: "#19364b", zerolinecolor: "#8097a8" },
            yaxis: { title: { text: "Profit / loss ($)" }, gridcolor: "#19364b", zerolinecolor: "#8097a8" },
            showlegend: false,
            shapes: annotations.map((annotation) => ({ type: "line", x0: annotation.x, x1: annotation.x, y0: 0, y1: 1, yref: "paper", line: { color: annotation.color, width: 1, dash: "dot" } })),
            annotations: annotations.map((annotation, index) => ({ x: annotation.x, y: 1, yref: "paper", text: annotation.text, showarrow: false, textangle: -90, yanchor: "bottom", xshift: index * 3, font: { color: annotation.color, size: 10 } })),
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%", height: "430px" }}
          useResizeHandler
        />
      </div>
      <div className="table-wrap scenario-table">
        <table aria-label="Expiration payoff scenarios">
          <caption>Text alternative: every backend payoff point used by the chart.</caption>
          <thead><tr><th scope="col">Underlying at expiration</th><th scope="col">Profit / loss</th></tr></thead>
          <tbody>{evaluation.payoff_points.map((point, index) => (
            <tr key={`${point.spot}-${index}`}><td>{money(point.spot)}</td><td className={Number(point.pnl) < 0 ? "loss" : "profit"}>{money(point.pnl)}</td></tr>
          ))}</tbody>
        </table>
      </div>
    </section>
  );
}
