/** @format */

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  c3ExplorerApi,
  type C3GoldenObservation,
  type C3ObservationFiltersResponse,
  type C3ObservationQuery,
  type C3ObservationSortBy,
} from "../api/c3Api";

import "../styles/c3GoldenDatabaseExplorer.css";

/* ============================================================
   Constants
   ============================================================ */

const PAGE_SIZES = [10, 25, 50, 100];

const INITIAL_QUERY: C3ObservationQuery = {
  sort_by: "timestamp",
  sort_order: "desc",
  limit: 25,
  offset: 0,
};

const SENSOR_FIELDS: {
  key: keyof C3GoldenObservation;
  label: string;
  unit: string;
}[] = [
  {
    key: "soil_moisture_pct",
    label: "Soil Moisture",
    unit: "%",
  },
  {
    key: "rainfall_proxy_counts",
    label: "Rainfall Proxy",
    unit: "counts",
  },
  {
    key: "tilt_deg",
    label: "Tilt",
    unit: "°",
  },
  {
    key: "vibration_g",
    label: "Vibration",
    unit: "g",
  },
  {
    key: "fsr_adc",
    label: "FSR",
    unit: "ADC",
  },
  {
    key: "air_temperature_c",
    label: "Air Temperature",
    unit: "°C",
  },
  {
    key: "humidity_pct",
    label: "Humidity",
    unit: "%",
  },
];

/* ============================================================
   Helpers
   ============================================================ */

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Unable to retrieve Golden observations.";
}

