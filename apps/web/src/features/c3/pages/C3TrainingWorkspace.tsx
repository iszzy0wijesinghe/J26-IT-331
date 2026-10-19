/** @format */

import { C3TrainingMonitor } from "./C3TrainingMonitor";
import { useCallback, useEffect, useMemo, useState } from "react";
import { c3GoldenApi, type C3GoldenDataset } from "../api/c3Api";
import { c3TrainingApi, type C3TrainingRecord } from "../api/c3TrainingApi";
import "../styles/c3TrainingWorkspace.css";

type Row = Record<string, unknown>;
const object = (v: unknown): Row =>
  v !== null && typeof v === "object" && !Array.isArray(v) ? (v as Row) : {};
const value = (v: unknown): string =>
  v === null || v === undefined
    ? "—"
    : typeof v === "object"
      ? JSON.stringify(v)
      : String(v);
const first = (r: Row, keys: string[]): unknown =>
  keys.map((k) => r[k]).find((v) => v !== undefined && v !== null);
const jobId = (r: Row) => value(first(r, ["job_id", "id", "training_job_id"]));
const jobStatus = (r: Row) =>
  value(first(r, ["status", "state", "job_status"]));
const datasetId = (r: Row) =>
  value(first(r, ["dataset_id", "source_dataset_id"]));
const jobList = (v: unknown): Row[] => {
  if (Array.isArray(v)) return v.map(object);
  const r = object(v);
  const list = first(r, ["jobs", "training_jobs", "items", "results"]);
  return Array.isArray(list) ? list.map(object) : [];
};
const stateTone = (s: string) =>
  /fail|error|cancel/i.test(s)
    ? "error"
    : /complete|success|finish|ready/i.test(s)
      ? "success"
      : /run|progress|queue|pending/i.test(s)
        ? "active"
        : "neutral";
const isReady = (r: Row | null): boolean | null => {
  if (!r) return null;
  const v = first(r, [
    "training_approved",
    "ready",
    "is_ready",
    "training_ready",
    "can_train",
    "eligible",
  ]);
  return typeof v === "boolean" ? v : null;
};
const compactFields = (r: Row, exclude: string[] = []) =>
  Object.entries(r)
    .filter(
      ([k, v]) => !exclude.includes(k) && (typeof v !== "object" || v === null),
    )
    .slice(0, 14);

