/** @format */

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  c3TrainingMonitorApi,
  type C3TrainingTelemetry,
} from "../api/c3TrainingApi";

import "../styles/c3TrainingMonitor.css";

/* ============================================================
   CONSTANTS
============================================================ */

const POLL_INTERVAL = 3000;

const TERMINAL = new Set([
  "COMPLETED",
  "FAILED",
  "CANCELLED",
  "CANCELED",
]);

const COLORS = {
  train: "#0c9f9b",
  validation: "#ff7100",
  grid: "#e8edf2",
  axis: "#708094",
};

/* ============================================================
   TYPES
============================================================ */

type MetricPoint = C3TrainingTelemetry["metric_points"][number];

type MetricKey =
  | "train_mae"
  | "val_mae"
  | "train_rmse"
  | "val_rmse";

type ChartType = "MAE" | "RMSE";

interface ChartProps {
  points: MetricPoint[];
  type: ChartType;
}

interface MetricSummary {
  latest: number | null;
  best: number | null;
  bestEpoch: number | null;
}

/* ============================================================
   HELPERS
============================================================ */

function readable(stage: string): string {
  return stage
    .replace(/^TRAINING_/, "")
    .replaceAll("_", " ");
}

function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "—";
  }

  return value.toFixed(4);
}

function formatTime(timestamp?: string): string {
  if (!timestamp) return "--:--:--";

  const match = timestamp.match(/T(\d{2}:\d{2}:\d{2})/);

  return match?.[1] ?? timestamp.slice(11, 19);
}

function getMetric(
  point: MetricPoint,
  key: MetricKey,
): number | null {
  const value = point.metrics[key];

  return typeof value === "number" && Number.isFinite(value)
    ? value
    : null;
}

function getMetricSummary(
  points: MetricPoint[],
  key: MetricKey,
): MetricSummary {
  const available = points
    .filter((point) => point.epoch !== null)
    .map((point) => ({
      epoch: point.epoch as number,
      value: getMetric(point, key),
    }))
    .filter(
      (point): point is { epoch: number; value: number } =>
        point.value !== null,
    );

  if (!available.length) {
    return {
      latest: null,
      best: null,
      bestEpoch: null,
    };
  }

  const latest = available[available.length - 1];

  const best = available.reduce((current, point) =>
    point.value < current.value ? point : current,
  );

  return {
    latest: latest.value,
    best: best.value,
    bestEpoch: best.epoch,
  };
}

function getModelLabel(stage: string): string {
  if (!stage) return "Waiting for model information";

  const cleaned = stage.replace(/^TRAINING_/, "");

  const match = cleaned.match(
    /^(M\d+)_([A-Z])_(15|30|60)MIN$/i,
  );

  if (match) {
    return `${match[1]}-${match[2]} · ${match[3]}-minute forecast`;
  }

  return readable(stage);
}

function getActiveMetricPoints(
  telemetry: C3TrainingTelemetry,
): MetricPoint[] {
  const valid = telemetry.metric_points.filter(
    (point) =>
      point.epoch !== null &&
      Object.values(point.metrics).some(
        (value) => typeof value === "number" && Number.isFinite(value),
      ),
  );

  if (!valid.length) return [];

  const currentStage = telemetry.current_stage;

  const activeStage = currentStage.startsWith("TRAINING_")
    ? currentStage
    : valid[valid.length - 1].stage;

  const selected = valid.filter(
    (point) => point.stage === activeStage,
  );

  // Preserve the latest available model metrics if the worker has
  // transitioned into artifact review or registration.
  const points = selected.length
    ? selected
    : valid.filter(
        (point) => point.stage === valid[valid.length - 1].stage,
      );

  // One point per epoch. If telemetry contains repeated records,
  // retain the latest recorded metrics for that epoch.
  const byEpoch = new Map<number, MetricPoint>();

  for (const point of points) {
    if (point.epoch !== null) {
      const previous = byEpoch.get(point.epoch);

      byEpoch.set(point.epoch, {
        ...point,
        metrics: {
          ...(previous?.metrics ?? {}),
          ...point.metrics,
        },
      });
    }
  }

  return [...byEpoch.values()].sort(
    (a, b) => (a.epoch ?? 0) - (b.epoch ?? 0),
  );
}

