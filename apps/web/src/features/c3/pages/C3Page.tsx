/** @format */

import { useEffect, useMemo, useState } from "react";

import {
  c3Api,
  type Ablation,
  type Horizon,
  type ModelAvailability,
  type ValidationExample,
  type ForecastResponse,
} from "../api/c3Api";

import { C3DatasetManager } from "./C3DatasetManager";

import "../styles/c3Prediction.css";

type C3WorkbenchTab = "prediction" | "datasets";

const HORIZONS: Horizon[] = [15, 30, 60];

const ABLATIONS: Ablation[] = ["A", "B", "C"];

const ablationNames: Record<Ablation, string> = {
  A: "Elapsed time only",
  B: "Operating mode only",
  C: "Elapsed time + mode",
};

// ============================================================
// Moisture History
// ============================================================

function moistureHistory(
  example: ValidationExample,
): Array<{ index: number; value: number }> {
  return example.temporal_sequence.steps.flatMap((step, index) => {
    const value = step.features?.soil_moisture_pct;

    return typeof value === "number" && Number.isFinite(value)
      ? [{ index, value }]
      : [];
  });
}

// ============================================================
// Moisture Forecast Chart
// ============================================================

function MoistureChart({
  example,
  forecast,
}: {
  example: ValidationExample;
  forecast: ForecastResponse | null;
}) {
  const history = moistureHistory(example);

  const actual = example.actual_soil_moisture_percent;

  const predicted = forecast?.forecast_soil_moisture_percent;

  const allValues = [
    ...history.map((point) => point.value),
    actual,
    ...(predicted === undefined ? [] : [predicted]),
  ];

  const min = Math.min(...allValues) - 1;
  const max = Math.max(...allValues) + 1;

  const y = (value: number) =>
    170 - ((value - min) / Math.max(max - min, 0.001)) * 130;

  const x = (index: number) =>
    45 +
    (index / Math.max(example.temporal_sequence.steps.length, 1)) * 450;

  const path = history
    .map(
      (point, index) =>
        `${index === 0 ? "M" : "L"} ${x(point.index).toFixed(2)} ${y(
          point.value,
        ).toFixed(2)}`,
    )
    .join(" ");

  const futureX = x(example.temporal_sequence.steps.length);

  const last = history[history.length - 1];

  return (
    <div className="c3-chart-wrap">
      <svg
        className="c3-chart"
        viewBox="0 0 550 210"
        role="img"
        aria-label="Observed synthetic soil moisture, actual future target, and optional forecast"
      >
        {[0, 1, 2, 3].map((tick) => {
          const val = min + ((max - min) * tick) / 3;

          return (
            <g key={tick}>
              <line
                x1="45"
                x2="515"
                y1={y(val)}
                y2={y(val)}
                stroke="currentColor"
                opacity="0.12"
              />

              <text
                x="38"
                y={y(val) + 4}
                textAnchor="end"
                fill="currentColor"
                fontSize="11"
              >
                {val.toFixed(1)}
              </text>
            </g>
          );
        })}

        <line
          x1="45"
          y1="183"
          x2="515"
          y2="183"
          stroke="currentColor"
          opacity="0.35"
        />

        {path && (
          <path
            d={path}
            fill="none"
            stroke="#38bdf8"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}

        {last && (
          <circle
            cx={x(last.index)}
            cy={y(last.value)}
            r="4"
            fill="#38bdf8"
          />
        )}

        {last && (
          <line
            x1={x(last.index)}
            y1={y(last.value)}
            x2={futureX}
            y2={y(actual)}
            stroke="#22c55e"
            strokeDasharray="4 5"
            opacity="0.65"
          />
        )}

        <circle
          cx={futureX}
          cy={y(actual)}
          r="5"
          fill="#22c55e"
        />

        {predicted !== undefined && (
          <>
            <circle
              cx={futureX}
              cy={y(predicted)}
              r="5"
              fill="#fb923c"
            />

            <line
              x1={futureX}
              x2={futureX}
              y1={y(predicted)}
              y2={y(actual)}
              stroke="#fb923c"
              strokeDasharray="3 3"
            />
          </>
        )}

        <text
          x="45"
          y="201"
          fill="currentColor"
          fontSize="11"
        >
          Observed sequence
        </text>

        <text
          x="515"
          y="201"
          textAnchor="end"
          fill="currentColor"
          fontSize="11"
        >
          Future target
        </text>
      </svg>

      <div className="c3-legend">
        <span>
          <i className="c3-dot observed" />
          Observed
        </span>

        <span>
          <i className="c3-dot actual" />
          Actual future
        </span>

        <span>
          <i className="c3-dot forecast" />
          Forecast
        </span>
      </div>
    </div>
  );
}

// ============================================================
// C3 Workbench
// ============================================================

export function C3Page() {
  // ----------------------------------------------------------
  // Workbench navigation
  // ----------------------------------------------------------

  const [activeTab, setActiveTab] =
    useState<C3WorkbenchTab>("prediction");

  // ----------------------------------------------------------
  // API and model state
  // ----------------------------------------------------------

  const [status, setStatus] = useState<
    "loading" | "online" | "offline"
  >("loading");

  const [models, setModels] = useState<ModelAvailability[]>([]);

  // ----------------------------------------------------------
  // Prediction Explorer state
  // ----------------------------------------------------------

  const [horizon, setHorizon] = useState<Horizon>(15);

  const [ablation, setAblation] = useState<Ablation>("A");

  const [examples, setExamples] = useState<ValidationExample[]>([]);

  const [offset, setOffset] = useState(0);

  const [hasMore, setHasMore] = useState(false);

  const [selectedId, setSelectedId] = useState("");

  const [loadingExamples, setLoadingExamples] = useState(false);

  const [running, setRunning] = useState(false);

  const [forecast, setForecast] = useState<ForecastResponse | null>(
    null,
  );

  const [error, setError] = useState("");

  // ==========================================================
  // Load API health and available checkpoints
  // ==========================================================

  useEffect(() => {
    const controller = new AbortController();

    Promise.all([
      c3Api.health(controller.signal),
      c3Api.models(controller.signal),
    ])
      .then(([health, response]) => {
        if (controller.signal.aborted) return;

        setStatus(
          health.status === "ok" ? "online" : "offline",
        );

        setModels(response.models);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          setStatus("offline");

          setError(
            cause instanceof Error
              ? cause.message
              : "API unavailable",
          );
        }
      });

    return () => controller.abort();
  }, []);

  // ==========================================================
  // Load validation examples
  // ==========================================================

  useEffect(() => {
    const controller = new AbortController();

    setLoadingExamples(true);

    setExamples([]);
    setSelectedId("");
    setForecast(null);
    setError("");

    c3Api
      .examples(horizon, offset, 10, controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;

        setExamples(response.examples);

        setSelectedId(response.examples[0]?.id ?? "");

        setHasMore(response.has_more);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            cause instanceof Error
              ? cause.message
              : "Could not load validation examples",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadingExamples(false);
        }
      });

    return () => controller.abort();
  }, [horizon, offset]);

  // ==========================================================
  // Selected example and checkpoint availability
  // ==========================================================

  const selected = useMemo(
    () => examples.find((example) => example.id === selectedId),
    [examples, selectedId],
  );

  const available = models.filter(
    (model) => model.available,
  ).length;

  const modelReady = models.some(
    (model) =>
      model.model === `M4-${ablation}` &&
      model.horizon_minutes === horizon &&
      model.available,
  );

  // ==========================================================
  // Run forecast
  // ==========================================================

  async function runForecast() {
    if (!selected || running) return;

    setRunning(true);
    setError("");
    setForecast(null);

    try {
      const response = await c3Api.predict(
        ablation,
        horizon,
        selected.temporal_sequence,
      );

      setForecast(response);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Prediction failed",
      );
    } finally {
      setRunning(false);
    }
  }

  // ==========================================================
  // Render
  // ==========================================================

  return (
    <div className="c3-workbench">
      {/* =====================================================
          Page Header
          ===================================================== */}

      <div className="eyebrow">
        <span className="eyebrow-line" />
        COMPONENT 03 / FORECASTING
      </div>

      <div className="page-title-row">
        <div>
          <h1 className="page-title">
            Temporal Forecasting <span>Workbench</span>
          </h1>

          <p className="page-description">
            Mode-conditioned, variable-rate multi-sensor forecasting
            · Synthetic validation demonstration.
          </p>
        </div>

        <span className={`connection-pill ${status}`}>
          <span className="status-dot" />

          {status === "online"
            ? "C3 API ONLINE"
            : status === "loading"
              ? "CONNECTING"
              : "C3 API OFFLINE"}
        </span>
      </div>

      {/* =====================================================
          Workbench Statistics
          ===================================================== */}

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">
            CHECKPOINTS DISCOVERED
          </span>

          <div className="stat-value">
            {status === "online"
              ? `${available} / 9`
              : "—"}
          </div>

          <span className="stat-foot">
            M4-A · M4-B · M4-C
          </span>
        </div>

        <div className="stat-card">
          <span className="stat-label">
            FORECAST HORIZONS
          </span>

          <div className="stat-value">
            15 <small>/ 30 / 60</small>
          </div>

          <span className="stat-foot">
            Minutes ahead
          </span>
        </div>

        <div className="stat-card">
          <span className="stat-label">
            MODEL INPUT
          </span>

          <div className="stat-value">
            20 <small>features</small>
          </div>

          <span className="stat-foot">
            Sensors · masks · time · mode
          </span>
        </div>

        <div className="stat-card">
          <span className="stat-label">
            DATASET
          </span>

          <div className="stat-value">
            V2
          </div>

          <span className="stat-foot">
            Synthetic validation only
          </span>
        </div>
      </div>

      {/* =====================================================
          C3 Workbench Navigation
          ===================================================== */}

      <nav
        className="c3-workbench-tabs"
        aria-label="C3 research workbench sections"
      >
        <button
          type="button"
          className={`c3-workbench-tab ${
            activeTab === "prediction" ? "active" : ""
          }`}
          aria-current={
            activeTab === "prediction"
              ? "page"
              : undefined
          }
          onClick={() => setActiveTab("prediction")}
        >
          Prediction Explorer
        </button>

        <button
          type="button"
          className={`c3-workbench-tab ${
            activeTab === "datasets" ? "active" : ""
          }`}
          aria-current={
            activeTab === "datasets"
              ? "page"
              : undefined
          }
          onClick={() => setActiveTab("datasets")}
        >
          Dataset Manager
        </button>
      </nav>

      {/* =====================================================
          Prediction Explorer Tab
          ===================================================== */}

      {activeTab === "prediction" && (
        <>
          {/* ===============================================
              Prediction Explorer
              =============================================== */}

          <section className="panel c3-prediction-explorer">
            <div className="panel-heading">
              <div>
                <span className="section-overline">
                  LIVE CHECKPOINT INFERENCE
                </span>

                <h2>Prediction Explorer</h2>
              </div>

              <span className="live-chip">
                M4 feature-augmented GRU
              </span>
            </div>

            <p className="panel-subtitle">
              Select a held-out-from-training validation example,
              choose an ablation and horizon, then execute the saved
              checkpoint through FastAPI.
            </p>

            {/* ===========================================
                Prediction Controls
                =========================================== */}

            <div className="c3-controls">
              <label>
                Forecast horizon

                <select
                  value={horizon}
                  onChange={(event) => {
                    setHorizon(
                      Number(event.target.value) as Horizon,
                    );

                    setOffset(0);
                  }}
                >
                  {HORIZONS.map((value) => (
                    <option
                      key={value}
                      value={value}
                    >
                      {value} minutes
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Model ablation

                <select
                  value={ablation}
                  onChange={(event) => {
                    setAblation(
                      event.target.value as Ablation,
                    );

                    setForecast(null);
                  }}
                >
                  {ABLATIONS.map((value) => (
                    <option
                      key={value}
                      value={value}
                    >
                      M4-{value} — {ablationNames[value]}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Validation example

                <select
                  value={selectedId}
                  disabled={
                    loadingExamples ||
                    examples.length === 0
                  }
                  onChange={(event) => {
                    setSelectedId(event.target.value);
                    setForecast(null);
                  }}
                >
                  {examples.map((example, index) => (
                    <option
                      key={example.id}
                      value={example.id}
                    >
                      {offset + index + 1}.{" "}
                      {example.episode_id} ·{" "}
                      {
                        example.temporal_sequence.steps
                          .length
                      }{" "}
                      steps
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {/* ===========================================
                Prediction Actions
                =========================================== */}

            <div className="c3-actions">
              <button
                type="button"
                className="c3-primary-button"
                onClick={() => void runForecast()}
                disabled={
                  !selected ||
                  !modelReady ||
                  running ||
                  status !== "online"
                }
              >
                {running
                  ? "Running inference…"
                  : "Run checkpoint forecast"}
              </button>

              <button
                type="button"
                className="c3-secondary-button"
                disabled={
                  offset === 0 ||
                  loadingExamples
                }
                onClick={() =>
                  setOffset((value) =>
                    Math.max(0, value - 10),
                  )
                }
              >
                Previous examples
              </button>

              <button
                type="button"
                className="c3-secondary-button"
                disabled={
                  !hasMore ||
                  loadingExamples
                }
                onClick={() =>
                  setOffset((value) => value + 10)
                }
              >
                Next examples
              </button>
            </div>

            {/* ===========================================
                Loading and Error Messages
                =========================================== */}

            {loadingExamples && (
              <p className="c3-inline-note">
                Loading validation examples…
              </p>
            )}

            {error && (
              <div
                className="api-warning"
                role="alert"
              >
                {error}
              </div>
            )}

            {/* ===========================================
                Prediction Results
                =========================================== */}

            {selected && (
              <>
                <div className="c3-result-grid">
                  <div>
                    <span>
                      Observed input steps
                    </span>

                    <strong>
                      {
                        selected.temporal_sequence.steps
                          .length
                      }
                    </strong>
                  </div>

                  <div>
                    <span>
                      Actual future moisture
                    </span>

                    <strong>
                      {selected.actual_soil_moisture_percent.toFixed(
                        4,
                      )}
                      %
                    </strong>
                  </div>

                  <div>
                    <span>
                      Model forecast
                    </span>

                    <strong>
                      {forecast
                        ? `${forecast.forecast_soil_moisture_percent.toFixed(
                            4,
                          )}%`
                        : "Not run"}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Absolute error
                    </span>

                    <strong>
                      {forecast
                        ? `${Math.abs(
                            forecast.forecast_soil_moisture_percent -
                              selected.actual_soil_moisture_percent,
                          ).toFixed(4)} pp`
                        : "—"}
                    </strong>
                  </div>
                </div>

                {/* Moisture chart */}

                <MoistureChart
                  example={selected}
                  forecast={forecast}
                />

                {/* Prediction metadata */}

                <div className="c3-meta">
                  <span>
                    Episode:{" "}
                    <strong>
                      {selected.episode_id}
                    </strong>
                  </span>

                  <span>
                    Device:{" "}
                    <strong>
                      {selected.device_id}
                    </strong>
                  </span>

                  <span>
                    Actual horizon:{" "}
                    <strong>
                      {selected.actual_horizon_seconds?.toFixed(
                        1,
                      ) ?? "—"}{" "}
                      s
                    </strong>
                  </span>
                </div>

                {/* =======================================
                    Sensor Sequence
                    ======================================= */}

                <div className="c3-steps">
                  <h3>
                    Sensor sequence and operating modes
                  </h3>

                  <div className="c3-step-list">
                    {selected.temporal_sequence.steps.map(
                      (step, index) => (
                        <div
                          key={index}
                          className="c3-step"
                        >
                          <strong>
                            Step {index + 1}
                          </strong>

                          <span>
                            {step.operating_mode ??
                              "UNKNOWN"}
                          </span>

                          <span>
                            Δt{" "}
                            {typeof step.delta_t_seconds ===
                            "number"
                              ? `${step.delta_t_seconds.toFixed(
                                  1,
                                )} s`
                              : "unknown"}
                          </span>

                          <span>
                            Moisture:{" "}
                            {typeof step.features
                              ?.soil_moisture_pct ===
                            "number"
                              ? `${step.features.soil_moisture_pct.toFixed(
                                  2,
                                )}%`
                              : "missing"}
                          </span>
                        </div>
                      ),
                    )}
                  </div>
                </div>
              </>
            )}

            {/* ===========================================
                Research Disclaimer
                =========================================== */}

            <p className="c3-research-warning">
              Research-only demonstration using synthetic
              validation data. Forecasts estimate future soil
              moisture; they are not landslide probabilities,
              operational warnings, or evidence of real-world
              accuracy.
            </p>
          </section>

          {/* ===============================================
              Available Model Checkpoints
              =============================================== */}

          <section className="panel c3-model-panel">
            <div className="panel-heading">
              <div>
                <span className="section-overline">
                  CHECKPOINT STATUS
                </span>

                <h2>Available trained models</h2>
              </div>
            </div>

            <div className="model-table">
              <div className="model-row model-table-header">
                <span>ABLATION</span>

                {HORIZONS.map((value) => (
                  <span key={value}>
                    {value} MIN
                  </span>
                ))}
              </div>

              {ABLATIONS.map((value) => (
                <div
                  className="model-row"
                  key={value}
                >
                  <strong>
                    M4-{value}

                    <small>
                      {ablationNames[value]}
                    </small>
                  </strong>

                  {HORIZONS.map((h) => {
                    const isAvailable = models.some(
                      (model) =>
                        model.model ===
                          `M4-${value}` &&
                        model.horizon_minutes === h &&
                        model.available,
                    );

                    return (
                      <span
                        key={h}
                        className={`model-indicator ${
                          isAvailable
                            ? "available"
                            : ""
                        }`}
                      >
                        {isAvailable
                          ? "Ready"
                          : "—"}
                      </span>
                    );
                  })}
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {/* =====================================================
          Dataset Manager Tab
          ===================================================== */}

      {activeTab === "datasets" && (
        <C3DatasetManager />
      )}
    </div>
  );
}