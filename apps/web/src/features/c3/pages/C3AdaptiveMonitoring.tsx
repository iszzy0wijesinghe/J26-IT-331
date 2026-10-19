/** @format */

import { useState } from "react";

import {
  c3AdaptiveApi,
  type C3AdaptiveReplayRequest,
  type C3AdaptiveReplayResponse,
  type C3AdaptiveReplayStep,
  type C3MonitoringMode,
} from "../api/c3AdaptiveApi";

import "../styles/c3AdaptiveMonitoring.css";

const DEFAULT_REQUEST: C3AdaptiveReplayRequest = {
  dataset_id: "c3raw_cf19059376cd4dd7",
  device_id: "GN-C3-005",
  episode_id: "SYN-EP-029",
  start_index: 32,
  observation_count: 12,
};

const MODES: C3MonitoringMode[] = [
  "DEEP_SLEEP",
  "IDLE",
  "RISK",
  "WARNING",
];

function formatNumber(value: number, digits = 2): string {
  return Number.isFinite(value)
    ? value.toLocaleString(undefined, {
        maximumFractionDigits: digits,
      })
    : "—";
}

function formatTime(value: string): string {
  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString();
}

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

function ModeBadge({ mode }: { mode: C3MonitoringMode }) {
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
        Forecast origin: {formatTime(step.forecast_origin)}
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
        Forecast values represent predicted soil moisture,
        not landslide probabilities.
      </p>
    </section>
  );
}

