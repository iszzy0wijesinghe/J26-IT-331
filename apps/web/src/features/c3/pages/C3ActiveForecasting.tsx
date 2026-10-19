/** @format */

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  c3ExplorerApi,
  type C3GoldenObservation,
  type C3ObservationFiltersResponse,
} from "../api/c3Api";

import {
  c3ForecastApi,
  type ForecastPrediction,
  type GenerateForecastResponse,
} from "../api/c3ForecastApi";

import "../styles/c3ActiveForecasting.css";

/* ============================================================
   Constants
   ============================================================ */

const ACTIVE_MODEL_DATASET_ID = "c3raw_cf19059376cd4dd7";

const OBSERVATION_PAGE_SIZE = 100;

const MIN_SEQUENCE_LENGTH = 3;
const MAX_SEQUENCE_LENGTH = 32;

const SENSOR_FIELDS: (keyof C3GoldenObservation)[] = [
  "soil_moisture_pct",
  "rainfall_proxy_counts",
  "tilt_deg",
  "vibration_g",
  "fsr_adc",
  "air_temperature_c",
  "humidity_pct",
];

type ForecastInput = {
  dataset_id: string;
  device_id: string;
  episode_id: string;
  forecast_origin: string;
};

const INITIAL_INPUT: ForecastInput = {
  dataset_id: "",
  device_id: "",
  episode_id: "",
  forecast_origin: "",
};

/* ============================================================
   Formatting
   ============================================================ */

function formatValue(value: number): string {
  return Number.isFinite(value)
    ? `${value.toFixed(2)}%`
    : "—";
}

function formatTimestamp(
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
   Observation Utilities
   ============================================================ */

async function loadAllObservations(
  datasetId: string,
  deviceId: string,
  episodeId: string | undefined,
  signal: AbortSignal,
): Promise<C3GoldenObservation[]> {
  const all: C3GoldenObservation[] = [];

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

    all.push(...response.observations);

    if (
      !response.has_more ||
      response.observations.length === 0
    ) {
      break;
    }

    offset += response.observations.length;
  }

  return all;
}

function hasValidSensors(
  observation: C3GoldenObservation,
): boolean {
  return SENSOR_FIELDS.every((field) => {
    const value = observation[field];

    return (
      typeof value === "number" &&
      Number.isFinite(value)
    );
  });
}

function getEligibleOrigins(
  observations: C3GoldenObservation[],
): string[] {
  const origins: string[] = [];

  const ordered = [...observations].sort((a, b) => {
    const timeDifference =
      new Date(a.timestamp).getTime() -
      new Date(b.timestamp).getTime();

    return timeDifference !== 0
      ? timeDifference
      : a.observation_id - b.observation_id;
  });

  const validObservations: C3GoldenObservation[] = [];

  for (const observation of ordered) {
    const timestamp = new Date(
      observation.timestamp,
    ).getTime();

    if (!Number.isFinite(timestamp)) {
      continue;
    }

    validObservations.push(observation);

    // The backend includes every observation at or before
    // the selected timestamp, then takes the latest 32.
    const historical = validObservations.slice(
      -MAX_SEQUENCE_LENGTH,
    );

    if (
      historical.length < MIN_SEQUENCE_LENGTH ||
      !historical.every(hasValidSensors)
    ) {
      continue;
    }

    origins.push(observation.timestamp);
  }

  return [...new Set(origins)];
}

/* ============================================================
   Component
   ============================================================ */

