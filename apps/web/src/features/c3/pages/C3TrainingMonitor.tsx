/** @format */

import { useEffect, useMemo, useState } from "react";
import {
  c3TrainingMonitorApi,
  type C3TrainingTelemetry,
} from "../api/c3TrainingApi";
import "../styles/c3TrainingMonitor.css";

const TERMINAL = new Set(["COMPLETED", "FAILED", "CANCELLED"]);
function readable(stage: string) {
  return stage.replace(/^TRAINING_/, "").replaceAll("_", " ");
}
function Graph({ telemetry }: { telemetry: C3TrainingTelemetry }) {
  const series = useMemo(() => {
    const points = telemetry.metric_points.filter(
      (p) => p.epoch !== null && Object.keys(p.metrics).length > 0,
    );
    const stage = telemetry.current_stage.startsWith("TRAINING_")
      ? telemetry.current_stage
      : points[points.length - 1]?.stage;
    return points.filter((p) => p.stage === stage);
  }, [telemetry]);
  const keys = [
    "train_mae",
    "val_mae",
    "train_rmse",
    "val_rmse",
    "train_loss",
    "val_loss",
    "training_loss",
    "validation_loss",
  ];
  const metric = (p: (typeof series)[number], k: string) => p.metrics[k];
  const activeKeys = keys.filter((k) =>
    series.some((p) => Number.isFinite(metric(p, k))),
  );
  if (!series.length || !activeKeys.length)
    return (
      <p className="c3-monitor-empty">
        Epoch-level loss values are not available in recorded worker output. The
        chart will appear when the training script emits numeric epoch metrics.
      </p>
    );
  const values = series.flatMap((p) =>
    activeKeys.map((k) => metric(p, k)).filter((v) => Number.isFinite(v)),
  );
  const low = Math.min(...values),
    high = Math.max(...values);
  const epochs = series.map((p) => p.epoch || 0),
    minEpoch = Math.min(...epochs),
    maxEpoch = Math.max(...epochs);
  const x = (e: number) =>
    36 + ((e - minEpoch) / Math.max(1, maxEpoch - minEpoch)) * 540;
  const y = (v: number) =>
    174 - ((v - low) / Math.max(0.000001, high - low)) * 144;
  return (
    <div className="c3-monitor-chart">
      <svg
        viewBox="0 0 610 205"
        role="img"
        aria-label="Recorded training and validation loss by epoch">
        <line
          x1="36"
          x2="580"
          y1="176"
          y2="176"
          stroke="currentColor"
          opacity=".3"
        />
        {activeKeys.map((k, i) => (
          <path
            key={k}
            d={series
              .filter((p) => Number.isFinite(metric(p, k)))
              .map(
                (p, n) =>
                  `${n ? "L" : "M"}${x(p.epoch || 0).toFixed(1)},${y(metric(p, k)).toFixed(1)}`,
              )
              .join(" ")}
            stroke={i % 2 ? "#ff7100" : "#13a89e"}
            fill="none"
            strokeWidth="2.5"
          />
        ))}
        <text x="36" y="198" fontSize="12" fill="currentColor">
          Epoch {minEpoch}
        </text>
        <text
          x="580"
          y="198"
          textAnchor="end"
          fontSize="12"
          fill="currentColor">
          Epoch {maxEpoch}
        </text>
      </svg>
      <p>{activeKeys.join(" · ")} · most recent trained model</p>
    </div>
  );
}
export function C3TrainingMonitor({ jobId }: { jobId: string }) {
  const [data, setData] = useState<C3TrainingTelemetry | null>(null);
  const [error, setError] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  useEffect(() => {
    if (!jobId) {
      setData(null);
      return;
    }
    let disposed = false;
    let busy = false;
    const load = async () => {
      if (busy) return;
      busy = true;
      try {
        const result = await c3TrainingMonitorApi.telemetry(jobId);
        if (!disposed) {
          setData(result);
          setError("");
        }
      } catch (e) {
        if (!disposed)
          setError(e instanceof Error ? e.message : "Telemetry unavailable");
      } finally {
        busy = false;
      }
    };
    setData(null);
    void load();
    const timer = window.setInterval(() => {
      if (!data || !TERMINAL.has(data.status)) void load();
    }, 3000);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [jobId]);
  useEffect(() => {
    if (autoScroll)
      document.getElementById("c3-training-console")?.scrollTo({ top: 999999 });
  }, [data?.events.length, autoScroll]);
  if (!jobId) return null;
  return (
    <section className="c3-monitor" aria-label="Live training monitor">
      <header>
        <div>
          <span className="c3-monitor-eyebrow">
            F10.4.2 / LIVE TRAINING TELEMETRY
          </span>
          <h3>Training monitor</h3>
        </div>
        <span className="c3-monitor-state">{data?.status || "CONNECTING"}</span>
      </header>
      {error && (
        <p role="alert" className="c3-monitor-error">
          {error}
        </p>
      )}
      {data && (
        <>
          <div className="c3-monitor-stats">
            <div>
              <span>Completed commands</span>
              <strong>
                {data.completed_tasks} / {data.total_tasks}
              </strong>
            </div>
            <div>
              <span>Current task</span>
              <strong>{readable(data.current_stage)}</strong>
            </div>
            <div>
              <span>Epoch</span>
              <strong>
                {data.current_epoch === null
                  ? "Not reported"
                  : `${data.current_epoch} / ${data.max_epochs ?? "?"}`}
              </strong>
            </div>
          </div>
          <div className="c3-monitor-progress-heading">
            <strong>{data.progress_percent.toFixed(1)}%</strong>
            <span>Completed-command progress</span>
          </div>
          <div
            className="c3-monitor-track"
            role="progressbar"
            aria-valuenow={data.progress_percent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Completed training commands">
            <div style={{ width: `${data.progress_percent}%` }} />
          </div>
          <p className="c3-monitor-note">
            {data.progress_basis}. This is not an estimate of remaining training
            time.
          </p>
          <h4>Recorded epoch metrics</h4>
          <Graph telemetry={data} />
          <div className="c3-monitor-console-heading">
            <h4>Worker event console</h4>
            <label>
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
              />{" "}
              Auto-scroll
            </label>
          </div>
          <div
            className="c3-monitor-console"
            id="c3-training-console"
            role="log"
            aria-live="off">
            {data.events.length ? (
              data.events.map((event, index) => (
                <div key={String(event.event_id ?? index)}>
                  <time>{event.timestamp?.slice(11, 19) ?? "--:--:--"}</time>
                  <b>{event.level ?? "INFO"}</b>
                  <span>
                    [{event.stage}] {event.message}
                  </span>
                </div>
              ))
            ) : (
              <p>Waiting for persisted worker events…</p>
            )}
          </div>
          {data.error_message && (
            <p role="alert" className="c3-monitor-error">
              {data.error_message}
            </p>
          )}
        </>
      )}
    </section>
  );
}