/* ============================================================
   METRIC CHART
============================================================ */

function MetricChart({ points, type }: ChartProps) {
  const [hoveredEpoch, setHoveredEpoch] = useState<number | null>(
    null,
  );

  const trainKey: MetricKey =
    type === "MAE" ? "train_mae" : "train_rmse";

  const validationKey: MetricKey =
    type === "MAE" ? "val_mae" : "val_rmse";

  const chartPoints = useMemo(
    () =>
      points.filter(
        (point) =>
          getMetric(point, trainKey) !== null ||
          getMetric(point, validationKey) !== null,
      ),
    [points, trainKey, validationKey],
  );

  const trainSummary = useMemo(
    () => getMetricSummary(chartPoints, trainKey),
    [chartPoints, trainKey],
  );

  const validationSummary = useMemo(
    () => getMetricSummary(chartPoints, validationKey),
    [chartPoints, validationKey],
  );

  if (!chartPoints.length) {
    return (
      <div className="c3-monitor-metric-card">
        <div className="c3-monitor-chart-header">
          <div>
            <h5>{type} by epoch</h5>
            <p>
              {type === "MAE"
                ? "Mean Absolute Error"
                : "Root Mean Squared Error"}
            </p>
          </div>
        </div>

        <div className="c3-monitor-chart-empty">
          Waiting for recorded {type} metrics from the training worker.
        </div>
      </div>
    );
  }

  /* ----------------------------------------------------------
     CHART GEOMETRY
  ---------------------------------------------------------- */

  const width = 660;
  const height = 270;

  const margin = {
    top: 20,
    right: 22,
    bottom: 42,
    left: 62,
  };

  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  const epochs = chartPoints.map((point) => point.epoch as number);

  const minEpoch = Math.min(...epochs);
  const maxEpoch = Math.max(...epochs);

  const values = chartPoints.flatMap((point) =>
    [getMetric(point, trainKey), getMetric(point, validationKey)].filter(
      (value): value is number => value !== null,
    ),
  );

  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);

  const rawRange = maxValue - minValue;

  const padding =
    rawRange > 0
      ? rawRange * 0.12
      : Math.max(Math.abs(maxValue) * 0.1, 0.01);

  const yMin = Math.max(0, minValue - padding);
  const yMax = maxValue + padding;

  const yRange = Math.max(yMax - yMin, 0.000001);

  const x = (epoch: number): number =>
    margin.left +
    ((epoch - minEpoch) / Math.max(1, maxEpoch - minEpoch)) *
      plotWidth;

  const y = (metric: number): number =>
    margin.top +
    plotHeight -
    ((metric - yMin) / yRange) * plotHeight;

  const makePath = (key: MetricKey): string => {
    let path = "";
    let started = false;

    for (const point of chartPoints) {
      const metric = getMetric(point, key);

      if (metric === null || point.epoch === null) {
        started = false;
        continue;
      }

      const command = started ? "L" : "M";

      path += `${command}${x(point.epoch).toFixed(2)},${y(metric).toFixed(2)} `;

      started = true;
    }

    return path.trim();
  };

  const gridLines = Array.from({ length: 5 }, (_, index) => {
    const ratio = index / 4;

    return {
      value: yMax - ratio * yRange,
      position: margin.top + ratio * plotHeight,
    };
  });

  const epochTicks = chartPoints
    .map((point) => point.epoch as number)
    .filter(
      (epoch, index, array) =>
        index === 0 ||
        index === array.length - 1 ||
        array.length <= 8 ||
        index % Math.ceil(array.length / 6) === 0,
    );

  const hoveredPoint =
    chartPoints.find((point) => point.epoch === hoveredEpoch) ??
    null;

  return (
    <div className="c3-monitor-metric-card">
      {/* CHART HEADER */}

      <div className="c3-monitor-chart-header">
        <div>
          <h5>{type} by epoch</h5>

          <p>
            {type === "MAE"
              ? "Mean Absolute Error"
              : "Root Mean Squared Error"}
          </p>
        </div>

        <span className="c3-monitor-chart-unit">
          Lower is better ↓
        </span>
      </div>

      {/* METRIC SUMMARY */}

      <div className="c3-monitor-metric-summary">
        <div>
          <span>Latest validation</span>

          <strong>
            {formatMetric(validationSummary.latest)}
          </strong>
        </div>

        <div>
          <span>Best validation</span>

          <strong>
            {formatMetric(validationSummary.best)}
          </strong>

          {validationSummary.bestEpoch !== null && (
            <small>
              Epoch {validationSummary.bestEpoch}
            </small>
          )}
        </div>
      </div>

      {/* LEGEND */}

      <div className="c3-monitor-legend">
        <span>
          <i className="train" />
          Training {type}
        </span>

        <span>
          <i className="validation" />
          Validation {type}
        </span>
      </div>

      {/* SVG CHART */}

      <div className="c3-monitor-chart-container">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={`${type} training and validation error by epoch`}
        >
          {/* GRID + Y AXIS */}

          {gridLines.map((line, index) => (
            <g key={index}>
              <line
                x1={margin.left}
                x2={width - margin.right}
                y1={line.position}
                y2={line.position}
                stroke={COLORS.grid}
                strokeWidth="1"
              />

              <text
                x={margin.left - 12}
                y={line.position + 4}
                textAnchor="end"
                fontSize="11"
                fill={COLORS.axis}
              >
                {line.value.toFixed(2)}
              </text>
            </g>
          ))}

          {/* X AXIS */}

          {epochTicks.map((epoch) => (
            <text
              key={epoch}
              x={x(epoch)}
              y={height - 16}
              textAnchor="middle"
              fontSize="11"
              fill={COLORS.axis}
            >
              {epoch}
            </text>
          ))}

          {/* TRAINING LINE */}

          <path
            d={makePath(trainKey)}
            stroke={COLORS.train}
            strokeWidth="2.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />

          {/* VALIDATION LINE */}

          <path
            d={makePath(validationKey)}
            stroke={COLORS.validation}
            strokeWidth="2.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />

          {/* INTERACTIVE POINTS */}

          {chartPoints.map((point) => {
            const epoch = point.epoch as number;

            const trainValue = getMetric(point, trainKey);
            const validationValue = getMetric(point, validationKey);

            return (
              <g key={epoch}>
                {trainValue !== null && (
                  <circle
                    cx={x(epoch)}
                    cy={y(trainValue)}
                    r={hoveredEpoch === epoch ? 5 : 3}
                    fill={COLORS.train}
                    stroke="white"
                    strokeWidth="1.5"
                  />
                )}

                {validationValue !== null && (
                  <circle
                    cx={x(epoch)}
                    cy={y(validationValue)}
                    r={hoveredEpoch === epoch ? 5 : 3}
                    fill={COLORS.validation}
                    stroke="white"
                    strokeWidth="1.5"
                  />
                )}

                <rect
                  x={x(epoch) - Math.max(10, plotWidth / chartPoints.length / 2)}
                  y={margin.top}
                  width={Math.max(20, plotWidth / chartPoints.length)}
                  height={plotHeight}
                  fill="transparent"
                  onMouseEnter={() => setHoveredEpoch(epoch)}
                  onMouseLeave={() => setHoveredEpoch(null)}
                />
              </g>
            );
          })}

          {/* HOVER INDICATOR */}

          {hoveredPoint && hoveredPoint.epoch !== null && (
            <line
              x1={x(hoveredPoint.epoch)}
              x2={x(hoveredPoint.epoch)}
              y1={margin.top}
              y2={margin.top + plotHeight}
              stroke="#94a3b8"
              strokeDasharray="4 4"
              pointerEvents="none"
            />
          )}
        </svg>

        {/* HOVER DETAILS */}

        {hoveredPoint && (
          <div className="c3-monitor-chart-tooltip">
            <strong>Epoch {hoveredPoint.epoch}</strong>

            <span>
              Training:{" "}
              {formatMetric(getMetric(hoveredPoint, trainKey))}
            </span>

            <span>
              Validation:{" "}
              {formatMetric(getMetric(hoveredPoint, validationKey))}
            </span>
          </div>
        )}
      </div>

      <div className="c3-monitor-chart-footer">
        <span>Epoch →</span>

        <span>
          Latest training: {formatMetric(trainSummary.latest)}
        </span>
      </div>
    </div>
  );
}

