/** @format */

import { useEffect, useMemo, useState } from "react";
import {
  c3ModelReviewApi,
  type ActiveAssignment,
  type ModelCandidate,
} from "../api/c3ModelReviewApi";
import "../styles/c3ModelEvaluation.css";

const HORIZONS = [15, 30, 60] as const;
const metric = (n: number | null) =>
  typeof n === "number" && Number.isFinite(n) ? n.toFixed(4) : "—";

export function C3ModelEvaluation() {
  const [candidates, setCandidates] = useState<ModelCandidate[]>([]);
  const [active, setActive] = useState<ActiveAssignment[]>([]);
  const [history, setHistory] = useState<Record<string, unknown>[]>([]);
  const [horizon, setHorizon] = useState<number>(15);
  const [dataset, setDataset] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    Promise.all([
      c3ModelReviewApi.candidates(controller.signal),
      c3ModelReviewApi.active(controller.signal),
      c3ModelReviewApi.history(controller.signal),
    ])
      .then(([c, a, h]) => {
        if (controller.signal.aborted) return;
        setCandidates(c.candidates);
        setActive(a.assignments);
        setHistory(h.events);
      })
      .catch((e: unknown) => {
        if (!controller.signal.aborted)
          setError(e instanceof Error ? e.message : "Model review unavailable");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [reload]);
  const datasets = useMemo(
    () => [...new Set(candidates.map((c) => c.dataset_id))],
    [candidates],
  );
  const rows = useMemo(
    () =>
      candidates
        .filter(
          (c) =>
            c.horizon_minutes === horizon &&
            (!dataset || c.dataset_id === dataset),
        )
        .sort(
          (a, b) =>
            (a.validation_mae ?? Infinity) - (b.validation_mae ?? Infinity) ||
            (a.validation_rmse ?? Infinity) - (b.validation_rmse ?? Infinity),
        ),
    [candidates, horizon, dataset],
  );
  const assigned = active.find((a) => a.horizon_minutes === horizon);
  return (
    <div className="c3-model-review">
      <div className="c3-model-review-head">
        <div>
          <span className="c3-model-review-eyebrow">
            MODEL REGISTRY / READ-ONLY REVIEW
          </span>
          <h3>Validation &amp; active models</h3>
          <p>
            Compare registered candidates using validation metrics. Activation
            is a separate controlled backend operation.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setReload((n) => n + 1)}
          disabled={loading}>
          {loading ? "Loading…" : "Refresh results"}
        </button>
      </div>
      {error && (
        <div className="c3-model-review-error" role="alert">
          {error}. Check the C3 API and install the read-only model routes.
        </div>
      )}
      <div className="c3-model-review-overview">
        <div>
          <small>Registered candidates</small>
          <strong>{loading ? "—" : candidates.length}</strong>
        </div>
        <div>
          <small>Active horizons</small>
          <strong>{loading ? "—" : `${active.length} / 3`}</strong>
        </div>
        <div>
          <small>Activation events</small>
          <strong>{loading ? "—" : history.length}</strong>
        </div>
      </div>
      <section className="c3-model-review-panel">
        <div className="c3-model-review-toolbar">
          <div>
            <h4>Candidate comparison</h4>
            <p>Lower validation MAE is better. RMSE breaks ties.</p>
          </div>
          <label>
            Dataset{" "}
            <select
              value={dataset}
              onChange={(e) => setDataset(e.target.value)}>
              <option value="">All datasets</option>
              {datasets.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div
          className="c3-model-review-horizons"
          role="group"
          aria-label="Forecast horizon">
          {HORIZONS.map((h) => (
            <button
              type="button"
              key={h}
              className={h === horizon ? "selected" : ""}
              aria-pressed={h === horizon}
              onClick={() => setHorizon(h)}>
              {h} min
            </button>
          ))}
        </div>
        <div className="c3-model-review-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Model</th>
                <th>Validation MAE</th>
                <th>Validation RMSE</th>
                <th>Registry status</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c, i) => (
                <tr key={c.model_version_id}>
                  <td>
                    <strong>{c.model_name}</strong>
                    <small>{c.model_version_id}</small>
                    {i === 0 && (
                      <em>Lowest validation MAE in current filter</em>
                    )}
                  </td>
                  <td>{metric(c.validation_mae)}</td>
                  <td>{metric(c.validation_rmse)}</td>
                  <td>{c.status}</td>
                  <td>
                    {assigned?.model_version_id === c.model_version_id
                      ? "Active"
                      : "—"}
                  </td>
                </tr>
              ))}
              {!rows.length && (
                <tr>
                  <td colSpan={5}>
                    No candidates available for this selection.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      <section className="c3-model-review-panel">
        <h4>Active checkpoint assignments</h4>
        <p>These are actual database assignments, not inferred winners.</p>
        <div className="c3-model-review-assignments">
          {HORIZONS.map((h) => {
            const a = active.find((x) => x.horizon_minutes === h);
            return (
              <div key={h}>
                <span>{h} MINUTE HORIZON</span>
                <strong>{a?.model_name ?? "Unassigned"}</strong>
                <small>
                  {a ? a.model_version_id : "No active model in registry"}
                </small>
              </div>
            );
          })}
        </div>
      </section>
      <div className="c3-model-review-boundary">
        <strong>Research integrity</strong>
        <p>
          Validation metrics are used for candidate comparison. Held-out test
          results must remain outside model selection. A registered or
          lowest-error candidate is not automatically active. This screen cannot
          activate or roll back models.
        </p>
      </div>
    </div>
  );
}
