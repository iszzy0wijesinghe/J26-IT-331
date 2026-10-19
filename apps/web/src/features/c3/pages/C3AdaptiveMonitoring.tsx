/** @format */

import {
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";

import {
  c3ExplorerApi,
  type C3GoldenObservation,
  type C3ObservationFiltersResponse,
} from "../api/c3Api";

import {
  c3AdaptiveApi,
  type C3AdaptiveReplayRequest,
  type C3AdaptiveReplayResponse,
  type C3AdaptiveReplayStep,
  type C3MonitoringMode,
} from "../api/c3AdaptiveApi";

import "../styles/c3AdaptiveMonitoring.css";

/* ============================================================
   Constants
   ============================================================ */

const PREFERRED_DATASET_ID =
  "c3raw_cf19059376cd4dd7";

const OBSERVATION_PAGE_SIZE = 100;
const MAX_REPLAY_OBSERVATIONS = 120;
const MIN_CONTEXT_INDEX = 2;

const DEFAULT_REQUEST: C3AdaptiveReplayRequest = {
  dataset_id: "",
  device_id: "",
  episode_id: "",
  start_index: 32,
  observation_count: 12,
};

const MODES: C3MonitoringMode[] = [
  "DEEP_SLEEP",
  "IDLE",
  "RISK",
  "WARNING",
];

/* ============================================================
   Helpers
   ============================================================ */

function formatNumber(
  value: number,
  digits = 2,
): string {
  return Number.isFinite(value)
    ? value.toLocaleString(undefined, {
        maximumFractionDigits: digits,
      })
    : "—";
}

function formatTime(
  value?: string | null,
): string {
  if (!value) {
    return "Timestamp unavailable";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Invalid timestamp";
  }

  const formatted = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Colombo",
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  }).format(date);

  return `${formatted} (UTC+05:30)`;
}

function getErrorMessage(
  error: unknown,
  fallback: string,
): string {
  return error instanceof Error
    ? error.message
    : fallback;
}

/* ============================================================
   Observation Loading
   ============================================================ */

async function loadAllObservations(
  datasetId: string,
  deviceId: string,
  episodeId: string | undefined,
  signal: AbortSignal,
): Promise<C3GoldenObservation[]> {
  const observations: C3GoldenObservation[] = [];

  let offset = 0;

  while (true) {
    if (signal.aborted) {
      throw new DOMException(
        "Request aborted",
        "AbortError",
      );
    }

    const response = await c3ExplorerApi.list(
      {
        dataset_id: datasetId,
        device_id: deviceId,
        episode_id: episodeId,
        sort_by: "timestamp",
        sort_order: "asc",
        limit: OBSERVATION_PAGE_SIZE,
        offset,
      },
      signal,
    );

    observations.push(...response.observations);

    if (
      !response.has_more ||
      response.observations.length === 0
    ) {
      break;
    }

    offset += response.observations.length;
  }

  return observations;
}

/* ============================================================
   Forecast Inspector
   ============================================================ */

function getForecastDetails(
  forecast: Record<string, unknown>,
): {
  horizon: string;
  moisture: string;
  model: string;
} {
  const horizon =
    forecast.horizon_minutes ??
    forecast.forecast_horizon_minutes ??
    forecast.horizon ??
    "—";

  const moisture =
    forecast.forecast_soil_moisture_percent ??
    forecast.predicted_soil_moisture_pct ??
    forecast.predicted_value ??
    forecast.prediction ??
    null;

  const model =
    forecast.model ??
    forecast.model_name ??
    forecast.model_id ??
    "Active model";

  return {
    horizon: String(horizon),

    moisture:
      typeof moisture === "number"
        ? `${formatNumber(moisture)}%`
        : "—",

    model: String(model),
  };
}

function ModeBadge({
  mode,
}: {
  mode: C3MonitoringMode;
}) {
  return (
    <span
      className={`c3-adaptive-mode c3-adaptive-mode--${mode.toLowerCase()}`}
    >
      {mode.replace("_", " ")}
    </span>
  );
}