export function C3AdaptiveMonitoring() {
  const [request, setRequest] =
    useState<C3AdaptiveReplayRequest>(DEFAULT_REQUEST);

  const [result, setResult] =
    useState<C3AdaptiveReplayResponse | null>(null);

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runReplay(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setLoading(true);
    setError(null);
    setResult(null);
    setSelectedIndex(0);

    try {
      const response = await c3AdaptiveApi.replay(request);
      setResult(response);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to complete the adaptive replay.",
      );
    } finally {
      setLoading(false);
    }
  }

  const selectedStep = result?.decisions[selectedIndex];

  const modeCounts = MODES.map((mode) => ({
    mode,
    count:
      result?.decisions.filter(
        (step) => step.adaptive_decision.selected_mode === mode,
      ).length ?? 0,
  }));

  return (
    <div className="c3-adaptive-workspace">
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
          Replay historical synthetic observations through the active
          forecasting models and safety-constrained monitoring policy.
          Compare hypothetical energy consumption against fixed
          monitoring schedules.
        </p>

        <form className="c3-adaptive-form" onSubmit={runReplay}>
          <label>
            Dataset ID
            <input
              required
              value={request.dataset_id}
              onChange={(event) =>
                setRequest((previous) => ({
                  ...previous,
                  dataset_id: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Device ID
            <input
              required
              value={request.device_id}
              onChange={(event) =>
                setRequest((previous) => ({
                  ...previous,
                  device_id: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Episode ID
            <input
              required
              value={request.episode_id}
              onChange={(event) =>
                setRequest((previous) => ({
                  ...previous,
                  episode_id: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Start Index
            <input
              type="number"
              min={0}
              required
              value={request.start_index}
              onChange={(event) =>
                setRequest((previous) => ({
                  ...previous,
                  start_index: Number(event.target.value),
                }))
              }
            />
          </label>

          <label>
            Observations
            <input
              type="number"
              min={1}
              max={120}
              required
              value={request.observation_count}
              onChange={(event) =>
                setRequest((previous) => ({
                  ...previous,
                  observation_count: Number(event.target.value),
                }))
              }
            />
          </label>

          <button type="submit" disabled={loading}>
            {loading ? "Running Replay…" : "Run Adaptive Replay"}
          </button>
        </form>

        {error && (
          <p className="c3-adaptive-error" role="alert">
            {error}
          </p>
        )}
      </section>

      {result && (
        <div className="c3-adaptive-results">
          <div className="c3-adaptive-stats">
            <div className="stat-card">
              <span className="stat-label">REPLAY OBSERVATIONS</span>
              <div className="stat-value">
                {result.observation_count}
              </div>
              <span className="stat-foot">
                Historical synthetic observations
              </span>
            </div>

            <div className="stat-card">
              <span className="stat-label">ADAPTIVE CYCLES</span>
              <div className="stat-value">
                {result.energy_evaluation.adaptive.total_monitoring_cycles}
              </div>
              <span className="stat-foot">
                Modeled monitoring cycles
              </span>
            </div>

            <div className="stat-card">
              <span className="stat-label">MODELED ENERGY SAVING</span>
              <div className="stat-value">
                {formatNumber(
                  result.energy_evaluation.saving_vs_fixed_5s_pct,
                )}
                %
              </div>
              <span className="stat-foot">
                Compared with fixed 5-second sampling
              </span>
            </div>
          </div>

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
              {result.decisions.map((step, index) => (
                <button
                  type="button"
                  key={`${step.forecast_origin}-${index}`}
                  className={`c3-adaptive-timeline-item ${
                    selectedIndex === index ? "selected" : ""
                  }`}
                  onClick={() => setSelectedIndex(index)}
                  aria-pressed={selectedIndex === index}
                >
                  <span>#{index + 1}</span>
                  <ModeBadge
                    mode={step.adaptive_decision.selected_mode}
                  />
                  <strong>
                    {formatNumber(
                      step.adaptive_decision.monitoring_interval_s,
                      0,
                    )}
                    s
                  </strong>
                  <small>{formatTime(step.forecast_origin)}</small>
                </button>
              ))}
            </div>
          </section>

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
                    mode={selectedStep.adaptive_decision.selected_mode}
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
                      <li key={`${index}-${reason}`}>{reason}</li>
                    ),
                  )}
                </ul>
              </section>

              <ForecastInspector step={selectedStep} />
            </>
          )}

          <section className="panel c3-adaptive-section">
            <div className="panel-heading">
              <div>
                <span className="section-overline">
                  HYPOTHETICAL ENERGY MODEL
                </span>
                <h3>Energy Comparison</h3>
              </div>
            </div>

            <div className="c3-adaptive-energy-chart" role="img" aria-label="Comparison of modeled energy for adaptive and fixed sampling">
              {[
                { label: "Adaptive policy", value: result.energy_evaluation.adaptive.total_energy_mj, adaptive: true },
                ...result.energy_evaluation.fixed_baselines.map((baseline) => ({
                  label: `Fixed ${baseline.monitoring_interval_s}s`,
                  value: baseline.energy.total_energy_mj,
                  adaptive: false,
                })),
              ].map((row) => {
                const max = Math.max(1, result.energy_evaluation.adaptive.total_energy_mj,
                  ...result.energy_evaluation.fixed_baselines.map((baseline) => baseline.energy.total_energy_mj));
                return (
                  <div className="c3-adaptive-bar-row" key={row.label}>
                    <span>{row.label}</span>
                    <div className="c3-adaptive-bar-track">
                      <div className={row.adaptive ? "c3-adaptive-bar-fill is-adaptive" : "c3-adaptive-bar-fill"}
                        style={{ width: `${Math.max(0, row.value / max * 100)}%` }} />
                    </div>
                    <strong>{formatNumber(row.value, 0)} <small>mJ</small></strong>
                  </div>
                );
              })}
            </div>

            <p className="c3-adaptive-disclaimer">
              Energy values use assumed baseline power and per-cycle
              energy costs. They are not measured hardware consumption.
            </p>
          </section>

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
              Replay type: {result.replay_type.replaceAll("_", " ")}
            </p>

            <ul className="c3-adaptive-reasons">
              {result.limitations.map((limitation, index) => (
                <li key={`${index}-${limitation}`}>
                  {limitation}
                </li>
              ))}
            </ul>

            <p className="c3-adaptive-disclaimer">
              Historical replay is open-loop: monitoring decisions
              do not alter which historical observations are
              available to later decisions. Results are not
              field-validated landslide warnings.
            </p>
          </section>
        </div>
      )}
    </div>
  );
}
