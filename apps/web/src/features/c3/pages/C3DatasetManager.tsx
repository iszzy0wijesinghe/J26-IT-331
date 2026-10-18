/** @format */

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  c3DatasetApi,
  c3GoldenApi,
  type C3RegisteredDataset,
  type C3DatasetValidation,
  type C3GoldenDataset,
  type C3GoldenDatasetDetails,
} from "../api/c3Api";

import { C3CSVValidationWorkspace } from "./C3CSVValidationWorkspace";

import "../styles/c3DatasetManager.css";

/* ============================================================
   Types
   ============================================================ */

type DatasetTab = "csv" | "registered" | "zip";

type DatasetDetails = C3RegisteredDataset & {
  validation?: C3DatasetValidation;
};

/* ============================================================
   Helpers
   ============================================================ */

function getValidation(
  dataset: DatasetDetails | null,
): C3DatasetValidation | null {
  if (!dataset) return null;

  const candidate =
    dataset.validation ??
    (dataset[
      "validation_result"
    ] as C3DatasetValidation | undefined);

  return candidate ?? null;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "An unexpected dataset operation error occurred.";
}

function formatDate(value: string): string {
  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString();
}

/* ============================================================
   Component
   ============================================================ */

export function C3DatasetManager() {
  /* ----------------------------------------------------------
     Navigation
     ---------------------------------------------------------- */

  const [activeTab, setActiveTab] =
    useState<DatasetTab>("csv");

  /* ----------------------------------------------------------
     Prepared ZIP Dataset Registry
     ---------------------------------------------------------- */

  const [datasets, setDatasets] =
    useState<C3RegisteredDataset[]>([]);

  const [selectedId, setSelectedId] =
    useState("");

  const [details, setDetails] =
    useState<DatasetDetails | null>(null);

  /* ----------------------------------------------------------
     Golden CSV Dataset Registry
     ---------------------------------------------------------- */

  const [goldenDatasets, setGoldenDatasets] =
    useState<C3GoldenDataset[]>([]);

  const [selectedGoldenId, setSelectedGoldenId] =
    useState("");

  const [goldenDetails, setGoldenDetails] =
    useState<C3GoldenDatasetDetails | null>(null);

  /* ----------------------------------------------------------
     Loading States
     ---------------------------------------------------------- */

  const [loading, setLoading] =
    useState(true);

  const [loadingDetails, setLoadingDetails] =
    useState(false);

  const [loadingGoldenDetails, setLoadingGoldenDetails] =
    useState(false);

  const [uploading, setUploading] =
    useState(false);

  /* ----------------------------------------------------------
     ZIP Upload
     ---------------------------------------------------------- */

  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  /* ----------------------------------------------------------
     Feedback
     ---------------------------------------------------------- */

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState("");

  /* ============================================================
     Load Both Dataset Registries
     ============================================================ */

  const loadDatasets = useCallback(
    async (signal?: AbortSignal) => {
      const [
        preparedResponse,
        goldenResponse,
      ] = await Promise.all([
        c3DatasetApi.list(signal),
        c3GoldenApi.list(signal),
      ]);

      if (signal?.aborted) return;

      /* ------------------------------------------------------
         Prepared ZIP datasets
         ------------------------------------------------------ */

      setDatasets(preparedResponse.datasets);

      setSelectedId((current) => {
        const exists =
          preparedResponse.datasets.some(
            (dataset) =>
              dataset.dataset_id === current,
          );

        return exists
          ? current
          : preparedResponse.datasets[0]
              ?.dataset_id ?? "";
      });

      /* ------------------------------------------------------
         Golden CSV datasets
         ------------------------------------------------------ */

      setGoldenDatasets(goldenResponse.datasets);

      setSelectedGoldenId((current) => {
        const exists =
          goldenResponse.datasets.some(
            (dataset) =>
              dataset.dataset_id === current,
          );

        return exists
          ? current
          : goldenResponse.datasets[0]
              ?.dataset_id ?? "";
      });
    },
    [],
  );

  /* ============================================================
     Initial Dataset Loading
     ============================================================ */

  useEffect(() => {
    const controller =
      new AbortController();

    setLoading(true);

    loadDatasets(controller.signal)
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
  }, [loadDatasets]);

  /* ============================================================
     Load Selected Prepared Dataset
     ============================================================ */

  useEffect(() => {
    if (!selectedId) {
      setDetails(null);
      setLoadingDetails(false);
      return;
    }

    const controller =
      new AbortController();

    setLoadingDetails(true);
    setDetails(null);

    c3DatasetApi
      .get(selectedId, controller.signal)
      .then((dataset) => {
        if (controller.signal.aborted) return;

        setDetails(dataset);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;

        setError(getErrorMessage(cause));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadingDetails(false);
        }
      });

    return () => controller.abort();
  }, [selectedId]);

  /* ============================================================
     Load Selected Golden Dataset
     ============================================================ */

  useEffect(() => {
    if (!selectedGoldenId) {
      setGoldenDetails(null);
      setLoadingGoldenDetails(false);
      return;
    }

    const controller =
      new AbortController();

    setLoadingGoldenDetails(true);
    setGoldenDetails(null);

    c3GoldenApi
      .get(selectedGoldenId, controller.signal)
      .then((dataset) => {
        if (controller.signal.aborted) return;

        setGoldenDetails(dataset);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;

        setError(getErrorMessage(cause));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadingGoldenDetails(false);
        }
      });

    return () => controller.abort();
  }, [selectedGoldenId]);

  /* ============================================================
     CSV Registration Callback
     ============================================================ */

  function handleGoldenDatasetRegistered(
    datasetId: string,
  ) {
    setSelectedGoldenId(datasetId);

    void loadDatasets().catch(
      (cause: unknown) => {
        setError(
          `Unable to refresh dataset history: ${getErrorMessage(
            cause,
          )}`,
        );
      },
    );
  }

  /* ============================================================
     ZIP Dataset Upload
     ============================================================ */

  async function handleUpload() {
    if (!selectedFile || uploading) return;

    setUploading(true);

    setError("");
    setSuccess("");

    try {
      const response =
        await c3DatasetApi.upload(selectedFile);

      setSuccess(response.message);

      await loadDatasets();

      setSelectedId(
        response.dataset.dataset_id,
      );

      setSelectedFile(null);

      setActiveTab("registered");
    } catch (cause) {
      setError(getErrorMessage(cause));
    } finally {
      setUploading(false);
    }
  }

  /* ============================================================
     Navigation
     ============================================================ */

  function changeTab(tab: DatasetTab) {
    setActiveTab(tab);
    setError("");
  }

  /* ============================================================
     Derived State
     ============================================================ */

  const validation =
    getValidation(details);

  const totalDatasets =
    datasets.length +
    goldenDatasets.length;

  const selectedDatasetLabel =
    activeTab === "registered" &&
    selectedGoldenId
      ? selectedGoldenId
      : selectedId || "None";

  const selectedDatasetStatus =
    activeTab === "registered" &&
    selectedGoldenId
      ? loadingGoldenDetails
        ? "Loading…"
        : goldenDetails?.pipeline_status ?? "—"
      : loadingDetails
        ? "Loading…"
        : details?.status ?? "—";

  /* ============================================================
     Render
     ============================================================ */

  return (
    <div className="c3-dataset-manager">
      {/* ======================================================
          Header
          ====================================================== */}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="section-overline">
              GEONEX C3 · DATA MANAGEMENT
            </span>

            <h2>Dataset Manager</h2>
          </div>

          <span className="live-chip">
            Synthetic forecasting research
          </span>
        </div>

        <p className="panel-subtitle">
          Validate and register raw sensor observations,
          inspect Golden Database history, and import
          prepared forecasting datasets. Held-out test
          records remain excluded from the dataset workflow.
        </p>

        <div className="c3-dataset-summary">
          <div>
            <span>REGISTERED DATASETS</span>

            <strong>
              {loading
                ? "…"
                : totalDatasets}
            </strong>
          </div>

          <div>
            <span>SELECTED DATASET</span>

            <strong>
              {selectedDatasetLabel}
            </strong>
          </div>

          <div>
            <span>DATASET STATUS</span>

            <strong>
              {selectedDatasetStatus}
            </strong>
          </div>
        </div>
      </section>

      {/* ======================================================
          Navigation Tabs
          ====================================================== */}

      <nav
        className="c3-dataset-navigation"
        aria-label="Dataset management sections"
      >
        <button
          type="button"
          className={`c3-dataset-navigation-button ${
            activeTab === "csv"
              ? "active"
              : ""
          }`}
          aria-current={
            activeTab === "csv"
              ? "page"
              : undefined
          }
          onClick={() =>
            changeTab("csv")
          }
        >
          <span
            className="c3-dataset-navigation-icon"
            aria-hidden="true"
          >
            ◈
          </span>

          <span className="c3-dataset-navigation-label">
            CSV Ingestion
          </span>
        </button>

        <button
          type="button"
          className={`c3-dataset-navigation-button ${
            activeTab === "registered"
              ? "active"
              : ""
          }`}
          aria-current={
            activeTab === "registered"
              ? "page"
              : undefined
          }
          onClick={() =>
            changeTab("registered")
          }
        >
          <span
            className="c3-dataset-navigation-icon"
            aria-hidden="true"
          >
            ▤
          </span>

          <span className="c3-dataset-navigation-label">
            Registered Datasets
          </span>
        </button>

        <button
          type="button"
          className={`c3-dataset-navigation-button ${
            activeTab === "zip"
              ? "active"
              : ""
          }`}
          aria-current={
            activeTab === "zip"
              ? "page"
              : undefined
          }
          onClick={() =>
            changeTab("zip")
          }
        >
          <span
            className="c3-dataset-navigation-icon"
            aria-hidden="true"
          >
            ⇧
          </span>

          <span className="c3-dataset-navigation-label">
            ZIP Import
          </span>
        </button>
      </nav>

      {/* ======================================================
          CSV Ingestion Workspace
          ====================================================== */}

      {activeTab === "csv" && (
        <div className="c3-dataset-workspace">
          <C3CSVValidationWorkspace
            onDatasetRegistered={
              handleGoldenDatasetRegistered
            }
          />
        </div>
      )}

      {/* ======================================================
          Registered Datasets
          ====================================================== */}

      {activeTab === "registered" && (
        <div className="c3-dataset-workspace">
          {/* ==================================================
              Golden CSV Dataset History
              ================================================== */}

          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="section-overline">
                  GOLDEN DATABASE · CSV HISTORY
                </span>

                <h2>
                  Golden Sensor Datasets
                </h2>
              </div>

              <span className="live-chip">
                {goldenDatasets.length} stored
              </span>
            </div>

            <p className="panel-subtitle">
              Persistent raw sensor observations
              registered through the Golden Data
              ingestion pipeline. These datasets
              are not automatically prepared
              training and validation splits.
            </p>

            {loading ? (
              <div className="c3-dataset-loading">
                <span className="c3-dataset-loading-spinner" />

                <p className="c3-inline-note">
                  Loading Golden datasets…
                </p>
              </div>
            ) : goldenDatasets.length === 0 ? (
              <p className="c3-inline-note">
                No Golden CSV datasets have
                been registered yet.
              </p>
            ) : (
              <div className="c3-dataset-list">
                {goldenDatasets.map(
                  (dataset) => (
                    <button
                      key={
                        dataset.dataset_id
                      }
                      type="button"
                      className={`c3-dataset-item ${
                        selectedGoldenId ===
                        dataset.dataset_id
                          ? "selected"
                          : ""
                      }`}
                      onClick={() => {
                        setSelectedGoldenId(
                          dataset.dataset_id,
                        );

                        setError("");
                      }}
                    >
                      <div>
                        <strong>
                          {dataset.filename}
                        </strong>

                        <span>
                          {dataset.dataset_id}
                          {" · "}
                          {dataset.total_rows.toLocaleString()}
                          {" observations · "}
                          {dataset.episode_count}
                          {" episodes"}
                        </span>
                      </div>

                      <span className="c3-dataset-status">
                        {dataset.pipeline_status}
                      </span>
                    </button>
                  ),
                )}
              </div>
            )}

            {/* ------------------------------------------------
                Golden Dataset Details
                ------------------------------------------------ */}

            {loadingGoldenDetails ? (
              <div className="c3-dataset-loading">
                <span className="c3-dataset-loading-spinner" />

                <p className="c3-inline-note">
                  Loading Golden dataset details…
                </p>
              </div>
            ) : goldenDetails ? (
              <>
                <h3 className="c3-dataset-section-title">
                  Golden Dataset Inspection
                </h3>

                <div className="c3-dataset-detail-grid">
                  <div>
                    <span>Dataset ID</span>

                    <strong>
                      {goldenDetails.dataset_id}
                    </strong>
                  </div>

                  <div>
                    <span>Stored Observations</span>

                    <strong>
                      {goldenDetails.stored_observations.toLocaleString()}
                    </strong>
                  </div>

                  <div>
                    <span>Devices</span>

                    <strong>
                      {goldenDetails.device_count}
                    </strong>
                  </div>

                  <div>
                    <span>Episodes</span>

                    <strong>
                      {goldenDetails.episode_count}
                    </strong>
                  </div>

                  <div>
                    <span>Quality Status</span>

                    <strong>
                      {goldenDetails.quality_status}
                    </strong>
                  </div>

                  <div>
                    <span>Pipeline Status</span>

                    <strong>
                      {goldenDetails.pipeline_status}
                    </strong>
                  </div>

                  <div>
                    <span>Uploaded At</span>

                    <strong>
                      {formatDate(
                        goldenDetails.uploaded_at,
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>Validation</span>

                    <strong>
                      {goldenDetails.validation.status}
                    </strong>
                  </div>
                </div>

                <h3 className="c3-dataset-section-title">
                  Sensor Quality Report
                </h3>

                <div className="c3-dataset-detail-grid">
                  <div>
                    <span>Valid Rows</span>

                    <strong>
                      {goldenDetails.validation.valid_rows.toLocaleString()}
                    </strong>
                  </div>

                  <div>
                    <span>Invalid Rows</span>

                    <strong>
                      {goldenDetails.validation.invalid_rows.toLocaleString()}
                    </strong>
                  </div>

                  <div>
                    <span>Validation Errors</span>

                    <strong>
                      {goldenDetails.validation.error_count}
                    </strong>
                  </div>

                  <div>
                    <span>Validation Warnings</span>

                    <strong>
                      {goldenDetails.validation.warning_count}
                    </strong>
                  </div>
                </div>

                <h3 className="c3-dataset-section-title">
                  Operating Modes
                </h3>

                <div className="c3-dataset-detail-grid">
                  {Object.entries(
                    goldenDetails.validation.operating_modes,
                  ).map(([mode, count]) => (
                    <div key={mode}>
                      <span>{mode}</span>

                      <strong>
                        {count.toLocaleString()}
                      </strong>
                    </div>
                  ))}
                </div>

                <p className="c3-research-warning">
                  This dataset passed the
                  currently implemented CSV
                  validation checks. Temporal
                  readiness, calibrated anomaly
                  assessment, and forecasting
                  suitability have not yet
                  been established.
                </p>
              </>
            ) : null}
          </section>

          {/* ==================================================
              Prepared ZIP Dataset Library
              ================================================== */}

          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="section-overline">
                  PREPARED DATASET LIBRARY
                </span>

                <h2>
                  Prepared Forecasting Datasets
                </h2>
              </div>

              <span className="live-chip">
                {datasets.length} registered
              </span>
            </div>

            <p className="panel-subtitle">
              Prepared datasets containing
              training and validation splits.
              These datasets are registered
              separately from raw Golden
              sensor observations.
            </p>

            {loading ? (
              <div className="c3-dataset-loading">
                <span className="c3-dataset-loading-spinner" />

                <p className="c3-inline-note">
                  Loading prepared datasets…
                </p>
              </div>
            ) : datasets.length === 0 ? (
              <p className="c3-inline-note">
                No prepared datasets have
                been registered yet.
              </p>
            ) : (
              <div className="c3-dataset-list">
                {datasets.map((dataset) => (
                  <button
                    key={dataset.dataset_id}
                    type="button"
                    className={`c3-dataset-item ${
                      selectedId === dataset.dataset_id
                        ? "selected"
                        : ""
                    }`}
                    onClick={() => {
                      setSelectedId(
                        dataset.dataset_id,
                      );

                      setError("");
                    }}
                  >
                    <div>
                      <strong>
                        {dataset.dataset_id}
                      </strong>

                      <span>
                        Synthetic C3 forecasting
                        dataset
                      </span>
                    </div>

                    <span className="c3-dataset-status">
                      {dataset.status}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </section>

          {/* ==================================================
              Prepared Dataset Inspection
              ================================================== */}

          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="section-overline">
                  PREPARED DATASET INSPECTION
                </span>

                <h2>
                  Prepared Dataset Details
                </h2>
              </div>
            </div>

            {loadingDetails ? (
              <div className="c3-dataset-loading">
                <span className="c3-dataset-loading-spinner" />

                <p className="c3-inline-note">
                  Loading dataset details…
                </p>
              </div>
            ) : !details ? (
              <p className="c3-inline-note">
                Select a prepared dataset to
                inspect its validation results.
              </p>
            ) : (
              <>
                <div className="c3-dataset-detail-grid">
                  <div>
                    <span>Dataset ID</span>

                    <strong>
                      {details.dataset_id}
                    </strong>
                  </div>

                  <div>
                    <span>Validation Status</span>

                    <strong>
                      {details.status}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Held-out Test Included
                    </span>

                    <strong>
                      {details.held_out_test_included
                        ? "YES"
                        : "NO"}
                    </strong>
                  </div>

                  <div>
                    <span>Source</span>

                    <strong>
                      {validation?.source_origin ??
                        "Synthetic"}
                    </strong>
                  </div>
                </div>

                {validation && (
                  <>
                    <h3 className="c3-dataset-section-title">
                      Training and Validation Statistics
                    </h3>

                    <div className="c3-dataset-splits">
                      {(
                        [
                          "train",
                          "validation",
                        ] as const
                      ).map((split) => {
                        const statistics =
                          validation.splits[split];

                        return (
                          <div
                            key={split}
                            className="c3-dataset-split-card"
                          >
                            <h4>
                              {split === "train"
                                ? "Training Split"
                                : "Validation Split"}
                            </h4>

                            <div>
                              <span>Examples</span>

                              <strong>
                                {statistics.examples.toLocaleString()}
                              </strong>
                            </div>

                            <div>
                              <span>Episodes</span>

                              <strong>
                                {statistics.episodes}
                              </strong>
                            </div>

                            <div>
                              <span>Devices</span>

                              <strong>
                                {statistics.devices}
                              </strong>
                            </div>

                            <div>
                              <span>
                                Missing readings
                              </span>

                              <strong>
                                {statistics.missing_readings.toLocaleString()}
                              </strong>
                            </div>

                            <h5>
                              Forecast horizons
                            </h5>

                            {[15, 30, 60].map(
                              (horizon) => (
                                <div key={horizon}>
                                  <span>
                                    {horizon} minutes
                                  </span>

                                  <strong>
                                    {(
                                      statistics.horizon_counts[
                                        String(horizon)
                                      ] ?? 0
                                    ).toLocaleString()}
                                  </strong>
                                </div>
                              ),
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}
              </>
            )}

            <p className="c3-research-warning">
              Prepared datasets are used
              for synthetic forecasting
              research. Dataset validation
              does not establish
              landslide-warning reliability.
            </p>
          </section>
        </div>
      )}

      {/* ======================================================
          ZIP Dataset Import
          ====================================================== */}

      {activeTab === "zip" && (
        <div className="c3-dataset-workspace">
          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="section-overline">
                  DATASET IMPORT
                </span>

                <h2>
                  Import Prepared Dataset
                </h2>
              </div>

              <span className="live-chip">
                ZIP dataset registration
              </span>
            </div>

            <p className="panel-subtitle">
              Upload a prepared dataset ZIP
              containing exactly the required
              training and validation files.
              The backend verifies dataset
              integrity, compatibility,
              and episode-disjoint splitting
              before registration.
            </p>

            <div className="c3-dataset-upload">
              <label htmlFor="c3-dataset-file">
                Dataset ZIP archive
              </label>

              <input
                id="c3-dataset-file"
                type="file"
                accept=".zip,application/zip"
                disabled={uploading}
                onChange={(event) => {
                  setSelectedFile(
                    event.target.files?.[0] ?? null,
                  );

                  setError("");
                  setSuccess("");
                }}
              />

              <button
                type="button"
                className="c3-primary-button"
                disabled={
                  !selectedFile || uploading
                }
                onClick={() =>
                  void handleUpload()
                }
              >
                {uploading
                  ? "Validating and registering…"
                  : "Upload and Register Dataset"}
              </button>
            </div>

            {error && (
              <div
                className="c3-dataset-error"
                role="alert"
              >
                {error}
              </div>
            )}

            {success && (
              <p
                className="c3-dataset-success"
                role="status"
              >
                {success}
              </p>
            )}

            <p className="c3-research-warning">
              Only manifest.json,
              train.jsonl.gz, and
              validation.jsonl.gz are
              permitted in the ZIP.
              Held-out test records must
              not be uploaded.
              Dataset registration does
              not automatically start
              model training.
            </p>
          </section>
        </div>
      )}

      {/* ======================================================
          Shared Error Feedback
          ====================================================== */}

      {error && activeTab !== "zip" && (
        <div
          className="c3-dataset-error"
          role="alert"
        >
          {error}
        </div>
      )}
    </div>
  );
}