function ForecastInspector({
  step,
}: {
  step: C3AdaptiveReplayStep;
}) {
  return (
    <section className="panel c3-adaptive-section">
      <div className="panel-heading">
        <div>
          <span className="section-overline">
            ACTIVE MODEL INFERENCE
          </span>

          <h3>Moisture Forecasts</h3>
        </div>
      </div>

      <p className="c3-adaptive-muted">
        Forecast origin:{" "}
        {formatTime(step.forecast_origin)}
      </p>

      <div className="c3-adaptive-forecast-grid">
        {step.forecasts.map((forecast, index) => {
          const details = getForecastDetails(forecast);

          return (
            <div
              className="c3-adaptive-forecast-card"
              key={`${details.horizon}-${index}`}
            >
              <span className="c3-adaptive-muted">
                +{details.horizon} minutes
              </span>

              <strong>{details.moisture}</strong>

              <small>{details.model}</small>
            </div>
          );
        })}
      </div>

      <p className="c3-adaptive-disclaimer">
        Forecast values represent predicted soil
        moisture, not landslide probabilities.
      </p>
    </section>
  );
}

/* ============================================================
   Component
   ============================================================ */

export function C3AdaptiveMonitoring() {
  const [request, setRequest] =
    useState<C3AdaptiveReplayRequest>(
      DEFAULT_REQUEST,
    );

  const [filters, setFilters] =
    useState<C3ObservationFiltersResponse | null>(
      null,
    );

  const [datasetFilters, setDatasetFilters] =
    useState<C3ObservationFiltersResponse | null>(
      null,
    );

  const [deviceObservations, setDeviceObservations] =
    useState<C3GoldenObservation[]>([]);

  const [episodeObservations, setEpisodeObservations] =
    useState<C3GoldenObservation[]>([]);

  const [filtersLoading, setFiltersLoading] =
    useState(true);

  const [devicesLoading, setDevicesLoading] =
    useState(false);

  const [episodesLoading, setEpisodesLoading] =
    useState(false);

  const [loading, setLoading] = useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [result, setResult] =
    useState<C3AdaptiveReplayResponse | null>(
      null,
    );

  const [selectedIndex, setSelectedIndex] =
    useState(0);

  /* ==========================================================
     Load Datasets
     ========================================================== */

  useEffect(() => {
    const controller = new AbortController();

    setFiltersLoading(true);

    c3ExplorerApi
      .filters(undefined, controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;

        setFilters(response);

        const preferred = response.datasets.find(
          (dataset) =>
            dataset.dataset_id ===
            PREFERRED_DATASET_ID,
        );

        if (preferred) {
          setRequest((previous) => ({
            ...previous,
            dataset_id: preferred.dataset_id,
          }));
        }
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;

        setError(
          getErrorMessage(
            cause,
            "Unable to load datasets.",
          ),
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setFiltersLoading(false);
        }
      });

    return () => controller.abort();
  }, []);

  /* ==========================================================
     Load Devices
     ========================================================== */

  useEffect(() => {
    if (!request.dataset_id) {
      setDatasetFilters(null);
      return;
    }

    const controller = new AbortController();

    setDevicesLoading(true);
    setDatasetFilters(null);

    c3ExplorerApi
      .filters(
        request.dataset_id,
        controller.signal,
      )
      .then((response) => {
        if (controller.signal.aborted) return;

        setDatasetFilters(response);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;

        setError(
          getErrorMessage(
            cause,
            "Unable to load devices.",
          ),
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setDevicesLoading(false);
        }
      });

    return () => controller.abort();
  }, [request.dataset_id]);

  /* ==========================================================
     Discover Episodes for Selected Device
     ========================================================== */

  useEffect(() => {
    if (
      !request.dataset_id ||
      !request.device_id
    ) {
      setDeviceObservations([]);
      return;
    }

    const controller = new AbortController();

    setEpisodesLoading(true);
    setDeviceObservations([]);

    loadAllObservations(
      request.dataset_id,
      request.device_id,
      undefined,
      controller.signal,
    )
      .then((observations) => {
        if (controller.signal.aborted) return;

        setDeviceObservations(observations);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;

        setError(
          getErrorMessage(
            cause,
            "Unable to load episodes.",
          ),
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setEpisodesLoading(false);
        }
      });

    return () => controller.abort();
  }, [request.dataset_id, request.device_id]);

  /* ==========================================================
     Load Selected Episode
     ========================================================== */

  useEffect(() => {
    if (
      !request.dataset_id ||
      !request.device_id ||
      !request.episode_id
    ) {
      setEpisodeObservations([]);
      return;
    }

    const controller = new AbortController();

    setEpisodesLoading(true);
    setEpisodeObservations([]);

    loadAllObservations(
      request.dataset_id,
      request.device_id,
      request.episode_id,
      controller.signal,
    )
      .then((observations) => {
        if (controller.signal.aborted) return;

        setEpisodeObservations(observations);

        const maxStart = observations.length - 1;

        if (maxStart >= MIN_CONTEXT_INDEX) {
          const startIndex = Math.min(
            32,
            maxStart,
          );

          const remaining =
            observations.length - startIndex;

          setRequest((previous) => ({
            ...previous,
            start_index: startIndex,
            observation_count: Math.min(
              12,
              MAX_REPLAY_OBSERVATIONS,
              remaining,
            ),
          }));
        }
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;

        setError(
          getErrorMessage(
            cause,
            "Unable to load episode observations.",
          ),
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setEpisodesLoading(false);
        }
      });

    return () => controller.abort();
  }, [
    request.dataset_id,
    request.device_id,
    request.episode_id,
  ]);

  /* ==========================================================
     Derived Options
     ========================================================== */

  const devices = useMemo(
    () =>
      [...(datasetFilters?.devices ?? [])].sort(),
    [datasetFilters],
  );

  const episodes = useMemo(
    () =>
      [
        ...new Set(
          deviceObservations.map(
            (observation) =>
              observation.episode_id,
          ),
        ),
      ].sort(),
    [deviceObservations],
  );

  const observationTotal =
    episodeObservations.length;

  const maxStartIndex = Math.max(
    0,
    observationTotal - 1,
  );

  const remainingObservations = Math.max(
    0,
    observationTotal - request.start_index,
  );

  const maxObservationCount = Math.min(
    MAX_REPLAY_OBSERVATIONS,
    remainingObservations,
  );

  const configurationValid =
    Boolean(request.dataset_id) &&
    Boolean(request.device_id) &&
    Boolean(request.episode_id) &&
    !filtersLoading &&
    !devicesLoading &&
    !episodesLoading &&
    Number.isInteger(request.start_index) &&
    request.start_index >= MIN_CONTEXT_INDEX &&
    request.start_index <= maxStartIndex &&
    Number.isInteger(request.observation_count) &&
    request.observation_count >= 1 &&
    request.observation_count <=
      maxObservationCount;

  const canReplay =
    configurationValid && !loading;

  const selectedStep =
    result?.decisions[selectedIndex];

  const modeCounts = MODES.map((mode) => ({
    mode,

    count:
      result?.decisions.filter(
        (step) =>
          step.adaptive_decision.selected_mode ===
          mode,
      ).length ?? 0,
  }));

  /* ==========================================================
     Selection Handlers
     ========================================================== */

  function clearResults() {
    setResult(null);
    setSelectedIndex(0);
    setError(null);
  }

  function changeDataset(datasetId: string) {
    setRequest({
      ...DEFAULT_REQUEST,
      dataset_id: datasetId,
    });

    setDeviceObservations([]);
    setEpisodeObservations([]);

    clearResults();
  }

  function changeDevice(deviceId: string) {
    setRequest((previous) => ({
      ...previous,
      device_id: deviceId,
      episode_id: "",
      start_index: 32,
      observation_count: 12,
    }));

    setDeviceObservations([]);
    setEpisodeObservations([]);

    clearResults();
  }

  function changeEpisode(episodeId: string) {
    setRequest((previous) => ({
      ...previous,
      episode_id: episodeId,
      start_index: 32,
      observation_count: 12,
    }));

    setEpisodeObservations([]);

    clearResults();
  }

  function changeStartIndex(value: number) {
    const remaining = Math.max(
      0,
      observationTotal - value,
    );

    setRequest((previous) => ({
      ...previous,
      start_index: value,
      observation_count: Math.min(
        previous.observation_count,
        MAX_REPLAY_OBSERVATIONS,
        remaining,
      ),
    }));

    clearResults();
  }

  function changeObservationCount(value: number) {
    setRequest((previous) => ({
      ...previous,
      observation_count: value,
    }));

    clearResults();
  }

  /* ==========================================================
     Run Replay
     ========================================================== */

  async function runReplay(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!canReplay) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setSelectedIndex(0);

    try {
      const response = await c3AdaptiveApi.replay(
        request,
      );

      setResult(response);
    } catch (caught) {
      setError(
        getErrorMessage(
          caught,
          "Unable to complete the adaptive replay.",
        ),
      );
    } finally {
      setLoading(false);
    }
  }

  /* ==========================================================
     Render
     ========================================================== */

  return (
    <div className="c3-adaptive-workspace">
      {/* ======================================================
          Replay Configuration
      ====================================================== */}

      <section className="c3-adaptive-intro">
        <div className="panel-heading">
          <div>
            <span className="section-overline">
              COMPONENT 03 · RESEARCH WORKBENCH
            </span>

            <h2>Replay configuration</h2>
          </div>
        </div>

        <p className="c3-adaptive-muted">
          Replay historical synthetic observations
          through the active forecasting models and
          safety-constrained monitoring policy.
          Compare hypothetical energy consumption
          against fixed monitoring schedules.
        </p>

        <form
          className="c3-adaptive-form"
          onSubmit={runReplay}
        >
          {/* Dataset */}

          <label>
            Dataset

            <select
              required
              value={request.dataset_id}
              disabled={loading || filtersLoading}
              onChange={(event) =>
                changeDataset(event.target.value)
              }
            >
              <option value="">
                {filtersLoading
                  ? "Loading datasets..."
                  : "Select dataset"}
              </option>

              {filters?.datasets.map((dataset) => (
                <option
                  key={dataset.dataset_id}
                  value={dataset.dataset_id}
                >
                  {dataset.filename}
                </option>
              ))}
            </select>
          </label>

          {/* Device */}

          <label>
            Device

            <select
              required
              value={request.device_id}
              disabled={
                loading ||
                !request.dataset_id ||
                devicesLoading
              }
              onChange={(event) =>
                changeDevice(event.target.value)
              }
            >
              <option value="">
                {devicesLoading
                  ? "Loading devices..."
                  : "Select device"}
              </option>

              {devices.map((device) => (
                <option
                  key={device}
                  value={device}
                >
                  {device}
                </option>
              ))}
            </select>
          </label>

          {/* Episode */}

          <label>
            Episode

            <select
              required
              value={request.episode_id}
              disabled={
                loading ||
                !request.device_id ||
                episodesLoading
              }
              onChange={(event) =>
                changeEpisode(event.target.value)
              }
            >
              <option value="">
                {episodesLoading
                  ? "Loading episodes..."
                  : "Select episode"}
              </option>

              {episodes.map((episode) => (
                <option
                  key={episode}
                  value={episode}
                >
                  {episode}
                </option>
              ))}
            </select>
          </label>

          {/* Start Index */}

          <label>
            Start Index

            <input
              type="number"
              required
              min={MIN_CONTEXT_INDEX}
              max={Math.max(
                MIN_CONTEXT_INDEX,
                maxStartIndex,
              )}
              step={1}
              value={request.start_index}
              disabled={
                loading ||
                !request.episode_id ||
                episodesLoading ||
                observationTotal < 3
              }
              onChange={(event) =>
                changeStartIndex(
                  Number(event.target.value),
                )
              }
            />
          </label>

          {/* Observation Count */}

          <label>
            Observations

            <input
              type="number"
              required
              min={1}
              max={Math.max(
                1,
                maxObservationCount,
              )}
              step={1}
              value={request.observation_count}
              disabled={
                loading ||
                !request.episode_id ||
                episodesLoading ||
                observationTotal < 3
              }
              onChange={(event) =>
                changeObservationCount(
                  Number(event.target.value),
                )
              }
            />
          </label>

          <button
            type="submit"
            disabled={!canReplay}
          >
            {loading
              ? "Running Replay…"
              : "Run Adaptive Replay"}
          </button>
        </form>

        {/* Episode Information */}

        {request.episode_id &&
          !episodesLoading && (
            <p className="c3-adaptive-muted">
              Episode observations:{" "}
              <strong>{observationTotal}</strong>
              {" · "}
              Available from selected index:{" "}
              <strong>
                {remainingObservations}
              </strong>
              {" · "}
              Maximum replay observations:{" "}
              <strong>
                {MAX_REPLAY_OBSERVATIONS}
              </strong>
            </p>
          )}

        {request.episode_id &&
          !episodesLoading &&
          observationTotal < 3 && (
            <p
              className="c3-adaptive-error"
              role="status"
            >
              At least three historical observations
              are required before adaptive replay
              can begin.
            </p>
          )}

        {error && (
          <p
            className="c3-adaptive-error"
            role="alert"
          >
            {error}
          </p>
        )}
      </section>

      {/* ======================================================
          Replay Results
      ====================================================== */}

      {result && (
        <div className="c3-adaptive-results">
          {/* ==================================================
              Summary Statistics
          ================================================== */}

          <div className="c3-adaptive-stats">
            <div className="stat-card">
              <span className="stat-label">
                REPLAY OBSERVATIONS
              </span>

              <div className="stat-value">
                {result.observation_count}
              </div>

              <span className="stat-foot">
                Historical synthetic observations
              </span>
            </div>

            <div className="stat-card">
              <span className="stat-label">
                ADAPTIVE CYCLES
              </span>

              <div className="stat-value">
                {
                  result.energy_evaluation.adaptive
                    .total_monitoring_cycles
                }
              </div>

              <span className="stat-foot">
                Modeled monitoring cycles
              </span>
            </div>

            <div className="stat-card">
              <span className="stat-label">
                MODELED ENERGY SAVING
              </span>

              <div className="stat-value">
                {formatNumber(
                  result.energy_evaluation
                    .saving_vs_fixed_5s_pct,
                )}
                %
              </div>

              <span className="stat-foot">
                Compared with fixed 5-second
                sampling
              </span>
            </div>
          </div>

          {/* ==================================================
              Monitoring Mode Timeline
          ================================================== */}

          <section className="panel c3-adaptive-section">
            <div className="panel-heading">
              <div>
                <span className="section-overline">
                  SAFETY-CONSTRAINED MODE CONTROL
                </span>

                <h3>Monitoring Mode Timeline</h3>
              </div>
            </div>

            <div className="c3-adaptive-mode-summary">
              {modeCounts.map(({ mode, count }) => (
                <div key={mode}>
                  <ModeBadge mode={mode} />
                  <strong>{count}</strong>
                </div>
              ))}
            </div>

            <div
              className="c3-adaptive-timeline"
              aria-label="Monitoring decisions in chronological order"
            >
              {result.decisions.map(
                (step, index) => (
                  <button
                    type="button"
                    key={`${step.forecast_origin}-${index}`}
                    className={`c3-adaptive-timeline-item ${
                      selectedIndex === index
                        ? "selected"
                        : ""
                    }`}
                    onClick={() =>
                      setSelectedIndex(index)
                    }
                    aria-pressed={
                      selectedIndex === index
                    }
                  >
                    <span>#{index + 1}</span>

                    <ModeBadge
                      mode={
                        step.adaptive_decision
                          .selected_mode
                      }
                    />

                    <strong>
                      {formatNumber(
                        step.adaptive_decision
                          .monitoring_interval_s,
                        0,
                      )}
                      s
                    </strong>

                    <small>
                      {formatTime(
                        step.forecast_origin,
                      )}
                    </small>
                  </button>
                ),
              )}
            </div>
          </section>

          {/* ==================================================
              Selected Decision
          ================================================== */}

          {selectedStep && (
            <>
              <section className="panel c3-adaptive-section">
                <div className="panel-heading">
                  <div>
                    <span className="section-overline">
                      SELECTED DECISION
                    </span>

                    <h3>Safety Policy Inspection</h3>
                  </div>

                  <ModeBadge
                    mode={
                      selectedStep.adaptive_decision
                        .selected_mode
                    }
                  />
                </div>

                <div className="c3-adaptive-detail-grid">
                  <div>
                    <span className="c3-adaptive-muted">
                      Monitoring interval
                    </span>

                    <strong>
                      {
                        selectedStep.adaptive_decision
                          .monitoring_interval_s
                      }
                      s
                    </strong>
                  </div>

                  <div>
                    <span className="c3-adaptive-muted">
                      Stable evaluations
                    </span>

                    <strong>
                      {
                        selectedStep.adaptive_decision
                          .stable_evaluation_count
                      }
                    </strong>
                  </div>

                  <div>
                    <span className="c3-adaptive-muted">
                      Safety override
                    </span>

                    <strong>
                      {selectedStep.adaptive_decision
                        .safety_override_applied
                        ? "Applied"
                        : "Not applied"}
                    </strong>
                  </div>
                </div>

                <h4>Decision Reasons</h4>

                <ul className="c3-adaptive-reasons">
                  {selectedStep.adaptive_decision.reasons.map(
                    (reason, index) => (
                      <li key={`${index}-${reason}`}>
                        {reason}
                      </li>
                    ),
                  )}
                </ul>
              </section>

              <ForecastInspector step={selectedStep} />
            </>
          )}

          {/* ==================================================
              Energy Comparison
          ================================================== */}

          <section className="panel c3-adaptive-section">
            <div className="panel-heading">
              <div>
                <span className="section-overline">
                  HYPOTHETICAL ENERGY MODEL
                </span>

                <h3>Energy Comparison</h3>
              </div>
            </div>

            <div
              className="c3-adaptive-energy-chart"
              role="img"
              aria-label="Comparison of modeled energy for adaptive and fixed sampling"
            >
              {[
                {
                  label: "Adaptive policy",
                  value:
                    result.energy_evaluation.adaptive
                      .total_energy_mj,
                  adaptive: true,
                },
                ...result.energy_evaluation.fixed_baselines.map(
                  (baseline) => ({
                    label: `Fixed ${baseline.monitoring_interval_s}s`,
                    value:
                      baseline.energy.total_energy_mj,
                    adaptive: false,
                  }),
                ),
              ].map((row) => {
                const max = Math.max(
                  1,
                  result.energy_evaluation.adaptive
                    .total_energy_mj,
                  ...result.energy_evaluation.fixed_baselines.map(
                    (baseline) =>
                      baseline.energy.total_energy_mj,
                  ),
                );

                return (
                  <div
                    className="c3-adaptive-bar-row"
                    key={row.label}
                  >
                    <span>{row.label}</span>

                    <div className="c3-adaptive-bar-track">
                      <div
                        className={
                          row.adaptive
                            ? "c3-adaptive-bar-fill is-adaptive"
                            : "c3-adaptive-bar-fill"
                        }
                        style={{
                          width: `${Math.max(
                            0,
                            (row.value / max) * 100,
                          )}%`,
                        }}
                      />
                    </div>

                    <strong>
                      {formatNumber(row.value, 0)}{" "}
                      <small>mJ</small>
                    </strong>
                  </div>
                );
              })}
            </div>

            <p className="c3-adaptive-disclaimer">
              Energy values use assumed baseline
              power and per-cycle energy costs.
              They are not measured hardware
              consumption.
            </p>
          </section>

          {/* ==================================================
              Research Limitations
          ================================================== */}

          <section className="panel c3-adaptive-section">
            <div className="panel-heading">
              <div>
                <span className="section-overline">
                  RESEARCH TRANSPARENCY
                </span>

                <h3>Limitations and Assumptions</h3>
              </div>
            </div>

            <p className="c3-adaptive-muted">
              Replay type:{" "}
              {result.replay_type.replaceAll(
                "_",
                " ",
              )}
            </p>

            <ul className="c3-adaptive-reasons">
              {result.limitations.map(
                (limitation, index) => (
                  <li key={`${index}-${limitation}`}>
                    {limitation}
                  </li>
                ),
              )}
            </ul>

            <p className="c3-adaptive-disclaimer">
              Historical replay is open-loop:
              monitoring decisions do not alter
              which historical observations are
              available to later decisions.
              Results are not field-validated
              landslide warnings.
            </p>
          </section>
        </div>
      )}
    </div>
  );
}