export function C3ActiveForecasting() {
  const [input, setInput] =
    useState<ForecastInput>(INITIAL_INPUT);

  const [filters, setFilters] =
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

  const [busy, setBusy] = useState(false);

  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [result, setResult] =
    useState<GenerateForecastResponse | null>(null);

  const [history, setHistory] =
    useState<ForecastPrediction[]>([]);

  /* ==========================================================
     Load Dataset Options
     ========================================================== */

  useEffect(() => {
    const controller = new AbortController();

    setFiltersLoading(true);

    c3ExplorerApi
      .filters(undefined, controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;

        setFilters(response);

        const preferredDataset =
          response.datasets.find(
            (dataset) =>
              dataset.dataset_id ===
              ACTIVE_MODEL_DATASET_ID,
          );

        if (preferredDataset) {
          setInput((previous) => ({
            ...previous,
            dataset_id: preferredDataset.dataset_id,
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
     Load Devices for Selected Dataset
     ========================================================== */

  const [datasetFilters, setDatasetFilters] =
    useState<C3ObservationFiltersResponse | null>(
      null,
    );

  useEffect(() => {
    if (!input.dataset_id) {
      setDatasetFilters(null);
      return;
    }

    const controller = new AbortController();

    setDevicesLoading(true);
    setDatasetFilters(null);

    c3ExplorerApi
      .filters(input.dataset_id, controller.signal)
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
  }, [input.dataset_id]);

  /* ==========================================================
     Load Device Observations to Discover Episodes
     ========================================================== */

  useEffect(() => {
    if (!input.dataset_id || !input.device_id) {
      setDeviceObservations([]);
      return;
    }

    const controller = new AbortController();

    setEpisodesLoading(true);
    setDeviceObservations([]);

    loadAllObservations(
      input.dataset_id,
      input.device_id,
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
            "Unable to load device episodes.",
          ),
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setEpisodesLoading(false);
        }
      });

    return () => controller.abort();
  }, [input.dataset_id, input.device_id]);

  /* ==========================================================
     Load Selected Episode
     ========================================================== */

  useEffect(() => {
    if (
      !input.dataset_id ||
      !input.device_id ||
      !input.episode_id
    ) {
      setEpisodeObservations([]);
      return;
    }

    const controller = new AbortController();

    setEpisodesLoading(true);
    setEpisodeObservations([]);

    loadAllObservations(
      input.dataset_id,
      input.device_id,
      input.episode_id,
      controller.signal,
    )
      .then((observations) => {
        if (controller.signal.aborted) return;

        setEpisodeObservations(observations);
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
    input.dataset_id,
    input.device_id,
    input.episode_id,
  ]);

  /* ==========================================================
     Derived Options
     ========================================================== */

  const devices = useMemo(
    () =>
      [...(datasetFilters?.devices ?? [])].sort(),
    [datasetFilters],
  );

  const episodes = useMemo(() => {
    return [
      ...new Set(
        deviceObservations.map(
          (observation) => observation.episode_id,
        ),
      ),
    ].sort();
  }, [deviceObservations]);

  const eligibleOrigins = useMemo(
    () => getEligibleOrigins(episodeObservations),
    [episodeObservations],
  );

  const activeDatasetMatches =
    input.dataset_id === ACTIVE_MODEL_DATASET_ID;

  const selectedOriginIsValid =
    eligibleOrigins.includes(input.forecast_origin);

  const canGenerate =
    !busy &&
    !filtersLoading &&
    !devicesLoading &&
    !episodesLoading &&
    activeDatasetMatches &&
    Boolean(input.dataset_id) &&
    Boolean(input.device_id) &&
    Boolean(input.episode_id) &&
    selectedOriginIsValid;

  /* ==========================================================
     Selection Handlers
     ========================================================== */

  function clearResults() {
    setResult(null);
    setHistory([]);
    setError("");
    setNotice("");
  }

  function changeDataset(datasetId: string) {
    setInput({
      dataset_id: datasetId,
      device_id: "",
      episode_id: "",
      forecast_origin: "",
    });

    setDeviceObservations([]);
    setEpisodeObservations([]);

    clearResults();
  }

  function changeDevice(deviceId: string) {
    setInput((previous) => ({
      ...previous,
      device_id: deviceId,
      episode_id: "",
      forecast_origin: "",
    }));

    setDeviceObservations([]);
    setEpisodeObservations([]);

    clearResults();
  }

  function changeEpisode(episodeId: string) {
    setInput((previous) => ({
      ...previous,
      episode_id: episodeId,
      forecast_origin: "",
    }));

    setEpisodeObservations([]);

    clearResults();
  }

  function changeOrigin(origin: string) {
    setInput((previous) => ({
      ...previous,
      forecast_origin: origin,
    }));

    clearResults();
  }

  /* ==========================================================
     Forecast Actions
     ========================================================== */

  async function generate() {
    if (!canGenerate) return;

    setBusy(true);
    setError("");
    setNotice("");

    try {
      const response = await c3ForecastApi.generate(
        input,
      );

      setResult(response);

      setNotice(
        "Forecasts generated and saved successfully.",
      );

      try {
        const saved = await c3ForecastApi.history(
          input.dataset_id,
          input.device_id,
          input.episode_id,
        );

        setHistory(saved.predictions);
      } catch (historyError) {
        setError(
          `Forecasts were saved, but history could not be loaded: ${
            getErrorMessage(
              historyError,
              "History retrieval failed.",
            )
          }`,
        );
      }
    } catch (caught) {
      setError(
        getErrorMessage(
          caught,
          "Forecast generation failed.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  async function loadHistory() {
    if (
      !input.dataset_id ||
      !input.device_id ||
      !input.episode_id
    ) {
      return;
    }

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
    } catch (caught) {
      setError(
        getErrorMessage(
          caught,
          "Unable to retrieve forecast history.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  const sortedPredictions = result
    ? [...result.predictions].sort(
        (a, b) =>
          a.horizon_minutes - b.horizon_minutes,
      )
    : [];

  /* ==========================================================
     Render
     ========================================================== */

  return (
    <div className="c3-active-forecasting">
      {/* ======================================================
          Configuration
      ====================================================== */}

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
          activated research models for 15-, 30-, and
          60-minute horizons.
        </p>

        <div className="c3-af-form">
          {/* Dataset */}

          <label className="c3-af-field">
            <span>Dataset</span>

            <select
              required
              value={input.dataset_id}
              disabled={busy || filtersLoading}
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

          <label className="c3-af-field">
            <span>Device</span>

            <select
              required
              value={input.device_id}
              disabled={
                busy ||
                !input.dataset_id ||
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
                <option key={device} value={device}>
                  {device}
                </option>
              ))}
            </select>
          </label>

          {/* Episode */}

          <label className="c3-af-field">
            <span>Episode</span>

            <select
              required
              value={input.episode_id}
              disabled={
                busy ||
                !input.device_id ||
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

          {/* Forecast Origin */}

          <label className="c3-af-field">
            <span>
              Forecast origin — Asia/Colombo
            </span>

            <select
              required
              value={input.forecast_origin}
              disabled={
                busy ||
                !input.episode_id ||
                episodesLoading
              }
              onChange={(event) =>
                changeOrigin(event.target.value)
              }
            >
              <option value="">
                {episodesLoading
                  ? "Loading observations..."
                  : "Select forecast origin"}
              </option>

              {eligibleOrigins.map((origin) => (
                <option key={origin} value={origin}>
                  {formatTimestamp(origin)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {/* Selection Information */}

        {input.episode_id && !episodesLoading && (
          <p className="c3-af-description">
            Episode observations:{" "}
            <strong>
              {episodeObservations.length}
            </strong>
            {" · "}
            Eligible forecast origins:{" "}
            <strong>
              {eligibleOrigins.length}
            </strong>
            {" · "}
            Maximum input window:{" "}
            <strong>
              {MAX_SEQUENCE_LENGTH} observations
            </strong>
          </p>
        )}

        {!activeDatasetMatches &&
          input.dataset_id && (
            <p className="c3-af-error" role="status">
              The currently activated forecasting
              models belong to a different dataset.
              Select the active-model dataset to
              generate forecasts.
            </p>
          )}

        {input.episode_id &&
          !episodesLoading &&
          eligibleOrigins.length === 0 && (
            <p className="c3-af-error" role="status">
              This episode does not contain an
              eligible forecasting window with at
              least three complete historical
              observations.
            </p>
          )}

        {/* Actions */}

        <div className="c3-af-actions">
          <button
            type="button"
            onClick={() => void generate()}
            disabled={!canGenerate}
          >
            {busy
              ? "Processing..."
              : "Generate forecasts"}
          </button>

          <button
            type="button"
            onClick={() => void loadHistory()}
            disabled={
              busy ||
              !input.dataset_id ||
              !input.device_id ||
              !input.episode_id
            }
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

      {/* ======================================================
          Forecast Results
      ====================================================== */}

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

      {/* ======================================================
          Forecast History
      ====================================================== */}

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
                  <th>Target</th>
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
                      {formatTimestamp(
                        prediction.target_timestamp,
                      )}
                    </td>

                    <td>
                      {prediction.horizon_minutes} min
                    </td>

                    <td>
                      {prediction.model_name}
                    </td>

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

      {/* ======================================================
          Research Limitations
      ====================================================== */}

      <section className="panel c3-af-limitation">
        <strong>Research limitations</strong>

        <p>
          These forecasts estimate future soil moisture
          using synthetic historical observations.
          They are not landslide probabilities,
          operational warnings, or evidence of
          field-validated accuracy.
        </p>
      </section>
    </div>
  );
}