export function C3TrainingWorkspace() {
  const [datasets, setDatasets] = useState<C3GoldenDataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState("");
  const [readiness, setReadiness] = useState<C3TrainingRecord | null>(null);
  const [jobs, setJobs] = useState<Row[]>([]);
  const [selectedJob, setSelectedJob] = useState("");
  const [details, setDetails] = useState<C3TrainingRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [starting, setStarting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    setRefreshing(true);
    try {
      const [ds, js] = await Promise.all([
        c3GoldenApi.list(signal),
        c3TrainingApi.jobs(signal),
      ]);
      if (signal?.aborted) return;
      setDatasets(ds.datasets);
      setSelectedDataset(
        (current) => current || ds.datasets[0]?.dataset_id || "",
      );
      const items = jobList(js);
      setJobs(items);
      setSelectedJob(
        (current) => current || (items.length ? jobId(items[0]) : ""),
      );
      setError("");
    } catch (e) {
      if (!signal?.aborted)
        setError(
          e instanceof Error ? e.message : "Unable to load training workspace.",
        );
    } finally {
      if (!signal?.aborted) {
        setRefreshing(false);
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    const ctrl = new AbortController();
    void refresh(ctrl.signal);
    return () => ctrl.abort();
  }, [refresh]);
  useEffect(() => {
    if (!selectedDataset) {
      setReadiness(null);
      return;
    }
    const ctrl = new AbortController();
    setChecking(true);
    setReadiness(null);
    void c3TrainingApi
      .readiness(selectedDataset, ctrl.signal)
      .then(setReadiness)
      .catch((e) => {
        if (!ctrl.signal.aborted)
          setError(e instanceof Error ? e.message : "Readiness check failed.");
      })
      .finally(() => {
        if (!ctrl.signal.aborted) setChecking(false);
      });
    return () => ctrl.abort();
  }, [selectedDataset]);
  useEffect(() => {
    if (!selectedJob || selectedJob === "—") {
      setDetails(null);
      return;
    }
    const ctrl = new AbortController();
    void c3TrainingApi
      .job(selectedJob, ctrl.signal)
      .then(setDetails)
      .catch((e) => {
        if (!ctrl.signal.aborted)
          setError(e instanceof Error ? e.message : "Unable to load job.");
      });
    return () => ctrl.abort();
  }, [selectedJob]);

  const selectedDatasetInfo = useMemo(
    () => datasets.find((d) => d.dataset_id === selectedDataset),
    [datasets, selectedDataset],
  );
  const selectedJobSummary = jobs.find((j) => jobId(j) === selectedJob);
  const ready = isReady(readiness);
  const readinessFields = readiness ? compactFields(readiness) : [];
  const temporalReady = readiness?.temporal_ready === true;
  const result = object(details);
  const resultFields = compactFields(result, [
    "job_id",
    "id",
    "dataset_id",
    "status",
  ]);

  async function startTraining() {
    if (!selectedDataset || starting || ready !== true) return;
    if (!window.confirm(`Start a training job for dataset ${selectedDataset}?`))
      return;
    setStarting(true);
    setError("");
    setNotice("");
    try {
      const created = await c3TrainingApi.start(selectedDataset);
      const id = jobId(created);
      setNotice(
        id !== "—"
          ? `Training job ${id} submitted; automatic worker launch requested.`
          : "Training request submitted. Refresh jobs to view progress.",
      );
      await refresh();
      if (id !== "—") setSelectedJob(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to start training.");
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="c3-training" aria-label="C3 model training workspace">
      <div className="c3-training-topline">
        <div>
          <span className="c3-training-eyebrow">TRAINING PIPELINE</span>
          <h3>Experiment control</h3>
          <p>
            Review dataset readiness, launch an authorized training run, and
            inspect verified model results.
          </p>
        </div>
        <button
          className="c3-training-secondary"
          type="button"
          onClick={() => void refresh()}
          disabled={refreshing}>
          {refreshing ? "Refreshing…" : "↻ Refresh jobs"}
        </button>
      </div>
      {error && (
        <div className="c3-training-alert error" role="alert">
          {error}
          <button
            type="button"
            onClick={() => setError("")}
            aria-label="Dismiss error">
            ×
          </button>
        </div>
      )}
      {notice && (
        <div className="c3-training-alert success" role="status">
          {notice}
        </div>
      )}
      <div className="c3-training-columns">
        <section className="c3-training-card c3-training-setup">
          <div className="c3-training-section-heading">
            <span className="c3-training-step">01</span>
            <div>
              <h4>Choose research dataset</h4>
              <p>Validated, registered research datasets</p>
            </div>
          </div>
          <label className="c3-training-label" htmlFor="c3-train-dataset">
            Dataset
          </label>
          <select
            id="c3-train-dataset"
            value={selectedDataset}
            onChange={(e) => setSelectedDataset(e.target.value)}
            disabled={loading || !datasets.length}>
            <option value="">
              {loading ? "Loading datasets…" : "Select dataset"}
            </option>
            {datasets.map((d) => (
              <option key={d.dataset_id} value={d.dataset_id}>
                {d.filename || d.dataset_id} · {d.dataset_id}
              </option>
            ))}
          </select>
          {selectedDatasetInfo && (
            <div className="c3-training-metrics">
              <div>
                <strong>
                  {selectedDatasetInfo.total_rows.toLocaleString()}
                </strong>
                <span>Observations</span>
              </div>
              <div>
                <strong>{selectedDatasetInfo.device_count}</strong>
                <span>Devices</span>
              </div>
              <div>
                <strong>{selectedDatasetInfo.episode_count}</strong>
                <span>Episodes</span>
              </div>
            </div>
          )}
          <div className="c3-training-divider" />
          <div className="c3-training-section-heading">
            <span className="c3-training-step">02</span>
            <div>
              <h4>Training readiness</h4>
              <p>Server-side eligibility assessment</p>
            </div>
          </div>
          <div
            className={`c3-training-readiness ${ready === true ? "success" : ready === false ? "error" : "neutral"}`}>
            <span className="c3-training-indicator" />
            <strong>
              {checking
                ? "Checking dataset…"
                : ready === true
                  ? "Ready to train"
                  : ready === false
                    ? "Research approval not granted"
                    : readiness
                      ? "Review assessment"
                      : "Choose a dataset"}
            </strong>
          </div>
          {readiness && (
            <p className="c3-training-footnote">
              Temporal suitability:{" "}
              <strong>{temporalReady ? "PASS" : "NOT VERIFIED"}</strong>.
              Research approval:{" "}
              <strong>{ready === true ? "APPROVED" : "NOT APPROVED"}</strong>.{" "}
              {typeof readiness.training_approval_reason === "string"
                ? readiness.training_approval_reason
                : ""}
            </p>
          )}
          <button
            className="c3-training-secondary c3-training-advanced-toggle"
            type="button"
            onClick={() => setShowAdvanced((v) => !v)}
            aria-expanded={showAdvanced}>
            {showAdvanced ? "Hide technical details" : "Show technical details"}
          </button>
          {showAdvanced && readiness && (
            <dl className="c3-training-keyvalues">
              {readinessFields.map(([k, v]) => (
                <div key={k}>
                  <dt>{k.replace(/_/g, " ")}</dt>
                  <dd>{value(v)}</dd>
                </div>
              ))}
            </dl>
          )}
          {showAdvanced &&
            readiness &&
            Object.entries(readiness)
              .filter(
                ([, v]) =>
                  Array.isArray(v) || (v !== null && typeof v === "object"),
              )
              .map(([k, v]) => (
                <details className="c3-training-details" key={k}>
                  <summary>{k.replace(/_/g, " ")}</summary>
                  <pre>{JSON.stringify(v, null, 2)}</pre>
                </details>
              ))}
          <button
            className="c3-training-primary"
            type="button"
            disabled={starting || checking || ready !== true}
            onClick={() => void startTraining()}>
            {starting
              ? "Submitting training job…"
              : "Authorize & launch training →"}
          </button>
          {ready !== true && (
            <p className="c3-training-footnote">
              Upload triggers validation and registration in Data Workspace.
              Explicit synthetic-research authorization is still required before
              training can run.
            </p>
          )}
        </section>
        <section className="c3-training-card c3-training-history">
          <div className="c3-training-section-heading">
            <span className="c3-training-step">03</span>
            <div>
              <h4>Training runs</h4>
              <p>
                {jobs.length} backend-reported job{jobs.length === 1 ? "" : "s"}
              </p>
            </div>
          </div>
          {loading ? (
            <p className="c3-training-empty">Loading training history…</p>
          ) : !jobs.length ? (
            <div className="c3-training-empty">
              <strong>No training jobs yet</strong>
              <p>When you start training, the job will appear here.</p>
            </div>
          ) : (
            <div className="c3-training-joblist">
              {jobs.map((job, i) => (
                <button
                  type="button"
                  key={`${jobId(job)}-${i}`}
                  className={selectedJob === jobId(job) ? "selected" : ""}
                  onClick={() => setSelectedJob(jobId(job))}>
                  <span className="c3-training-jobhead">
                    <strong>{jobId(job)}</strong>
                    <span
                      className={`c3-training-badge ${stateTone(jobStatus(job))}`}>
                      {jobStatus(job)}
                    </span>
                  </span>
                  <small>{datasetId(job)}</small>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>
      <section className="c3-training-card c3-training-inspector">
        <div className="c3-training-section-heading">
          <span className="c3-training-step">04</span>
          <div>
            <h4>Run inspector</h4>
            <p>Actual training job metadata and outcomes</p>
          </div>
        </div>
        {!selectedJob || selectedJob === "—" ? (
          <p className="c3-training-empty">
            Select a training run to inspect its details.
          </p>
        ) : (
          <>
            <div className="c3-training-inspector-head">
              <div>
                <span className="c3-training-eyebrow">SELECTED RUN</span>
                <h4>{selectedJob}</h4>
                <p>{datasetId(selectedJobSummary || result)}</p>
              </div>
              <span
                className={`c3-training-badge ${stateTone(jobStatus(details || selectedJobSummary || {}))}`}>
                {jobStatus(details || selectedJobSummary || {})}
              </span>
            </div>
            <dl className="c3-training-keyvalues grid">
              {resultFields
                .filter(([k]) =>
                  [
                    "current_stage",
                    "created_at",
                    "started_at",
                    "completed_at",
                    "error_message",
                  ].includes(k),
                )
                .map(([k, v]) => (
                  <div key={k}>
                    <dt>{k.replace(/_/g, " ")}</dt>
                    <dd>{value(v)}</dd>
                  </div>
                ))}
            </dl>
            {showAdvanced &&
              Object.entries(result)
                .filter(
                  ([, v]) =>
                    Array.isArray(v) || (v !== null && typeof v === "object"),
                )
                .map(([k, v]) => (
                  <details className="c3-training-details" key={k}>
                    <summary>{k.replace(/_/g, " ")}</summary>
                    <pre>{JSON.stringify(v, null, 2)}</pre>
                  </details>
                ))}
          </>
        )}
        {selectedJob && selectedJob !== "—" && (
          <C3TrainingMonitor jobId={selectedJob} />
        )}
        <p className="c3-training-footnote">
          Job submission does not imply checkpoint activation. The backend must
          separately validate and activate selected models. No live training
          progress is invented by this interface.
        </p>
      </section>
    </div>
  );
}