/* ============================================================
   TRAINING MONITOR
============================================================ */

export function C3TrainingMonitor({
  jobId,
}: {
  jobId: string;
}) {
  const [data, setData] =
    useState<C3TrainingTelemetry | null>(null);

  const [error, setError] = useState("");

  const [autoScroll, setAutoScroll] = useState(true);

  const [followingLatest, setFollowingLatest] = useState(true);

  const consoleRef = useRef<HTMLDivElement | null>(null);

  const lastEventRef = useRef<string>("");

  /* ============================================================
     TELEMETRY POLLING
  ============================================================ */

  useEffect(() => {
    if (!jobId) {
      setData(null);
      return;
    }

    let disposed = false;
    let busy = false;
    let finished = false;

    const load = async () => {
      if (busy || finished || disposed) return;

      busy = true;

      try {
        const result =
          await c3TrainingMonitorApi.telemetry(jobId);

        if (disposed) return;

        setData(result);
        setError("");

        if (TERMINAL.has(result.status.toUpperCase())) {
          finished = true;
        }
      } catch (cause) {
        if (!disposed) {
          setError(
            cause instanceof Error
              ? cause.message
              : "Training telemetry unavailable.",
          );
        }
      } finally {
        busy = false;
      }
    };

    setData(null);
    setError("");

    lastEventRef.current = "";

    void load();

    const timer = window.setInterval(
      () => void load(),
      POLL_INTERVAL,
    );

    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [jobId]);

  /* ============================================================
     CONSOLE SCROLLING
  ============================================================ */

  const scrollToLatest = useCallback(() => {
    const element = consoleRef.current;

    if (!element) return;

    element.scrollTop = element.scrollHeight;
  }, []);

  const jumpToLatest = useCallback(() => {
    setAutoScroll(true);
    setFollowingLatest(true);

    requestAnimationFrame(() => {
      scrollToLatest();
    });
  }, [scrollToLatest]);

  const handleConsoleScroll = useCallback(() => {
    const element = consoleRef.current;

    if (!element) return;

    const distance =
      element.scrollHeight -
      element.scrollTop -
      element.clientHeight;

    const nearBottom = distance < 35;

    setFollowingLatest(nearBottom);

    if (!nearBottom) {
      setAutoScroll(false);
    }
  }, []);

  const lastEvent = data?.events[data.events.length - 1];

  const lastEventKey = lastEvent
    ? `${lastEvent.event_id ?? ""}:${lastEvent.timestamp ?? ""}:${lastEvent.message}`
    : "";

  useEffect(() => {
    if (!autoScroll || !followingLatest) return;

    if (lastEventRef.current === lastEventKey) return;

    lastEventRef.current = lastEventKey;

    requestAnimationFrame(() => {
      scrollToLatest();
    });
  }, [
    lastEventKey,
    autoScroll,
    followingLatest,
    scrollToLatest,
  ]);

  /* ============================================================
     ACTIVE MODEL METRICS
  ============================================================ */

  const metricPoints = useMemo(
    () => (data ? getActiveMetricPoints(data) : []),
    [data],
  );

  const activeStage = useMemo(() => {
    if (!data) return "";

    if (data.current_stage.startsWith("TRAINING_")) {
      return data.current_stage;
    }

    return metricPoints[0]?.stage ?? data.current_stage;
  }, [data, metricPoints]);

  const currentEpoch =
    metricPoints.length > 0
      ? metricPoints[metricPoints.length - 1].epoch
      : data?.current_epoch ?? null;

  const progress = data
    ? Math.min(100, Math.max(0, data.progress_percent))
    : 0;

  /* ============================================================
     RENDER
  ============================================================ */

  if (!jobId) return null;

  return (
    <section
      className="c3-monitor"
      aria-label="Live training monitor"
    >
      {/* HEADER */}

      <header className="c3-monitor-header">
        <div>
          <span className="c3-monitor-eyebrow">
            LIVE TRAINING TELEMETRY
          </span>

          <h3>Training monitor</h3>

          <p className="c3-monitor-subtitle">
            Live execution progress and recorded model performance
          </p>
        </div>

        <span
          className={`c3-monitor-state ${
            data?.status.toLowerCase() ?? "connecting"
          }`}
        >
          {data?.status ?? "CONNECTING"}
        </span>
      </header>

      {error && (
        <p
          role="alert"
          className="c3-monitor-error"
        >
          {error}
        </p>
      )}

      {data && (
        <>
          {/* ==================================================
              STATUS CARDS
          ================================================== */}

          <div className="c3-monitor-stats">
            <div>
              <span>Completed commands</span>

              <strong>
                {data.completed_tasks} / {data.total_tasks}
              </strong>
            </div>

            <div>
              <span>Current model</span>

              <strong>
                {getModelLabel(activeStage)}
              </strong>
            </div>

            <div>
              <span>Current epoch</span>

              <strong>
                {currentEpoch === null
                  ? "Not reported"
                  : `${currentEpoch} / ${data.max_epochs ?? "?"}`}
              </strong>
            </div>
          </div>

          {/* ==================================================
              OVERALL PROGRESS
          ================================================== */}

          <div className="c3-monitor-progress-heading">
            <strong>
              Overall training progress
            </strong>

            <span>
              {progress.toFixed(1)}%
            </span>
          </div>

          <div
            className="c3-monitor-track"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Completed training commands"
          >
            <div
              style={{
                width: `${progress}%`,
              }}
            />
          </div>

          <p className="c3-monitor-note">
            {data.progress_basis}. Progress is based on completed
            training commands, not estimated remaining time.
          </p>

          {/* ==================================================
              MODEL PERFORMANCE
          ================================================== */}

          <div className="c3-monitor-section-heading">
            <div>
              <h4>Model performance</h4>

              <p>
                {getModelLabel(activeStage)}
              </p>
            </div>

            <span className="c3-monitor-live-label">
              <i />
              {TERMINAL.has(data.status.toUpperCase())
                ? "Recorded results"
                : "Live updates"}
            </span>
          </div>

          <div className="c3-monitor-chart-grid">
            <MetricChart
              points={metricPoints}
              type="MAE"
            />

            <MetricChart
              points={metricPoints}
              type="RMSE"
            />
          </div>

          <p className="c3-monitor-explanation">
            <strong>How to read these charts:</strong> Each point
            represents one recorded training epoch. Teal shows
            training error; orange shows validation error.
            Lower values indicate better predictive accuracy on
            the corresponding data split. A widening gap between
            training and validation error may indicate overfitting.
            These are synthetic research metrics, not field
            performance measurements.
          </p>

          {/* ==================================================
              WORKER EVENT CONSOLE
          ================================================== */}

          <div className="c3-monitor-console-heading">
            <div>
              <h4>Worker event console</h4>

              <p>
                Actual backend execution logs
              </p>
            </div>

            <div className="c3-monitor-console-actions">
              <label>
                <input
                  type="checkbox"
                  checked={autoScroll}
                  onChange={(event) => {
                    const enabled = event.target.checked;

                    setAutoScroll(enabled);

                    if (enabled) {
                      setFollowingLatest(true);

                      requestAnimationFrame(() => {
                        scrollToLatest();
                      });
                    }
                  }}
                />

                Auto-scroll
              </label>

              <button
                type="button"
                className="c3-monitor-jump-button"
                onClick={jumpToLatest}
              >
                ↓ Jump to latest
              </button>
            </div>
          </div>

          <div
            ref={consoleRef}
            className="c3-monitor-console"
            role="log"
            aria-live="off"
            onScroll={handleConsoleScroll}
          >
            {data.events.length ? (
              data.events.map((event, index) => (
                <div
                  className="c3-monitor-console-row"
                  key={String(event.event_id ?? index)}
                >
                  <time>
                    {formatTime(event.timestamp)}
                  </time>

                  <b
                    className={`level-${(
                      event.level ?? "info"
                    ).toLowerCase()}`}
                  >
                    {event.level ?? "INFO"}
                  </b>

                  <span>
                    [{event.stage}] {event.message}
                  </span>
                </div>
              ))
            ) : (
              <p>
                Waiting for persisted worker events…
              </p>
            )}
          </div>

          <div className="c3-monitor-console-footer">
            <span>
              {data.events.length} recorded events
            </span>

            <span>
              {autoScroll
                ? "Following latest events"
                : "Auto-scroll paused"}
            </span>
          </div>

          {/* ==================================================
              BACKEND ERROR
          ================================================== */}

          {data.error_message && (
            <p
              role="alert"
              className="c3-monitor-error"
            >
              {data.error_message}
            </p>
          )}
        </>
      )}
    </section>
  );
}