function formatTimestamp(value: string): string {
  const date = new Date(value);

  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function formatNumber(value: number, digits = 3): string {
  return value.toLocaleString(undefined, {
    maximumFractionDigits: digits,
  });
}

function toIsoTimestamp(value: string): string | undefined {
  if (!value) return undefined;

  const date = new Date(value);

  return Number.isNaN(date.getTime()) ? undefined : date.toISOString();
}

/* ============================================================
   Component
   ============================================================ */

export function C3GoldenDatabaseExplorer() {
  const [query, setQuery] = useState<C3ObservationQuery>(INITIAL_QUERY);

  const [searchInput, setSearchInput] = useState("");

  const [fromInput, setFromInput] = useState("");

  const [toInput, setToInput] = useState("");

  const [filters, setFilters] = useState<C3ObservationFiltersResponse | null>(
    null,
  );

  const [observations, setObservations] = useState<C3GoldenObservation[]>([]);

  const [total, setTotal] = useState(0);

  const [loading, setLoading] = useState(true);

  const [filtersLoading, setFiltersLoading] = useState(true);

  const [error, setError] = useState("");

  const [selectedObservation, setSelectedObservation] =
    useState<C3GoldenObservation | null>(null);

  const [refreshVersion, setRefreshVersion] = useState(0);

  /* ==========================================================
     Load Filter Options
     ========================================================== */

  useEffect(() => {
    const controller = new AbortController();

    setFiltersLoading(true);

    c3ExplorerApi
      .filters(query.dataset_id, controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;

        setFilters(response);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;

        setError(getErrorMessage(cause));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setFiltersLoading(false);
        }
      });

    return () => controller.abort();
  }, [query.dataset_id, refreshVersion]);

  /* ==========================================================
     Load Observations
     ========================================================== */

  useEffect(() => {
    const controller = new AbortController();

    setLoading(true);
    setError("");

    c3ExplorerApi
      .list(query, controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;

        setObservations(response.observations);
        setTotal(response.total);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;

        setError(getErrorMessage(cause));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [query, refreshVersion]);

  /* ==========================================================
     Query Updates
     ========================================================== */

  const updateQuery = useCallback((updates: Partial<C3ObservationQuery>) => {
    setQuery((current) => ({
      ...current,
      ...updates,
      offset: 0,
    }));

    setSelectedObservation(null);
  }, []);

  function applySearch() {
    updateQuery({
      search: searchInput.trim() || undefined,
      timestamp_from: toIsoTimestamp(fromInput),
      timestamp_to: toIsoTimestamp(toInput),
    });
  }

  function clearFilters() {
    setSearchInput("");
    setFromInput("");
    setToInput("");

    setQuery(INITIAL_QUERY);
    setSelectedObservation(null);
  }

  function changePage(offset: number) {
    setQuery((current) => ({
      ...current,
      offset,
    }));

    setSelectedObservation(null);
  }

  function refresh() {
    setRefreshVersion((current) => current + 1);
  }

  /* ==========================================================
     Sorting
     ========================================================== */

  function changeSort(sortBy: C3ObservationSortBy) {
    setQuery((current) => ({
      ...current,
      sort_by: sortBy,
      sort_order:
        current.sort_by === sortBy && current.sort_order === "asc"
          ? "desc"
          : "asc",
      offset: 0,
    }));

    setSelectedObservation(null);
  }

  /* ==========================================================
     Export
     ========================================================== */

  function exportCSV() {
    const exportQuery: C3ObservationQuery = {
      dataset_id: query.dataset_id,
      device_id: query.device_id,
      episode_id: query.episode_id,
      operating_mode: query.operating_mode,
      timestamp_from: query.timestamp_from,
      timestamp_to: query.timestamp_to,
      search: query.search,
    };

    window.location.assign(c3ExplorerApi.exportUrl(exportQuery));
  }

  /* ==========================================================
     Derived Values
     ========================================================== */

  const limit = query.limit ?? 25;
  const offset = query.offset ?? 0;

  const page = Math.floor(offset / limit) + 1;

  const totalPages = Math.max(1, Math.ceil(total / limit));

  const showingFrom = total === 0 ? 0 : offset + 1;

  const showingTo = Math.min(offset + observations.length, total);

  const hasNextPage = offset + observations.length < total;

  const activeFilterCount = useMemo(
    () =>
      [
        query.dataset_id,
        query.device_id,
        query.episode_id,
        query.operating_mode,
        query.timestamp_from,
        query.timestamp_to,
        query.search,
      ].filter(Boolean).length,
    [query],
  );

  /* ==========================================================
     Render
     ========================================================== */

  return (
    <div className="c3-explorer">
      {/* ======================================================
          Header
          ====================================================== */}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="section-overline">
              GEONEX C3 · GOLDEN DATA EXPLORER
            </span>

            <h2>Sensor Observation Explorer</h2>
          </div>

          <span className="live-chip">Read-only SQLite</span>
        </div>

        <p className="panel-subtitle">
          Explore persistent Golden Database sensor observations using
          server-side filtering, sorting, and pagination. All measurements shown
          are retrieved from SQLite rather than generated by the frontend.
        </p>

        <div className="c3-explorer-overview">
          <div>
            <span>MATCHING OBSERVATIONS</span>
            <strong>{loading ? "…" : total.toLocaleString()}</strong>
          </div>

          <div>
            <span>VISIBLE RECORDS</span>
            <strong>{loading ? "…" : observations.length}</strong>
          </div>

          <div>
            <span>ACTIVE FILTERS</span>
            <strong>{activeFilterCount}</strong>
          </div>

          <div>
            <span>PAGE</span>
            <strong>
              {page} / {totalPages}
            </strong>
          </div>
        </div>
      </section>

      {/* ======================================================
          Filters
          ====================================================== */}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="section-overline">OBSERVATION QUERY</span>

            <h2>Search & Filter</h2>
          </div>

          <span className="c3-explorer-filter-chip">
            {activeFilterCount} active
          </span>
        </div>

        <div className="c3-explorer-filter-grid">
          <label>
            <span>Dataset</span>

            <select
              value={query.dataset_id ?? ""}
              disabled={filtersLoading}
              onChange={(event) =>
                updateQuery({
                  dataset_id: event.target.value || undefined,
                  device_id: undefined,
                  episode_id: undefined,
                  operating_mode: undefined,
                })
              }>
              <option value="">All datasets</option>

              {filters?.datasets.map((dataset) => (
                <option key={dataset.dataset_id} value={dataset.dataset_id}>
                  {dataset.filename}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Device</span>

            <select
              value={query.device_id ?? ""}
              disabled={filtersLoading}
              onChange={(event) =>
                updateQuery({
                  device_id: event.target.value || undefined,
                  episode_id: undefined,
                })
              }>
              <option value="">All devices</option>

              {filters?.devices.map((device) => (
                <option key={device} value={device}>
                  {device}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Episode</span>

            <select
              value={query.episode_id ?? ""}
              disabled={filtersLoading}
              onChange={(event) =>
                updateQuery({
                  episode_id: event.target.value || undefined,
                })
              }>
              <option value="">All episodes</option>

              {filters?.episodes.map((episode) => (
                <option key={episode} value={episode}>
                  {episode}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Operating Mode</span>

            <select
              value={query.operating_mode ?? ""}
              disabled={filtersLoading}
              onChange={(event) =>
                updateQuery({
                  operating_mode: event.target.value || undefined,
                })
              }>
              <option value="">All modes</option>

              {filters?.operating_modes.map((mode) => (
                <option key={mode} value={mode}>
                  {mode}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Search Device / Episode</span>

            <input
              type="search"
              value={searchInput}
              placeholder="Search identifiers…"
              onChange={(event) => setSearchInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  applySearch();
                }
              }}
            />
          </label>

          <label>
            <span>Timestamp From</span>

            <input
              type="datetime-local"
              value={fromInput}
              onChange={(event) => setFromInput(event.target.value)}
            />
          </label>

          <label>
            <span>Timestamp To</span>

            <input
              type="datetime-local"
              value={toInput}
              onChange={(event) => setToInput(event.target.value)}
            />
          </label>
        </div>

        <div className="c3-explorer-actions">
          <button
            type="button"
            className="c3-explorer-button primary"
            onClick={applySearch}>
            Apply Filters
          </button>

          <button
            type="button"
            className="c3-explorer-button secondary"
            onClick={clearFilters}>
            Clear Filters
          </button>

          <button
            type="button"
            className="c3-explorer-button secondary"
            onClick={refresh}>
            Refresh
          </button>

          <button
            type="button"
            className="c3-explorer-button export"
            onClick={exportCSV}
            disabled={loading || total === 0}>
            Export CSV
          </button>
        </div>
      </section>

      {/* ======================================================
          Observation Table
          ====================================================== */}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="section-overline">
              GOLDEN DATABASE · SENSOR READINGS
            </span>

            <h2>Stored Observations</h2>
          </div>

          <span className="live-chip">
            {showingFrom.toLocaleString()}–{showingTo.toLocaleString()} of{" "}
            {total.toLocaleString()}
          </span>
        </div>

        <div className="c3-explorer-table-toolbar">
          <span>Select a row to inspect all seven sensors.</span>

          <label>
            Rows per page
            <select
              value={limit}
              onChange={(event) =>
                updateQuery({
                  limit: Number(event.target.value),
                })
              }>
              {PAGE_SIZES.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
        </div>

        {loading ? (
          <div className="c3-explorer-state">Loading observations…</div>
        ) : observations.length === 0 ? (
          <div className="c3-explorer-state">
            No observations match the selected filters.
          </div>
        ) : (
          <div className="c3-explorer-table-scroll">
            <table className="c3-explorer-table">
              <thead>
                <tr>
                  <th>
                    <button
                      type="button"
                      onClick={() => changeSort("timestamp")}>
                      Timestamp ↕
                    </button>
                  </th>

                  <th>
                    <button
                      type="button"
                      onClick={() => changeSort("device_id")}>
                      Device ↕
                    </button>
                  </th>

                  <th>
                    <button
                      type="button"
                      onClick={() => changeSort("episode_id")}>
                      Episode ↕
                    </button>
                  </th>

                  <th>
                    <button
                      type="button"
                      onClick={() => changeSort("operating_mode")}>
                      Mode ↕
                    </button>
                  </th>

                  <th>
                    <button
                      type="button"
                      onClick={() => changeSort("soil_moisture_pct")}>
                      Moisture ↕
                    </button>
                  </th>

                  <th>
                    <button
                      type="button"
                      onClick={() => changeSort("rainfall_proxy_counts")}>
                      Rainfall ↕
                    </button>
                  </th>

                  <th>
                    <button
                      type="button"
                      onClick={() => changeSort("tilt_deg")}>
                      Tilt ↕
                    </button>
                  </th>

                  <th>Inspect</th>
                </tr>
              </thead>

              <tbody>
                {observations.map((observation) => (
                  <tr
                    key={observation.observation_id}
                    className={
                      selectedObservation?.observation_id ===
                      observation.observation_id
                        ? "selected"
                        : ""
                    }>
                    <td>{formatTimestamp(observation.timestamp)}</td>

                    <td>{observation.device_id}</td>

                    <td>{observation.episode_id}</td>

                    <td>
                      <span
                        className={`c3-explorer-mode mode-${observation.operating_mode.toLowerCase()}`}>
                        {observation.operating_mode}
                      </span>
                    </td>

                    <td>{formatNumber(observation.soil_moisture_pct)}%</td>

                    <td>{formatNumber(observation.rainfall_proxy_counts)}</td>

                    <td>{formatNumber(observation.tilt_deg)}°</td>

                    <td>
                      <button
                        type="button"
                        className="c3-explorer-inspect"
                        onClick={() => setSelectedObservation(observation)}>
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="c3-explorer-pagination">
          <span>
            Page {page} of {totalPages}
          </span>

          <div>
            <button
              type="button"
              disabled={loading || offset === 0}
              onClick={() => changePage(Math.max(0, offset - limit))}>
              Previous
            </button>

            <button
              type="button"
              disabled={loading || !hasNextPage}
              onClick={() => changePage(offset + limit)}>
              Next
            </button>
          </div>
        </div>
      </section>

      {/* ======================================================
          Selected Observation
          ====================================================== */}

      {selectedObservation && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="section-overline">OBSERVATION INSPECTION</span>

              <h2>Reading #{selectedObservation.observation_id}</h2>
            </div>

            <button
              type="button"
              className="c3-explorer-button secondary"
              onClick={() => setSelectedObservation(null)}>
              Close
            </button>
          </div>

          <div className="c3-explorer-detail-grid">
            <div>
              <span>Dataset</span>
              <strong>{selectedObservation.dataset_id}</strong>
            </div>

            <div>
              <span>Device</span>
              <strong>{selectedObservation.device_id}</strong>
            </div>

            <div>
              <span>Episode</span>
              <strong>{selectedObservation.episode_id}</strong>
            </div>

            <div>
              <span>Operating Mode</span>
              <strong>{selectedObservation.operating_mode}</strong>
            </div>

            <div>
              <span>Observation Timestamp</span>
              <strong>{formatTimestamp(selectedObservation.timestamp)}</strong>
            </div>

            <div>
              <span>Database Ingestion Time</span>
              <strong>{formatTimestamp(selectedObservation.created_at)}</strong>
            </div>
          </div>

          <h3 className="c3-explorer-subheading">Sensor Measurements</h3>

          <div className="c3-explorer-sensor-grid">
            {SENSOR_FIELDS.map((sensor) => {
              const value = selectedObservation[sensor.key];

              return (
                <div key={sensor.key} className="c3-explorer-sensor-card">
                  <span>{sensor.label}</span>

                  <strong>
                    {typeof value === "number" ? formatNumber(value, 5) : "—"}

                    <small>{sensor.unit}</small>
                  </strong>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* ======================================================
          Error Feedback
          ====================================================== */}

      {error && (
        <div className="c3-explorer-error" role="alert">
          {error}
        </div>
      )}

      <p className="c3-research-warning">
        Observations displayed here are stored research records. Their presence
        in the Golden Database does not establish calibration accuracy,
        forecasting readiness, or real-world landslide-warning reliability.
      </p>
    </div>
  );
}
