/** @format */

import { useEffect, useMemo, useState } from "react";

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
   Configuration
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

const FORECAST_HORIZONS = [15, 30, 60] as const;

type ForecastMode = "latest" | "historical";

type ForecastInput = {
  dataset_id: string;
  device_id: string;
  episode_id: string;
  forecast_origin: string;
};

type ForecastPoint = {
  timestamp: string;
  value: number;
  type: "observed" | "predicted";
  horizon?: number;
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

function formatValue(value?: number | null): string {
  if (
    typeof value !== "number" ||
    !Number.isFinite(value)
  ) {
    return "—";
  }

  return `${value.toFixed(2)}%`;
}

function formatTimestamp(
  value?: string | null,
): string {
  if (!value) {
    return "—";
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

function formatShortTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Colombo",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(date);
}

function formatShortDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Colombo",
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

function addMinutes(
  timestamp: string,
  minutes: number,
): string {
  const date = new Date(timestamp);

  return new Date(
    date.getTime() + minutes * 60_000,
  ).toISOString();
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

function sortObservations(
  observations: C3GoldenObservation[],
): C3GoldenObservation[] {
  return [...observations].sort((a, b) => {
    const difference =
      new Date(a.timestamp).getTime() -
      new Date(b.timestamp).getTime();

    return difference !== 0
      ? difference
      : a.observation_id - b.observation_id;
  });
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

/**
 * An origin is eligible when the latest backend-equivalent
 * historical window has at least 3 complete observations.
 *
 * All observations sharing a timestamp are included before
 * checking eligibility, matching the backend's <= origin rule.
 */
function getEligibleOrigins(
  observations: C3GoldenObservation[],
): string[] {
  const ordered = sortObservations(observations);

  const eligible: string[] = [];

  let index = 0;

  while (index < ordered.length) {
    const currentTime = new Date(
      ordered[index].timestamp,
    ).getTime();

    if (!Number.isFinite(currentTime)) {
      index += 1;
      continue;
    }

    let nextIndex = index + 1;

    while (
      nextIndex < ordered.length &&
      new Date(
        ordered[nextIndex].timestamp,
      ).getTime() === currentTime
    ) {
      nextIndex += 1;
    }

    const historical = ordered.slice(
      0,
      nextIndex,
    );

    const window = historical.slice(
      -MAX_SEQUENCE_LENGTH,
    );

    if (
      window.length >= MIN_SEQUENCE_LENGTH &&
      window.every(hasValidSensors)
    ) {
      eligible.push(
        ordered[nextIndex - 1].timestamp,
      );
    }

    index = nextIndex;
  }

  return eligible;
}

/* ============================================================
   Chart
   ============================================================ */

type ForecastChartProps = {
  observations: C3GoldenObservation[];
  origin: string;
  predictions: ForecastPrediction[];
};

function ForecastChart({
  observations,
  origin,
  predictions,
}: ForecastChartProps) {
  const points = useMemo(() => {
    const originTime = new Date(origin).getTime();

    const observed = sortObservations(observations)
      .filter(
        (observation) =>
          new Date(observation.timestamp).getTime() <=
            originTime &&
          Number.isFinite(
            observation.soil_moisture_pct,
          ),
      )
      .slice(-MAX_SEQUENCE_LENGTH)
      .map<ForecastPoint>((observation) => ({
        timestamp: observation.timestamp,
        value: observation.soil_moisture_pct,
        type: "observed",
      }));

    const predicted = predictions
      .filter((prediction) =>
        Number.isFinite(
          prediction.predicted_soil_moisture_pct,
        ),
      )
      .map<ForecastPoint>((prediction) => ({
        timestamp: prediction.target_timestamp,
        value:
          prediction.predicted_soil_moisture_pct,
        type: "predicted",
        horizon: prediction.horizon_minutes,
      }))
      .sort(
        (a, b) =>
          new Date(a.timestamp).getTime() -
          new Date(b.timestamp).getTime(),
      );

    return { observed, predicted };
  }, [observations, origin, predictions]);

  const allPoints = [
    ...points.observed,
    ...points.predicted,
  ];

  if (allPoints.length < 2) {
    return (
      <p className="c3-af-description">
        Not enough data to display the forecast chart.
      </p>
    );
  }

  const width = 1000;
  const height = 330;

  const left = 65;
  const right = 30;
  const top = 30;
  const bottom = 65;

  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;

  const values = allPoints.map((point) => point.value);

  const minimumValue = Math.min(...values);
  const maximumValue = Math.max(...values);

  const valuePadding = Math.max(
    0.5,
    (maximumValue - minimumValue) * 0.2,
  );

  const minY = Math.max(
    0,
    minimumValue - valuePadding,
  );

  const maxY = Math.min(
    100,
    maximumValue + valuePadding,
  );

  const timeValues = allPoints.map((point) =>
    new Date(point.timestamp).getTime(),
  );

  const minX = Math.min(...timeValues);
  const maxX = Math.max(...timeValues);

  const xRange = Math.max(1, maxX - minX);
  const yRange = Math.max(0.0001, maxY - minY);

  function x(timestamp: string): number {
    const time = new Date(timestamp).getTime();

    return (
      left +
      ((time - minX) / xRange) * plotWidth
    );
  }

  function y(value: number): number {
    return (
      top +
      (1 - (value - minY) / yRange) *
        plotHeight
    );
  }

  function linePath(
    data: ForecastPoint[],
  ): string {
    return data
      .map(
        (point, index) =>
          `${index === 0 ? "M" : "L"} ${x(
            point.timestamp,
          )} ${y(point.value)}`,
      )
      .join(" ");
  }

  const lastObserved =
    points.observed[points.observed.length - 1];

  const forecastPath = lastObserved
    ? linePath([
        lastObserved,
        ...points.predicted,
      ])
    : linePath(points.predicted);

  const originX = x(origin);

  const yTicks = Array.from(
    { length: 5 },
    (_, index) =>
      minY + ((maxY - minY) * index) / 4,
  );

  const xTicks = [
    minX,
    minX + (maxX - minX) * 0.25,
    minX + (maxX - minX) * 0.5,
    minX + (maxX - minX) * 0.75,
    maxX,
  ];

  return (
    <div className="c3-af-chart">
      <div className="c3-af-chart-header">
        <div>
          <h3>Historical observations → Future forecasts</h3>

          <p>
            The blue series contains recorded synthetic
            observations. The orange series contains
            predictions generated by activated models.
          </p>
        </div>

        <span className="c3-af-chart-badge">
          HISTORICAL REPLAY
        </span>
      </div>

      <div className="c3-af-chart-scroll">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label="Soil moisture over time. Historical observations are blue, future model predictions are orange."
        >
          {yTicks.map((tick) => (
            <g key={tick}>
              <line
                x1={left}
                x2={width - right}
                y1={y(tick)}
                y2={y(tick)}
                className="c3-af-grid-line"
              />

              <text
                x={left - 12}
                y={y(tick) + 4}
                textAnchor="end"
                className="c3-af-axis-label"
              >
                {tick.toFixed(1)}%
              </text>
            </g>
          ))}

          {xTicks.map((tick, index) => {
            const timestamp = new Date(
              tick,
            ).toISOString();

            return (
              <text
                key={index}
                x={left + (index / 4) * plotWidth}
                y={height - 30}
                textAnchor="middle"
                className="c3-af-axis-label"
              >
                {formatShortTime(timestamp)}
              </text>
            );
          })}

          <line
            x1={originX}
            x2={originX}
            y1={top}
            y2={height - bottom}
            className="c3-af-origin-line"
          />

          <text
            x={Math.min(
              originX + 8,
              width - 130,
            )}
            y={top + 15}
            className="c3-af-origin-label"
          >
            Forecast origin
          </text>

          <path
            d={linePath(points.observed)}
            className="c3-af-observed-line"
          />

          <path
            d={forecastPath}
            className="c3-af-predicted-line"
          />

          {points.observed.map((point, index) => (
            <circle
              key={`observed-${index}`}
              cx={x(point.timestamp)}
              cy={y(point.value)}
              r={3.5}
              className="c3-af-observed-point"
            >
              <title>
                {`${formatTimestamp(
                  point.timestamp,
                )}: ${formatValue(point.value)}`}
              </title>
            </circle>
          ))}

          {points.predicted.map((point, index) => (
            <circle
              key={`predicted-${index}`}
              cx={x(point.timestamp)}
              cy={y(point.value)}
              r={6}
              className="c3-af-predicted-point"
            >
              <title>
                {`+${
                  point.horizon
                } minutes: ${formatValue(
                  point.value,
                )} at ${formatTimestamp(
                  point.timestamp,
                )}`}
              </title>
            </circle>
          ))}

          <text
            x={width / 2}
            y={height - 4}
            textAnchor="middle"
            className="c3-af-axis-title"
          >
            Observation / forecast time (Asia/Colombo)
          </text>

          <text
            x={18}
            y={height / 2}
            textAnchor="middle"
            transform={`rotate(-90 18 ${
              height / 2
            })`}
            className="c3-af-axis-title"
          >
            Soil moisture (%)
          </text>
        </svg>
      </div>

      <div className="c3-af-chart-legend">
        <span>
          <i className="c3-af-legend-observed" />
          Historical observations
        </span>

        <span>
          <i className="c3-af-legend-predicted" />
          Model-generated predictions
        </span>

        <span>
          <i className="c3-af-legend-origin" />
          Forecast boundary
        </span>
      </div>

      <p className="c3-af-chart-footnote">
        Predictions are independent horizon-specific
        estimates. The orange line connects them for
        visualization; it does not represent a continuous
        forecast or intermediate predictions.
      </p>
    </div>
  );
}

/* ============================================================
   Main Component
   ============================================================ */

export function C3ActiveForecasting() {
  const [input, setInput] =
    useState<ForecastInput>(INITIAL_INPUT);

  const [forecastMode, setForecastMode] =
    useState<ForecastMode>("latest");

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

  const [deviceDataLoading, setDeviceDataLoading] =
    useState(false);

  const [episodeDataLoading, setEpisodeDataLoading] =
    useState(false);

  const [busy, setBusy] = useState(false);

  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [result, setResult] =
    useState<GenerateForecastResponse | null>(null);

  const [history, setHistory] =
    useState<ForecastPrediction[]>([]);

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

        const preferred =
          response.datasets.find(
            (dataset) =>
              dataset.dataset_id ===
              ACTIVE_MODEL_DATASET_ID,
          );

        if (preferred) {
          setInput((previous) => ({
            ...previous,
            dataset_id: preferred.dataset_id,
          }));
        }
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            getErrorMessage(
              cause,
              "Unable to load datasets.",
            ),
          );
        }
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
        if (!controller.signal.aborted) {
          setDatasetFilters(response);
        }
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            getErrorMessage(
              cause,
              "Unable to load devices.",
            ),
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setDevicesLoading(false);
        }
      });

    return () => controller.abort();
  }, [input.dataset_id]);

  /* ==========================================================
     Discover Episodes
     ========================================================== */

  useEffect(() => {
    if (!input.dataset_id || !input.device_id) {
      setDeviceObservations([]);
      return;
    }

    const controller = new AbortController();

    setDeviceDataLoading(true);
    setDeviceObservations([]);

    loadAllObservations(
      input.dataset_id,
      input.device_id,
      undefined,
      controller.signal,
    )
      .then((observations) => {
        if (!controller.signal.aborted) {
          setDeviceObservations(observations);
        }
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            getErrorMessage(
              cause,
              "Unable to load episodes.",
            ),
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setDeviceDataLoading(false);
        }
      });

    return () => controller.abort();
  }, [input.dataset_id, input.device_id]);

  /* ==========================================================
     Load Episode Observations
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

    setEpisodeDataLoading(true);
    setEpisodeObservations([]);

    loadAllObservations(
      input.dataset_id,
      input.device_id,
      input.episode_id,
      controller.signal,
    )
      .then((observations) => {
        if (!controller.signal.aborted) {
          setEpisodeObservations(observations);
        }
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            getErrorMessage(
              cause,
              "Unable to load episode observations.",
            ),
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setEpisodeDataLoading(false);
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

  const orderedObservations = useMemo(
    () => sortObservations(episodeObservations),
    [episodeObservations],
  );

  const eligibleOrigins = useMemo(
    () => getEligibleOrigins(episodeObservations),
    [episodeObservations],
  );

  const latestEligibleOrigin =
    eligibleOrigins[eligibleOrigins.length - 1] ?? "";

  const effectiveOrigin =
    forecastMode === "latest"
      ? latestEligibleOrigin
      : input.forecast_origin;

  const originTime = effectiveOrigin
    ? new Date(effectiveOrigin).getTime()
    : NaN;

  const inputWindow = useMemo(
    () =>
      orderedObservations
        .filter(
          (observation) =>
            new Date(
              observation.timestamp,
            ).getTime() <= originTime,
        )
        .slice(-MAX_SEQUENCE_LENGTH),
    [orderedObservations, originTime],
  );

  const latestObserved =
    inputWindow[inputWindow.length - 1] ?? null;

  const activeDatasetMatches =
    input.dataset_id === ACTIVE_MODEL_DATASET_ID;

  const originIsValid =
    eligibleOrigins.includes(effectiveOrigin);

  const loading =
    filtersLoading ||
    devicesLoading ||
    deviceDataLoading ||
    episodeDataLoading;

  const canGenerate =
    !busy &&
    !loading &&
    activeDatasetMatches &&
    Boolean(input.dataset_id) &&
    Boolean(input.device_id) &&
    Boolean(input.episode_id) &&
    originIsValid;

  const targetPreview = useMemo(() => {
    if (!effectiveOrigin) {
      return [];
    }

    return FORECAST_HORIZONS.map((horizon) => ({
      horizon,
      target: addMinutes(
        effectiveOrigin,
        horizon,
      ),
    }));
  }, [effectiveOrigin]);

  const sortedPredictions = useMemo(
    () =>
      result
        ? [...result.predictions].sort(
            (a, b) =>
              a.horizon_minutes -
              b.horizon_minutes,
          )
        : [],
    [result],
  );

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

    setDatasetFilters(null);
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

  function changeMode(mode: ForecastMode) {
    setForecastMode(mode);

    setInput((previous) => ({
      ...previous,
      forecast_origin: "",
    }));

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
     Forecast Generation
     ========================================================== */

  async function generate() {
    if (!canGenerate) return;

    const request: ForecastInput = {
      ...input,
      forecast_origin: effectiveOrigin,
    };

    setBusy(true);
    setError("");
    setNotice("");
    setResult(null);

    try {
      const response = await c3ForecastApi.generate(
        request,
      );

      setResult(response);

      setNotice(
        "Three model-generated forecasts were saved successfully.",
      );

      try {
        const saved = await c3ForecastApi.history(
          request.dataset_id,
          request.device_id,
          request.episode_id,
        );

        setHistory(saved.predictions);
      } catch (historyError) {
        setError(
          `Forecasts were generated and saved, but history could not be loaded: ${getErrorMessage(
            historyError,
            "History retrieval failed.",
          )}`,
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

  /* ==========================================================
     Render
     ========================================================== */

  return (
    <div className="c3-active-forecasting">
      {/* ======================================================
          Page Introduction
      ====================================================== */}

      <section className="c3-af-intro">
        <div>
          <span className="section-overline">
            COMPONENT 03 · RESEARCH FORECASTING
          </span>

          <h2>Future soil-moisture forecasting</h2>

          <p>
            Use activated machine-learning models to
            estimate soil moisture 15, 30, and 60 minutes
            after the selected observation.
          </p>
        </div>

        <span className="c3-af-research-badge">
          SYNTHETIC RESEARCH
        </span>
      </section>

      {/* ======================================================
          Forecast Configuration
      ====================================================== */}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="section-overline">
              STEP 01 · FORECAST CONFIGURATION
            </span>

            <h2>Select the observation source</h2>
          </div>
        </div>

        <p className="c3-af-description">
          Historical sensor observations provide the
          input context. Future values are generated
          by the activated models, not copied from the
          Golden Database.
        </p>

        <div className="c3-af-form">
          <label className="c3-af-field">
            <span>Dataset</span>

            <select
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

          <label className="c3-af-field">
            <span>Device</span>

            <select
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

          <label className="c3-af-field">
            <span>Episode</span>

            <select
              value={input.episode_id}
              disabled={
                busy ||
                !input.device_id ||
                deviceDataLoading
              }
              onChange={(event) =>
                changeEpisode(event.target.value)
              }
            >
              <option value="">
                {deviceDataLoading
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
        </div>

        <div className="c3-af-mode-selector">
          <div>
            <strong>Forecasting mode</strong>

            <p>
              Choose the latest available observation
              or replay a previous historical origin.
            </p>
          </div>

          <div className="c3-af-mode-buttons">
            <button
              type="button"
              className={
                forecastMode === "latest"
                  ? "c3-af-mode-button active"
                  : "c3-af-mode-button"
              }
              onClick={() => changeMode("latest")}
              disabled={busy}
              aria-pressed={forecastMode === "latest"}
            >
              Latest observation
            </button>

            <button
              type="button"
              className={
                forecastMode === "historical"
                  ? "c3-af-mode-button active"
                  : "c3-af-mode-button"
              }
              onClick={() =>
                changeMode("historical")
              }
              disabled={busy}
              aria-pressed={
                forecastMode === "historical"
              }
            >
              Historical replay
            </button>
          </div>
        </div>

        {forecastMode === "historical" && (
          <label className="c3-af-field c3-af-origin-field">
            <span>
              Historical forecast origin · Asia/Colombo
            </span>

            <select
              value={input.forecast_origin}
              disabled={
                busy ||
                !input.episode_id ||
                episodeDataLoading
              }
              onChange={(event) =>
                changeOrigin(event.target.value)
              }
            >
              <option value="">
                Select historical observation
              </option>

              {eligibleOrigins.map((origin) => (
                <option key={origin} value={origin}>
                  {formatTimestamp(origin)}
                </option>
              ))}
            </select>
          </label>
        )}

        {input.episode_id && !episodeDataLoading && (
          <div className="c3-af-source-summary">
            <div>
              <span>Episode observations</span>
              <strong>
                {episodeObservations.length}
              </strong>
            </div>

            <div>
              <span>Eligible forecast origins</span>
              <strong>{eligibleOrigins.length}</strong>
            </div>

            <div>
              <span>Input sequence</span>
              <strong>
                {inputWindow.length} /{" "}
                {MAX_SEQUENCE_LENGTH}
              </strong>
            </div>
          </div>
        )}

        {!activeDatasetMatches &&
          input.dataset_id && (
            <p
              className="c3-af-error"
              role="status"
            >
              The currently activated models belong
              to another dataset. This dataset needs
              compatible model activation before
              forecasts can be generated.
            </p>
          )}

        {input.episode_id &&
          !episodeDataLoading &&
          eligibleOrigins.length === 0 && (
            <p
              className="c3-af-error"
              role="status"
            >
              No eligible forecasting origin was
              found. At least three complete historical
              observations are required.
            </p>
          )}
      </section>

      {/* ======================================================
          Forecast Preview
      ====================================================== */}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="section-overline">
              STEP 02 · FORECAST PREVIEW
            </span>

            <h2>Observation → Future targets</h2>
          </div>
        </div>

        {!effectiveOrigin ? (
          <p className="c3-af-description">
            Select a dataset, device, and episode
            to preview the forecast timestamps.
          </p>
        ) : (
          <>
            <div className="c3-af-origin-summary">
              <div>
                <span>Forecast origin</span>

                <strong>
                  {formatTimestamp(effectiveOrigin)}
                </strong>

                <small>
                  {forecastMode === "latest"
                    ? "Latest eligible observation"
                    : "Selected historical replay origin"}
                </small>
              </div>

              <div>
                <span>Last observed soil moisture</span>

                <strong>
                  {formatValue(
                    latestObserved?.soil_moisture_pct,
                  )}
                </strong>

                <small>
                  Recorded synthetic sensor value
                </small>
              </div>
            </div>

            <div className="c3-af-target-preview">
              {targetPreview.map((target) => (
                <article
                  key={target.horizon}
                  className="c3-af-target-card"
                >
                  <span>
                    +{target.horizon} MINUTES
                  </span>

                  <strong>
                    {formatShortTime(target.target)}
                  </strong>

                  <small>
                    {formatShortDate(target.target)}
                  </small>

                  <em>
                    Awaiting model prediction
                  </em>
                </article>
              ))}
            </div>
          </>
        )}

        <div className="c3-af-actions">
          <button
            type="button"
            onClick={() => void generate()}
            disabled={!canGenerate}
            className="c3-af-generate-button"
          >
            {busy
              ? "Generating forecasts..."
              : "Generate future forecasts"}
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
          Generated Predictions
      ====================================================== */}

      {result && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="section-overline">
                STEP 03 · MODEL-GENERATED RESULTS
              </span>

              <h2>Future soil-moisture predictions</h2>
            </div>

            <span className="c3-af-success-badge">
              SAVED TO DATABASE
            </span>
          </div>

          <p className="c3-af-description">
            These values were generated by the
            activated forecasting models using
            observations available at or before
            the forecast origin.
          </p>

          <div className="c3-af-results">
            {sortedPredictions.map((prediction) => {
              const change =
                latestObserved &&
                Number.isFinite(
                  latestObserved.soil_moisture_pct,
                )
                  ? prediction.predicted_soil_moisture_pct -
                    latestObserved.soil_moisture_pct
                  : null;

              return (
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

                  <div className="c3-af-result-divider" />

                  <span className="c3-af-result-label">
                    Target date & time
                  </span>

                  <strong className="c3-af-result-time">
                    {formatTimestamp(
                      prediction.target_timestamp,
                    )}
                  </strong>

                  {change !== null && (
                    <span className="c3-af-result-change">
                      {change >= 0 ? "+" : ""}
                      {change.toFixed(2)} percentage
                      points from last observation
                    </span>
                  )}
                </article>
              );
            })}
          </div>

          <ForecastChart
            observations={episodeObservations}
            origin={result.forecast_origin}
            predictions={sortedPredictions}
          />

          <p className="c3-af-description">
            Forecast origin:{" "}
            <strong>
              {formatTimestamp(result.forecast_origin)}
            </strong>
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
              PERSISTED MODEL OUTPUTS
            </span>

            <h2>Saved forecast history</h2>
          </div>
        </div>

        {history.length === 0 ? (
          <p className="c3-af-description">
            No saved forecasts loaded for this
            dataset, device, and episode.
          </p>
        ) : (
          <div className="c3-af-history">
            <table>
              <thead>
                <tr>
                  <th>Forecast origin</th>
                  <th>Future target</th>
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
                      +{prediction.horizon_minutes} min
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
          Research Boundaries
      ====================================================== */}

      <section className="panel c3-af-limitation">
        <strong>Research interpretation</strong>

        <p>
          This workspace performs historical replay
          using synthetic research observations.
          Forecast timestamps may be later than the
          final observation, but they are not live
          calendar-time predictions. The outputs
          estimate soil moisture only—not landslide
          probability, disaster risk, or operational
          warning status.
        </p>
      </section>
    </div>
  );
}