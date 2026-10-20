import type { RecentPrediction } from "../types";

interface Props {
  rows: RecentPrediction[];
  offline: boolean;
}

const num = (v: number | null | undefined, digits = 1) => (v === null || v === undefined ? "–" : v.toFixed(digits));

export function RecentTable({ rows, offline }: Props) {
  const mock = rows.length > 0 && rows.every((r) => r.source === "mock");
  return (
    <section className="c1-card">
      <header className="c1-card__head">
        <div>
          <span className="c1-eyebrow">03 / History</span>
          <h2>Latest predictions</h2>
          <p>{mock ? "The API is not reachable, these rows are mock data." : "Most recent predictions served by the C1 API."}</p>
        </div>
        {mock && <span className="c1-pill c1-pill--amber">{offline ? "Mock data" : "Sample rows"}</span>}
      </header>

      {rows.length === 0 ? (
        <div className="c1-empty">No predictions yet. Run one above.</div>
      ) : (
        <div className="c1-table-wrap">
          <table className="c1-table">
            <thead>
              <tr>
                <th>Time</th><th>Label</th><th>Confidence</th><th>Soil moisture</th><th>Rain 1 h</th><th>Neighbours</th><th>Source</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{new Date(r.timestamp).toLocaleTimeString()}</td>
                  <td><span className={`c1-tag c1-tag--${r.label}`}>{r.label}</span></td>
                  <td>{(r.confidence * 100).toFixed(1)}%</td>
                  <td>{num(r.input.value)}</td>
                  <td>{num(r.input.rain_1h_mm)} mm</td>
                  <td>{num(r.input.n_neighbours_fresh, 0)}</td>
                  <td>{r.source === "mock" ? "mock" : "API"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
