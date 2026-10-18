/** @format */

import { useCallback, useEffect, useState } from "react";

import {
  c3DatasetApi,
  type C3RegisteredDataset,
  type C3DatasetValidation,
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
    (dataset["validation_result"] as C3DatasetValidation | undefined);

  return candidate ?? null;
}

/* ============================================================
   Dataset Manager
   ============================================================ */

export function C3DatasetManager() {
  /* ----------------------------------------------------------
     Navigation
     ---------------------------------------------------------- */

  const [activeTab, setActiveTab] = useState<DatasetTab>("csv");

  /* ----------------------------------------------------------
     Dataset Registry
     ---------------------------------------------------------- */

  const [datasets, setDatasets] = useState<C3RegisteredDataset[]>([]);

  const [selectedId, setSelectedId] = useState("");

  const [details, setDetails] = useState<DatasetDetails | null>(null);

  /* ----------------------------------------------------------
     Loading States
     ---------------------------------------------------------- */

  const [loading, setLoading] = useState(true);

  const [loadingDetails, setLoadingDetails] = useState(false);

  const [uploading, setUploading] = useState(false);

  /* ----------------------------------------------------------
     ZIP Upload
     ---------------------------------------------------------- */

  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  /* ----------------------------------------------------------
     Feedback
     ---------------------------------------------------------- */

  const [error, setError] = useState("");

  const [success, setSuccess] = useState("");

  /* ============================================================
     Load Registered Datasets
     ============================================================ */

  const loadDatasets = useCallback(async (signal?: AbortSignal) => {
    const response = await c3DatasetApi.list(signal);

    if (signal?.aborted) return;

    setDatasets(response.datasets);

    setSelectedId((current) => {
      const exists = response.datasets.some(
        (dataset) => dataset.dataset_id === current,
      );

      if (exists) {
        return current;
      }

      return response.datasets[0]?.dataset_id ?? "";
    });
  }, []);

  /* ============================================================
     Initial Dataset Loading
     ============================================================ */

  useEffect(() => {
    const controller = new AbortController();

    setLoading(true);

    loadDatasets(controller.signal)
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;

        setError(
          cause instanceof Error
            ? cause.message
            : "Unable to load registered datasets",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [loadDatasets]);

  /* ============================================================
     Load Selected Dataset Details
     ============================================================ */

  useEffect(() => {
    if (!selectedId) {
      setDetails(null);
      setLoadingDetails(false);
      return;
    }

    const controller = new AbortController();

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

        setError(
          cause instanceof Error
            ? cause.message
            : "Unable to load dataset details",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadingDetails(false);
        }
      });

    return () => controller.abort();
  }, [selectedId]);

  /* ============================================================
     ZIP Dataset Upload
     ============================================================ */

  async function handleUpload() {
    if (!selectedFile || uploading) return;

    setUploading(true);

    setError("");
    setSuccess("");

    try {
      const response = await c3DatasetApi.upload(selectedFile);

      setSuccess(response.message);

      await loadDatasets();

      setSelectedId(response.dataset.dataset_id);

      setSelectedFile(null);

      // After successful registration, open the dataset library.
      setActiveTab("registered");
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Dataset upload failed",
      );
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

  const validation = getValidation(details);

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
          Validate raw sensor observations, inspect registered datasets,
          and import prepared forecasting data. Held-out test records
          remain excluded from dataset uploads.
        </p>

        <div className="c3-dataset-summary">
          <div>
            <span>REGISTERED DATASETS</span>

            <strong>
              {loading ? "…" : datasets.length}
            </strong>
          </div>

          <div>
            <span>SELECTED DATASET</span>

            <strong>{selectedId || "None"}</strong>
          </div>

          <div>
            <span>DATASET STATUS</span>

            <strong>
              {loadingDetails
                ? "Loading…"
                : details?.status ?? "—"}
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
            activeTab === "csv" ? "active" : ""
          }`}
          aria-current={activeTab === "csv" ? "page" : undefined}
          onClick={() => changeTab("csv")}
        >
          <span
            className="c3-dataset-navigation-icon"
            aria-hidden="true"
          >
            ◈
          </span>

          <span className="c3-dataset-navigation-label">
            CSV Validation
          </span>
        </button>

        <button
          type="button"
          className={`c3-dataset-navigation-button ${
            activeTab === "registered" ? "active" : ""
          }`}
          aria-current={activeTab === "registered" ? "page" : undefined}
          onClick={() => changeTab("registered")}
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
            activeTab === "zip" ? "active" : ""
          }`}
          aria-current={activeTab === "zip" ? "page" : undefined}
          onClick={() => changeTab("zip")}
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
          CSV Validation Workspace
          ====================================================== */}

      {activeTab === "csv" && (
        <div
          key="csv"
          className="c3-dataset-workspace"
        >
          <C3CSVValidationWorkspace />
        </div>
      )}

      {/* ======================================================
          Registered Datasets Workspace
          ====================================================== */}

      {activeTab === "registered" && (
        <div
          key="registered"
          className="c3-dataset-workspace"
        >
          {/* --------------------------------------------------
              Dataset Library
              -------------------------------------------------- */}

          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="section-overline">
                  DATASET LIBRARY
                </span>

                <h2>Registered Datasets</h2>
              </div>

              <span className="live-chip">
                {datasets.length} registered
              </span>
            </div>

            <p className="panel-subtitle">
              Explore datasets that have completed backend
              registration and integrity validation.
            </p>

            {loading ? (
              <div className="c3-dataset-loading">
                <span className="c3-dataset-loading-spinner" />

                <p className="c3-inline-note">
                  Loading registered datasets…
                </p>
              </div>
            ) : datasets.length === 0 ? (
              <p className="c3-inline-note">
                No datasets have been registered yet.
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
                      setSelectedId(dataset.dataset_id);
                      setError("");
                    }}
                  >
                    <div>
                      <strong>
                        {dataset.dataset_id}
                      </strong>

                      <span>
                        Synthetic C3 forecasting dataset
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

          {/* --------------------------------------------------
              Dataset Inspection
              -------------------------------------------------- */}

          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="section-overline">
                  DATASET INSPECTION
                </span>

                <h2>Dataset Details</h2>
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
                Select a registered dataset to inspect its
                validation results.
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
                    <span>Held-out Test Included</span>

                    <strong>
                      {details.held_out_test_included
                        ? "YES"
                        : "NO"}
                    </strong>
                  </div>

                  <div>
                    <span>Source</span>

                    <strong>
                      {validation?.source_origin ?? "Synthetic"}
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
                        ["train", "validation"] as const
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
                              <span>Missing readings</span>

                              <strong>
                                {statistics.missing_readings.toLocaleString()}
                              </strong>
                            </div>

                            <h5>
                              Forecast horizons
                            </h5>

                            {[15, 30, 60].map((horizon) => (
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
                            ))}
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}
              </>
            )}

            <p className="c3-research-warning">
              Registered datasets are used for synthetic
              forecasting research. Dataset validation does not
              establish landslide-warning reliability.
            </p>
          </section>
        </div>
      )}

      {/* ======================================================
          ZIP Dataset Import Workspace
          ====================================================== */}

      {activeTab === "zip" && (
        <div
          key="zip"
          className="c3-dataset-workspace"
        >
          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="section-overline">
                  DATASET IMPORT
                </span>

                <h2>Import Prepared Dataset</h2>
              </div>

              <span className="live-chip">
                ZIP dataset registration
              </span>
            </div>

            <p className="panel-subtitle">
              Upload a prepared dataset ZIP containing exactly
              the required training and validation files.
              The backend verifies dataset integrity,
              compatibility, and episode-disjoint splitting
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
                disabled={!selectedFile || uploading}
                onClick={() => void handleUpload()}
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
              Only manifest.json, train.jsonl.gz, and
              validation.jsonl.gz are permitted in the ZIP.
              Held-out test records must not be uploaded.
              Dataset registration does not automatically
              start model training.
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