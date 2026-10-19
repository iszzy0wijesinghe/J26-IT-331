import { useState } from "react";

import {
  c3ForecastApi,
  type ForecastPrediction,
  type GenerateForecastResponse,
} from "../api/c3ForecastApi";

import "../styles/c3ActiveForecasting.css";

const INITIAL_INPUT = {
  dataset_id: "c3raw_cf19059376cd4dd7",
  device_id: "GN-C3-001",
  episode_id: "SYN-EP-001",
  forecast_origin: "2026-02-01T09:55:00+00:00",
};

function formatValue(value: number): string {
  return `${value.toFixed(2)}%`;
}

function formatTimestamp(value: string): string {
  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString();
}

export function C3ActiveForecasting() {
  const [input, setInput] = useState(INITIAL_INPUT);

  const [result, setResult] =
    useState<GenerateForecastResponse | null>(null);

  const [history, setHistory] =
    useState<ForecastPrediction[]>([]);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const updateInput = (
    key: keyof typeof INITIAL_INPUT,
    value: string,
  ) => {
    setInput((previous) => ({
      ...previous,
      [key]: value,
    }));

    setResult(null);
    setHistory([]);
    setError("");
    setNotice("");
  };

  const generate = async () => {
    setBusy(true);
    setError("");
    setNotice("");

    try {
      const response = await c3ForecastApi.generate(input);

      setResult(response);

      const saved = await c3ForecastApi.history(
        input.dataset_id,
        input.device_id,
        input.episode_id,
      );

      setHistory(saved.predictions);

      setNotice(
        "Forecasts generated and saved successfully.",
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Forecast generation failed.",
      );
    } finally {
      setBusy(false);
    }
  };

  const loadHistory = async () => {
    setBusy(true);
    setError("");
    setNotice("");

    try {
      const response = await c3ForecastApi.history(
        input.dataset_id,
        input.device_id,
        input.episode_id,
      );

      setHistory(response.predictions);

      setNotice(
        `${response.total} saved forecast records retrieved.`,
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to retrieve forecast history.",
      );
    } finally {
      setBusy(false);
    }
  };

  const sortedPredictions = result
    ? [...result.predictions].sort(
        (a, b) => a.horizon_minutes - b.horizon_minutes,
      )
    : [];

  return (
    <div className="c3-active-forecasting">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="section-overline">
              ACTIVE MODEL INFERENCE
            </span>

            <h2>Historical forecasting</h2>
          </div>
        </div>

        <p className="c3-af-description">
          Generate soil-moisture forecasts using the
          activated research models for 15, 30, and
          60-minute horizons.
        </p>

        <div className="c3-af-form">
          {(
            [
              ["dataset_id", "Dataset ID"],
              ["device_id", "Device ID"],
              ["episode_id", "Episode ID"],
              ["forecast_origin", "Forecast origin (ISO 8601)"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="c3-af-field">
              <span>{label}</span>

              <input
                value={input[key]}
                onChange={(event) =>
                  updateInput(key, event.target.value)
                }
                disabled={busy}
                required
              />
            </label>
          ))}
        </div>

        <div className="c3-af-actions">
          <button
            type="button"
            onClick={() => void generate()}
            disabled={busy}
          >
            {busy ? "Processing..." : "Generate forecasts"}
          </button>

          <button
            type="button"
            onClick={() => void loadHistory()}
            disabled={busy}
            className="c3-af-secondary"
          >
            Load saved history
          </button>
        </div>

        {error && (
          <p className="c3-af-error" role="alert">
            {error}
          </p>
        )}

        {notice && (
          <p className="c3-af-notice" role="status">
            {notice}
          </p>
        )}
      </section>

      {result && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="section-overline">
                FORECAST RESULTS
              </span>

              <h2>Predicted soil moisture</h2>
            </div>
          </div>

          <div className="c3-af-results">
            {sortedPredictions.map((prediction) => (
              <article
                className="c3-af-result-card"
                key={prediction.prediction_id}
              >
                <span className="c3-af-horizon">
                  +{prediction.horizon_minutes} MIN
                </span>

                <strong className="c3-af-value">
                  {formatValue(
                    prediction.predicted_soil_moisture_pct,
                  )}
                </strong>

                <span className="c3-af-model">
                  {prediction.model_name}
                </span>

                <small>
                  Target:{" "}
                  {formatTimestamp(
                    prediction.target_timestamp,
                  )}
                </small>
              </article>
            ))}
          </div>

          <p className="c3-af-description">
            Forecast origin:{" "}
            {formatTimestamp(result.forecast_origin)}
          </p>
        </section>
      )}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="section-overline">
              PERSISTED PREDICTIONS
            </span>

            <h2>Forecast history</h2>
          </div>
        </div>

        {history.length === 0 ? (
          <p className="c3-af-description">
            No forecast records loaded.
          </p>
        ) : (
          <div className="c3-af-history">
            <table>
              <thead>
                <tr>
                  <th>Origin</th>
                  <th>Horizon</th>
                  <th>Model</th>
                  <th>Predicted moisture</th>
                </tr>
              </thead>

              <tbody>
                {history.map((prediction) => (
                  <tr key={prediction.prediction_id}>
                    <td>
                      {formatTimestamp(
                        prediction.forecast_origin,
                      )}
                    </td>

                    <td>
                      {prediction.horizon_minutes} min
                    </td>

                    <td>{prediction.model_name}</td>

                    <td>
                      {formatValue(
                        prediction.predicted_soil_moisture_pct,
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel c3-af-limitation">
        <strong>Research limitations</strong>

        <p>
          These forecasts estimate future soil moisture
          using synthetic historical observations.
          They are not landslide probabilities, operational
          warnings, or evidence of field-validated accuracy.
        </p>
      </section>
    </div>
  );
}