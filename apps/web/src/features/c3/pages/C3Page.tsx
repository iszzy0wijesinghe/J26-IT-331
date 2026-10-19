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
import { C3AdaptiveMonitoring } from "./C3AdaptiveMonitoring";
import { C3TrainingWorkspace } from "./C3TrainingWorkspace";
import { C3ModelEvaluation } from "./C3ModelEvaluation";
import { C3ResearchPipeline } from "./C3ResearchPipeline";
import { C3ActiveForecasting } from "./C3ActiveForecasting";

import "../styles/c3Prediction.css";
import "../styles/c3Studio.css";

type C3WorkbenchTab =
  | "pipeline"
  | "datasets"
  | "training"
  | "evaluation"
  | "prediction"
  | "forecasting"
  | "adaptive";

type WorkspaceDefinition = {
  id: C3WorkbenchTab;
  index: string;
  title: string;
  subtitle: string;
  heading: string;
  description: string;
};

// ============================================================
// Constants
// ============================================================

const HORIZONS: Horizon[] = [15, 30, 60];

const ABLATIONS: Ablation[] = ["A", "B", "C"];

const ablationNames: Record<Ablation, string> = {
  A: "Elapsed time only",
  B: "Operating mode only",
  C: "Elapsed time + mode",
};

const WORKSPACES: WorkspaceDefinition[] = [
  {
    id: "pipeline",
    index: "01",
    title: "Research pipeline",
    subtitle: "Upload · validate · train · evaluate",
    heading: "Research pipeline",
    description:
      "Prepare research datasets, assess readiness, monitor training, and review registered model candidates.",
  },
  {
    id: "datasets",
    index: "02",
    title: "Data workspace",
    subtitle: "Import · verify · inspect",
    heading: "Dataset preparation",
    description:
      "Manage dataset sources, validate observations, and inspect registered research data.",
  },
  {
    id: "training",
    index: "03",
    title: "Model training",
    subtitle: "Readiness · jobs · results",
    heading: "Model training",
    description:
      "Assess dataset readiness, submit training jobs, and inspect recorded training results.",
  },
  {
    id: "evaluation",
    index: "04",
    title: "Model evaluation",
    subtitle: "Candidates · active assignments",
    heading: "Model evaluation",
    description:
      "Compare validation metrics and inspect registered candidates, active assignments, and activation history.",
  },
  {
    id: "prediction",
    index: "05",
    title: "Forecast laboratory",
    subtitle: "Checkpoint inference",
    heading: "Forecast laboratory",
    description:
      "Explore legacy synthetic validation examples and execute available M4 checkpoint forecasts.",
  },
  {
    id: "adaptive",
    index: "06",
    title: "Adaptive analysis",
    subtitle: "Modes · energy · policy",
    heading: "Adaptive monitoring",
    description:
      "Replay historical monitoring decisions and compare modeled energy consumption against fixed-interval baselines.",
  },
  {
    id: "forecasting",
    index: "07",
    title: "Active forecasting",
    subtitle: "Real-time predictions",
    heading: "Active forecasting",
    description:
      "Execute real-time forecasting models and visualize prediction results.",
  }
];

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
          const value = min + ((max - min) * tick) / 3;

          return (
            <g key={tick}>
              <line
                x1="45"
                x2="515"
                y1={y(value)}
                y2={y(value)}
                stroke="currentColor"
                opacity="0.12"
              />

              <text
                x="38"
                y={y(value) + 4}
                textAnchor="end"
                fill="currentColor"
                fontSize="11"
              >
                {value.toFixed(1)}
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
// C3 Research Workbench
// ============================================================

export function C3Page() {
  // ----------------------------------------------------------
  // Workspace navigation
  // ----------------------------------------------------------

  const [activeTab, setActiveTab] =
    useState<C3WorkbenchTab>("pipeline");

  const activeWorkspace = useMemo(
    () =>
      WORKSPACES.find((workspace) => workspace.id === activeTab) ??
      WORKSPACES[0],
    [activeTab],
  );

  // ----------------------------------------------------------
  // API and legacy model state
  // ----------------------------------------------------------

  const [status, setStatus] = useState<
    "loading" | "online" | "offline"
  >("loading");

  const [models, setModels] = useState<ModelAvailability[]>([]);

  // ----------------------------------------------------------
  // Forecast Laboratory state
  // ----------------------------------------------------------

  const [horizon, setHorizon] = useState<Horizon>(15);

  const [ablation, setAblation] = useState<Ablation>("A");

  const [examples, setExamples] = useState<ValidationExample[]>([]);

  const [offset, setOffset] = useState(0);

  const [hasMore, setHasMore] = useState(false);

  const [selectedId, setSelectedId] = useState("");

  const [loadingExamples, setLoadingExamples] = useState(false);

  const [running, setRunning] = useState(false);

  const [forecast, setForecast] =
    useState<ForecastResponse | null>(null);

  const [error, setError] = useState("");

  // ==========================================================
  // Load API health and legacy checkpoints
  // ==========================================================

  useEffect(() => {
    const controller = new AbortController();

    Promise.all([
      c3Api.health(controller.signal),
      c3Api.models(controller.signal),
    ])
      .then(([health, response]) => {
        if (controller.signal.aborted) {
          return;
        }

        setStatus(
          health.status === "ok" ? "online" : "offline",
        );

        setModels(response.models);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setStatus("offline");

        setError(
          cause instanceof Error
            ? cause.message
            : "C3 API unavailable",
        );
      });

    return () => controller.abort();
  }, []);

  // ==========================================================
  // Load validation examples
  //
  // Only load these while the Forecast Laboratory is open.
  // ==========================================================

  useEffect(() => {
    if (activeTab !== "prediction") {
      return;
    }

    const controller = new AbortController();

    setLoadingExamples(true);

    setExamples([]);
    setSelectedId("");
    setForecast(null);
    setError("");

    c3Api
      .examples(horizon, offset, 10, controller.signal)
      .then((response) => {
        if (controller.signal.aborted) {
          return;
        }

        setExamples(response.examples);

        setSelectedId(response.examples[0]?.id ?? "");

        setHasMore(response.has_more);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setError(
          cause instanceof Error
            ? cause.message
            : "Could not load validation examples",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadingExamples(false);
        }
      });

    return () => controller.abort();
  }, [activeTab, horizon, offset]);

  // ==========================================================
  // Selected example and checkpoint availability
  // ==========================================================

  const selected = useMemo(
    () =>
      examples.find(
        (example) => example.id === selectedId,
      ),
    [examples, selectedId],
  );

  const available = useMemo(
    () => models.filter((model) => model.available).length,
    [models],
  );

  const modelReady = useMemo(
    () =>
      models.some(
        (model) =>
          model.model === `M4-${ablation}` &&
          model.horizon_minutes === horizon &&
          model.available,
      ),
    [models, ablation, horizon],
  );

  // ==========================================================
  // Run legacy checkpoint forecast
  // ==========================================================

  async function runForecast() {
    if (!selected || running || !modelReady) {
      return;
    }

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
  // Navigation helpers
  // ==========================================================

  function openWorkspace(tab: C3WorkbenchTab) {
    setActiveTab(tab);

    if (tab === "prediction") {
      setForecast(null);
      setError("");
    }
  }

  // ==========================================================
  // Render
  // ==========================================================

  return (
    <div className="c3-workbench">
      {/* ======================================================
          Research Studio Header
      ====================================================== */}

      <header className="c3-studio-header">
        <div>
          <span className="c3-studio-kicker">
            GEONEX / COMPONENT 03 / RESEARCH STUDIO
          </span>

          <h1>
            Forecasting{" "}
            <span>&amp; adaptive intelligence</span>
          </h1>

          <p>
            Explore datasets, validate moisture forecasts,
            and investigate safety-constrained monitoring
            decisions.
          </p>
        </div>

        <span
          className={`connection-pill ${status}`}
          role="status"
        >
          <span className="status-dot" />

          {status === "online"
            ? "API connected"
            : status === "loading"
              ? "Connecting"
              : "API unavailable"}
        </span>
      </header>

      {/* ======================================================
          Research Studio Layout
      ====================================================== */}

      <div className="c3-studio-layout">
        {/* ====================================================
            Sidebar
        ==================================================== */}

        <aside
          className="c3-studio-sidebar"
          aria-label="C3 workspace navigation"
        >
          <div className="c3-studio-sidebar-title">
            WORKSPACES <span>{String(WORKSPACES.length).padStart(2, "0")}</span>
          </div>

          <nav
            className="c3-studio-nav"
            aria-label="C3 research workbench sections"
          >
            {WORKSPACES.map((workspace) => (
              <button
                key={workspace.id}
                type="button"
                className={
                  activeTab === workspace.id
                    ? "selected"
                    : ""
                }
                aria-current={
                  activeTab === workspace.id
                    ? "page"
                    : undefined
                }
                onClick={() =>
                  openWorkspace(workspace.id)
                }
              >
                <span className="c3-studio-nav-index">
                  {workspace.index}
                </span>

                <span>
                  <strong>{workspace.title}</strong>

                  <small>{workspace.subtitle}</small>
                </span>

                <span
                  className="c3-studio-nav-arrow"
                  aria-hidden="true"
                >
                  ↗
                </span>
              </button>
            ))}
          </nav>

          <div className="c3-studio-sidebar-note">
            <span>RESEARCH BOUNDARY</span>

            <p>
              Synthetic demonstration. Forecasts are
              moisture estimates, not landslide
              probabilities.
            </p>
          </div>
        </aside>

        {/* ====================================================
            Main Workspace
        ==================================================== */}

        <main
          className="c3-studio-main"
          id="c3-workspace-content"
        >
          {/* ==================================================
              Workspace Context Header
          ================================================== */}

          <div className="c3-studio-context">
            <div>
              <span className="c3-studio-kicker">
                ACTIVE WORKSPACE
              </span>

              <h2>{activeWorkspace.heading}</h2>

              <p>{activeWorkspace.description}</p>
            </div>

            {activeTab === "prediction" && (
              <div className="c3-studio-context-stat">
                <strong>
                  {status === "online"
                    ? `${available} / 9`
                    : "—"}
                </strong>

                <small>Legacy checkpoints</small>
              </div>
            )}
          </div>

          {/* ==================================================
              01 — Research Pipeline
          ================================================== */}

          {activeTab === "pipeline" && (
            <C3ResearchPipeline
              onOpenEvaluation={() =>
                openWorkspace("evaluation")
              }
            />
          )}

          {/* ==================================================
              02 — Data Workspace
          ================================================== */}

          {activeTab === "datasets" && (
            <C3DatasetManager />
          )}

          {/* ==================================================
              03 — Model Training
          ================================================== */}

          {activeTab === "training" && (
            <C3TrainingWorkspace />
          )}

          {/* ==================================================
              04 — Model Evaluation
          ================================================== */}

          {activeTab === "evaluation" && (
            <C3ModelEvaluation />
          )}

          {/* ==================================================
              05 — Forecast Laboratory
          ================================================== */}

          {activeTab === "prediction" && (
            <>
              {/* ==============================================
                  Prediction Explorer
              ============================================== */}

              <section className="panel c3-prediction-explorer">
                <div className="panel-heading">
                  <div>
                    <span className="section-overline">
                      LEGACY CHECKPOINT INFERENCE
                    </span>

                    <h2>Prediction Explorer</h2>
                  </div>

                  <span className="live-chip">
                    M4 feature-augmented GRU
                  </span>
                </div>

                <p className="panel-subtitle">
                  Select a synthetic validation example,
                  choose an ablation and forecast horizon,
                  then execute the saved legacy checkpoint
                  through FastAPI. This workspace is not yet
                  connected to the newly trained active-model
                  registry.
                </p>

                {/* ============================================
                    Prediction Controls
                ============================================ */}

                <div className="c3-controls">
                  <label>
                    Forecast horizon

                    <select
                      value={horizon}
                      onChange={(event) => {
                        setHorizon(
                          Number(
                            event.target.value,
                          ) as Horizon,
                        );

                        setOffset(0);
                        setForecast(null);
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
                          M4-{value} —{" "}
                          {ablationNames[value]}
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
                        setSelectedId(
                          event.target.value,
                        );

                        setForecast(null);
                      }}
                    >
                      {examples.map(
                        (example, index) => (
                          <option
                            key={example.id}
                            value={example.id}
                          >
                            {offset + index + 1}.{" "}
                            {example.episode_id} ·{" "}
                            {
                              example.temporal_sequence
                                .steps.length
                            }{" "}
                            steps
                          </option>
                        ),
                      )}
                    </select>
                  </label>
                </div>

                {/* ============================================
                    Prediction Actions
                ============================================ */}

                <div className="c3-actions">
                  <button
                    type="button"
                    className="c3-primary-button"
                    onClick={() =>
                      void runForecast()
                    }
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
                      setOffset(
                        (value) => value + 10,
                      )
                    }
                  >
                    Next examples
                  </button>
                </div>

                {/* ============================================
                    Loading and Error Messages
                ============================================ */}

                {loadingExamples && (
                  <p className="c3-inline-note">
                    Loading validation examples…
                  </p>
                )}

                {!modelReady &&
                  status === "online" && (
                    <p className="c3-inline-note">
                      The selected legacy checkpoint is
                      unavailable for this horizon.
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

                {/* ============================================
                    Prediction Results
                ============================================ */}

                {selected && (
                  <>
                    <div className="c3-result-grid">
                      <div>
                        <span>
                          Observed input steps
                        </span>

                        <strong>
                          {
                            selected.temporal_sequence
                              .steps.length
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

                    {/* ========================================
                        Moisture Forecast Chart
                    ======================================== */}

                    <MoistureChart
                      example={selected}
                      forecast={forecast}
                    />

                    {/* ========================================
                        Prediction Metadata
                    ======================================== */}

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

                    {/* ========================================
                        Sensor Sequence
                    ======================================== */}

                    <div className="c3-steps">
                      <h3>
                        Sensor sequence and operating
                        modes
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

                {/* ============================================
                    Research Disclaimer
                ============================================ */}

                <p className="c3-research-warning">
                  Research-only demonstration using
                  synthetic validation data. Forecasts
                  estimate future soil moisture; they are
                  not landslide probabilities, operational
                  warnings, or evidence of real-world
                  accuracy.
                </p>
              </section>

              {/* ==============================================
                  Legacy Checkpoint Availability
              ============================================== */}

              <section className="panel c3-model-panel">
                <div className="panel-heading">
                  <div>
                    <span className="section-overline">
                      LEGACY CHECKPOINT STATUS
                    </span>

                    <h2>
                      Available trained models
                    </h2>
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
                        const isAvailable =
                          models.some(
                            (model) =>
                              model.model ===
                                `M4-${value}` &&
                              model.horizon_minutes ===
                                h &&
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

                <p className="c3-research-warning">
                  These are legacy M4 demonstration
                  checkpoints. They are separate from the
                  18 newly registered research model
                  candidates shown in Model Evaluation.
                </p>
              </section>
            </>
          )}

          {/* ==================================================
              06 — Adaptive Analysis
          ================================================== */}

          {activeTab === "adaptive" && (
            <C3AdaptiveMonitoring />
          )}
          {/* Active Forecasting Workspace */}
          {activeTab === "forecasting" && (
            <C3ActiveForecasting />
          )}
        </main>
      </div>
    </div>
  );
}