import { WarnIcon } from "./icons";
import type { Connection, PredictResponse } from "../types";

interface Props {
  response: PredictResponse | null;
  running: boolean;
  error: string | null;
  problems: string[];
  connection: Connection;
  classOrderVerified: boolean | null;
}

const LABEL_TEXT: Record<string, string> = {
  CLEAN: "Clean reading",
  ANOMALY: "Anomaly (sensor fault)",
  VALID_EVENT: "Valid environmental event",
};

export function ResultPanel({ response, running, error, problems, connection, classOrderVerified }: Props) {
  const first = response?.results[0];
  const sorted = first ? Object.entries(first.probabilities).sort((a, b) => b[1] - a[1]) : [];

  return (
    <section className="c1-card">
      <header className="c1-card__head">
        <div>
          <span className="c1-eyebrow">02 / Result</span>
          <h2>Credibility prediction</h2>
          <p>Label, confidence and class probabilities from the trained XGBoost model.</p>
        </div>
      </header>

      {classOrderVerified === false && (
        <div className="c1-inline-warn">
          <WarnIcon /> Class order is not confirmed. Add a <code>classes</code> list to the model meta file before trusting these labels.
        </div>
      )}
      {problems.length > 0 && (
        <div className="c1-inline-error" role="alert">
          {problems.map((p) => <div key={p}>{p}</div>)}
        </div>
      )}
      {error && <div className="c1-inline-error" role="alert">{error}</div>}

      {!first && !error && (
        <div className="c1-empty">
          {connection === "offline"
            ? "The C1 API is offline. Start it on port 8033, then run a prediction."
            : running ? "Waiting for the model…" : "Pick a preset or edit the signals, then run a prediction."}
        </div>
      )}

      {first && (
        <div className="c1-result">
          <div className={`c1-badge c1-badge--${first.label}`}>
            <span>{LABEL_TEXT[first.label] ?? first.label}</span>
            <strong>{(first.confidence * 100).toFixed(1)}%</strong>
          </div>

          <div className="c1-bars">
            {sorted.map(([label, prob]) => (
              <div key={label} className="c1-bar">
                <div className="c1-bar__row"><span>{label}</span><span>{(prob * 100).toFixed(1)}%</span></div>
                <div className="c1-bar__track"><div className={`c1-bar__fill c1-bar__fill--${label}`} style={{ width: `${prob * 100}%` }} /></div>
              </div>
            ))}
          </div>

          <dl className="c1-facts">
            <div><dt>Model</dt><dd>{response?.model_version}</dd></div>
            <div><dt>Latency</dt><dd>{response?.latency_ms} ms</dd></div>
            <div><dt>Rows scored</dt><dd>{response?.count}</dd></div>
            <div><dt>Missing features</dt><dd>{first.missing_features.length}</dd></div>
          </dl>

          {response && response.count > 1 && (
            <div className="c1-batch">
              <h3>Batch result</h3>
              <ul>
                {response.results.map((r, i) => (
                  <li key={i}><span>Row {i + 1}</span><span className={`c1-tag c1-tag--${r.label}`}>{r.label}</span><span>{(r.confidence * 100).toFixed(1)}%</span></li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
