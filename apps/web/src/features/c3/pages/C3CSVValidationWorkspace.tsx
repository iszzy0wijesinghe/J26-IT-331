/** @format */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from "react";

import {
  c3CSVApi,
  type C3CSVValidationResult,
} from "../api/c3Api";

import "../styles/c3CSVValidationWorkspace.css";

/* ============================================================
   Types
   ============================================================ */

type WorkspaceStatus =
  | "IDLE"
  | "VALIDATING"
  | "VALIDATED"
  | "FAILED";

type TerminalLevel = "INFO" | "SUCCESS" | "WARNING" | "ERROR";

type TerminalEntry = {
  id: number;
  timestamp: string;
  level: TerminalLevel;
  message: string;
};

type C3CSVValidationWorkspaceProps = {
  onDatasetRegistered?: (datasetId: string) => void;
};

/* ============================================================
   Constants
   ============================================================ */

const MAX_FILE_BYTES = 100 * 1024 * 1024;

const VALIDATION_STAGES = [
  {
    id: "upload",
    label: "Dataset received",
    description: "CSV transferred to the backend ingestion service",
  },
  {
    id: "schema",
    label: "Schema inspection",
    description: "Required columns and dataset structure",
  },
  {
    id: "quality",
    label: "Data quality checks",
    description: "Sensor values, timestamps, and operating modes",
  },
  {
    id: "storage",
    label: "Golden Database registration",
    description: "Validated observations saved persistently",
  },
  {
    id: "report",
    label: "Validation report",
    description: "Verified results returned by the backend",
  },
] as const;

/* ============================================================
   Helpers
   ============================================================ */

function formatNumber(value: number): string {
  return value.toLocaleString();
}

function formatTimestamp(value: string | null): string {
  if (!value) return "—";

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "An unexpected dataset ingestion error occurred.";
}

/* ============================================================
   Component
   ============================================================ */

export function C3CSVValidationWorkspace({
  onDatasetRegistered,
}: C3CSVValidationWorkspaceProps) {
  /* ----------------------------------------------------------
     Refs
     ---------------------------------------------------------- */

  const fileInputRef = useRef<HTMLInputElement>(null);
  const terminalRef = useRef<HTMLDivElement>(null);

  const terminalCounter = useRef(0);

  const requestController = useRef<AbortController | null>(null);

  /* ----------------------------------------------------------
     Upload State
     ---------------------------------------------------------- */

  const [file, setFile] = useState<File | null>(null);

  const [dragActive, setDragActive] = useState(false);

  const [status, setStatus] = useState<WorkspaceStatus>("IDLE");

  const [result, setResult] =
    useState<C3CSVValidationResult | null>(null);

  /* ----------------------------------------------------------
     Golden Database Registration
     ---------------------------------------------------------- */

  const [registeredDatasetId, setRegisteredDatasetId] =
    useState("");

  const [alreadyRegistered, setAlreadyRegistered] =
    useState(false);

  const [storedObservations, setStoredObservations] =
    useState<number | null>(null);

  /* ----------------------------------------------------------
     Feedback
     ---------------------------------------------------------- */

  const [error, setError] = useState("");

  const [showAllIssues, setShowAllIssues] = useState(false);

  /* ----------------------------------------------------------
     Terminal
     ---------------------------------------------------------- */

  const [terminalEntries, setTerminalEntries] =
    useState<TerminalEntry[]>([]);

  const [terminalExpanded, setTerminalExpanded] = useState(true);

  const [autoScroll, setAutoScroll] = useState(true);

  /* ----------------------------------------------------------
     Derived State
     ---------------------------------------------------------- */

  const validating = status === "VALIDATING";

  const registered =
    status === "VALIDATED" && registeredDatasetId !== "";

  /* ============================================================
     Activity Logging
     ============================================================ */

  const appendLog = useCallback(
    (level: TerminalLevel, message: string) => {
      terminalCounter.current += 1;

      const entry: TerminalEntry = {
        id: terminalCounter.current,
        timestamp: new Date().toLocaleTimeString(),
        level,
        message,
      };

      setTerminalEntries((current) =>
        [...current, entry].slice(-300),
      );
    },
    [],
  );

  /* ============================================================
     Terminal Auto Scroll
     ============================================================ */

  useEffect(() => {
    if (!autoScroll || !terminalExpanded) return;

    const terminal = terminalRef.current;

    if (terminal) {
      terminal.scrollTop = terminal.scrollHeight;
    }
  }, [terminalEntries, autoScroll, terminalExpanded]);

  /* ============================================================
     Cleanup
     ============================================================ */

  useEffect(() => {
    return () => {
      requestController.current?.abort();
    };
  }, []);

  /* ============================================================
     File Selection
     ============================================================ */

  const selectFile = useCallback(
    (selected: File | null) => {
      if (validating) return;

      setError("");
      setResult(null);
      setStatus("IDLE");

      setRegisteredDatasetId("");
      setAlreadyRegistered(false);
      setStoredObservations(null);

      setShowAllIssues(false);

      if (!selected) {
        setFile(null);
        return;
      }

      if (!selected.name.toLowerCase().endsWith(".csv")) {
        setFile(null);

        setError("Please select a .csv dataset file.");

        appendLog(
          "ERROR",
          "File selection rejected: unsupported file format.",
        );

        return;
      }

      if (selected.size === 0) {
        setFile(null);

        setError("The selected CSV file is empty.");

        appendLog(
          "ERROR",
          "File selection rejected: empty dataset.",
        );

        return;
      }

      if (selected.size > MAX_FILE_BYTES) {
        setFile(null);

        setError(
          "The selected CSV exceeds the 100 MiB upload limit.",
        );

        appendLog(
          "ERROR",
          "File selection rejected: file exceeds upload limit.",
        );

        return;
      }

      setFile(selected);

      appendLog(
        "INFO",
        `Selected dataset: ${selected.name} (${(
          selected.size / 1024
        ).toFixed(1)} KiB)`,
      );
    },
    [appendLog, validating],
  );

  /* ============================================================
     File Input
     ============================================================ */

  function handleFileChange(
    event: ChangeEvent<HTMLInputElement>,
  ) {
    selectFile(event.target.files?.[0] ?? null);

    event.target.value = "";
  }

  /* ============================================================
     Drag and Drop
     ============================================================ */

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();

    setDragActive(false);

    if (validating) return;

    selectFile(event.dataTransfer.files?.[0] ?? null);
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();

    if (!validating) {
      setDragActive(true);
    }
  }

  /* ============================================================
     Golden CSV Ingestion
     ============================================================ */

  async function handleValidateAndSave() {
    if (!file || validating) return;

    const controller = new AbortController();

    requestController.current = controller;

    setStatus("VALIDATING");
    setResult(null);
    setError("");
    setShowAllIssues(false);

    setRegisteredDatasetId("");
    setAlreadyRegistered(false);
    setStoredObservations(null);

    appendLog(
      "INFO",
      `Submitting ${file.name} to the Golden Data ingestion API...`,
    );

    try {
      /* ------------------------------------------------------
         Backend validation + registration
         ------------------------------------------------------ */

      const response = await c3CSVApi.upload(
        file,
        controller.signal,
      );

      if (controller.signal.aborted) return;

      const report = response.validation;

      setResult(report);

      /* ------------------------------------------------------
         Verified validation information
         ------------------------------------------------------ */

      appendLog(
        "INFO",
        `Schema version: ${report.schema_version}`,
      );

      appendLog(
        "INFO",
        `Processed ${formatNumber(report.total_rows)} observations.`,
      );

      appendLog(
        "INFO",
        `Detected ${report.devices} device(s) and ${report.episodes} episode(s).`,
      );

      appendLog(
        "INFO",
        `Valid rows: ${formatNumber(report.valid_rows)} / ${formatNumber(
          report.total_rows,
        )}`,
      );

      /* ------------------------------------------------------
         Validation issues
         ------------------------------------------------------ */

      for (const issue of report.issues) {
        const location =
          issue.row !== null
            ? `Row ${issue.row}${
                issue.column ? `, ${issue.column}` : ""
              }: `
            : issue.column
              ? `${issue.column}: `
              : "";

        appendLog(
          issue.severity === "ERROR"
            ? "ERROR"
            : "WARNING",
          `${location}${issue.message}`,
        );
      }

      /* ------------------------------------------------------
         Registration result
         ------------------------------------------------------ */

      if (
        report.status === "VALIDATED" &&
        response.registered &&
        response.dataset?.dataset_id
      ) {
        const dataset = response.dataset;

        setStatus("VALIDATED");

        setRegisteredDatasetId(dataset.dataset_id);

        setAlreadyRegistered(dataset.already_registered);

        setStoredObservations(dataset.observations);

        appendLog(
          "SUCCESS",
          "CSV validation passed.",
        );

        if (dataset.already_registered) {
          appendLog(
            "SUCCESS",
            `Dataset already registered: ${dataset.dataset_id}`,
          );
        } else {
          appendLog(
            "SUCCESS",
            `Dataset saved to Golden Database: ${dataset.dataset_id}`,
          );
        }

        appendLog(
          "INFO",
          `${formatNumber(
            dataset.observations,
          )} observations associated with this dataset.`,
        );

        /* ----------------------------------------------------
           Notify Dataset Manager
           ---------------------------------------------------- */

        onDatasetRegistered?.(dataset.dataset_id);
      } else {
        setStatus("FAILED");

        appendLog(
          "ERROR",
          `Dataset ingestion failed. Validation errors: ${report.error_count}.`,
        );

        appendLog(
          "WARNING",
          "No observations were registered by this upload.",
        );
      }

      appendLog(
        "INFO",
        "Automatic model training is not enabled yet.",
      );
    } catch (cause) {
      if (controller.signal.aborted) return;

      const message = getErrorMessage(cause);

      setError(message);
      setStatus("FAILED");

      appendLog(
        "ERROR",
        `Golden Data ingestion request failed: ${message}`,
      );
    } finally {
      if (requestController.current === controller) {
        requestController.current = null;
      }
    }
  }

  /* ============================================================
     Derived Validation Results
     ============================================================ */

  const totalMissing = result
    ? Object.values(result.missing_values).reduce(
        (sum, count) => sum + count,
        0,
      )
    : 0;

  const visibleIssues = result
    ? showAllIssues
      ? result.issues
      : result.issues.slice(0, 8)
    : [];

  /* ============================================================
     Render
     ============================================================ */

  return (
    <div className="c3-csv-workspace">
      {/* ======================================================
          Hero
          ====================================================== */}

      <section className="panel c3-csv-hero">
        <div className="c3-csv-hero-content">
          <div>
            <span className="section-overline">
              GEONEX C3 · DATA INTEGRITY
            </span>

            <h2>Golden Data Ingestion</h2>

            <p className="panel-subtitle">
              Upload sensor observations for automatic validation
              and persistent Golden Database registration.
              Invalid datasets are rejected without saving observations.
            </p>
          </div>

          <div
            className={`c3-csv-state c3-csv-state-${status.toLowerCase()}`}
            role="status"
            aria-live="polite"
          >
            <span className="c3-csv-state-dot" />

            {status === "IDLE"
              ? "READY TO UPLOAD"
              : status === "VALIDATING"
                ? "INGESTION RUNNING"
                : status === "VALIDATED"
                  ? "DATASET REGISTERED"
                  : "INGESTION FAILED"}
          </div>
        </div>

        <div className="c3-csv-hero-stats">
          <div>
            <span>SCHEMA</span>
            <strong>c3-observations-v1</strong>
          </div>

          <div>
            <span>FORECAST HORIZONS</span>
            <strong>15 · 30 · 60 min</strong>
          </div>

          <div>
            <span>DATA SOURCE</span>
            <strong>Raw sensor CSV</strong>
          </div>
        </div>
      </section>

      {/* ======================================================
          Main Grid
          ====================================================== */}

      <div className="c3-csv-main-grid">
        {/* ----------------------------------------------------
            Upload Panel
            ---------------------------------------------------- */}

        <section className="panel c3-csv-upload-panel">
          <div className="panel-heading">
            <div>
              <span className="section-overline">
                DATA INGESTION
              </span>

              <h2>Upload Observations</h2>
            </div>
          </div>

          <div
            className={[
              "c3-csv-dropzone",
              dragActive ? "is-dragging" : "",
              file ? "has-file" : "",
              validating ? "is-busy" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onDragOver={handleDragOver}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
          >
            <div
              className="c3-csv-upload-symbol"
              aria-hidden="true"
            >
              ↑
            </div>

            <h3>
              {file
                ? file.name
                : "Drop your CSV dataset here"}
            </h3>

            <p>
              {file
                ? `${(file.size / 1024).toFixed(
                    1,
                  )} KiB · Ready for ingestion`
                : "Choose a file or drag it into this workspace"}
            </p>

            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={handleFileChange}
              disabled={validating}
              className="c3-csv-file-input"
              aria-label="Select CSV dataset"
            />

            <button
              type="button"
              className="c3-csv-secondary-button"
              disabled={validating}
              onClick={() =>
                fileInputRef.current?.click()
              }
            >
              {file ? "Change File" : "Browse CSV Files"}
            </button>

            <span className="c3-csv-file-note">
              CSV only · Maximum 100 MiB · No held-out test uploads
            </span>
          </div>

          <button
            type="button"
            className="c3-csv-primary-button"
            disabled={!file || validating}
            onClick={() =>
              void handleValidateAndSave()
            }
          >
            {validating ? (
              <>
                <span className="c3-csv-button-spinner" />
                Validating and Saving...
              </>
            ) : (
              "Validate and Save to Golden DB →"
            )}
          </button>

          {/* --------------------------------------------------
              Successful Registration
              -------------------------------------------------- */}

          {registered && (
            <div
              className="c3-csv-registration-success"
              role="status"
            >
              <strong>
                {alreadyRegistered
                  ? "Dataset Already Registered"
                  : "Successfully Saved to Golden Database"}
              </strong>

              <p>
                Dataset ID:{" "}
                <code>{registeredDatasetId}</code>
              </p>

              {storedObservations !== null && (
                <p>
                  Stored observations:{" "}
                  <strong>
                    {formatNumber(storedObservations)}
                  </strong>
                </p>
              )}

              <p>
                This dataset is available in Registered Datasets.
              </p>
            </div>
          )}

          {error && (
            <div
              className="c3-csv-error"
              role="alert"
            >
              {error}
            </div>
          )}
        </section>

        {/* ----------------------------------------------------
            Processing Pipeline
            ---------------------------------------------------- */}

        <section className="panel c3-csv-progress-panel">
          <div className="panel-heading">
            <div>
              <span className="section-overline">
                PROCESSING PIPELINE
              </span>

              <h2>Ingestion Stages</h2>
            </div>
          </div>

          <div className="c3-csv-stage-list">
            {VALIDATION_STAGES.map((stage, index) => {
              // The API currently returns a final report, not
              // per-stage events. We therefore avoid fabricating
              // individual progress updates.
              const completed = registered;

              const active =
                validating && index === 0;

              return (
                <div
                  key={stage.id}
                  className={[
                    "c3-csv-stage",
                    completed ? "is-complete" : "",
                    active ? "is-active" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  <div className="c3-csv-stage-indicator">
                    {completed
                      ? "✓"
                      : active
                        ? "…"
                        : index + 1}
                  </div>

                  <div>
                    <strong>{stage.label}</strong>
                    <span>{stage.description}</span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="c3-csv-pipeline-note">
            {validating
              ? "The backend is validating the CSV and processing the registration request."
              : registered
                ? "Validation and database registration completed successfully."
                : result
                  ? "The backend returned a validation report. Dataset registration was not completed."
                  : "Select a dataset to begin Golden Data ingestion."}
          </div>
        </section>
      </div>

      {/* ======================================================
          Validation Results
          ====================================================== */}

      {result && (
        <section className="panel c3-csv-results">
          <div className="panel-heading">
            <div>
              <span className="section-overline">
                VALIDATION REPORT
              </span>

              <h2>Dataset Quality Overview</h2>
            </div>

            <span
              className={`c3-csv-result-badge ${
                result.status === "VALIDATED"
                  ? "is-valid"
                  : "is-invalid"
              }`}
            >
              {result.status}
            </span>
          </div>

          {/* --------------------------------------------------
              Metrics
              -------------------------------------------------- */}

          <div className="c3-csv-metric-grid">
            {[
              ["OBSERVATIONS", result.total_rows],
              ["VALID ROWS", result.valid_rows],
              ["INVALID ROWS", result.invalid_rows],
              ["DEVICES", result.devices],
              ["EPISODES", result.episodes],
              ["MISSING READINGS", totalMissing],
            ].map(([label, value]) => (
              <div
                className="c3-csv-metric"
                key={String(label)}
              >
                <span>{label}</span>

                <strong>
                  {formatNumber(Number(value))}
                </strong>
              </div>
            ))}
          </div>

          {/* --------------------------------------------------
              Quality and Metadata
              -------------------------------------------------- */}

          <div className="c3-csv-result-columns">
            <div className="c3-csv-result-card">
              <h3>Sensor Coverage</h3>

              <div className="c3-csv-sensor-list">
                {Object.entries(
                  result.missing_values,
                ).map(([sensor, missing]) => {
                  const available =
                    result.total_rows > 0
                      ? ((result.total_rows -
                          missing) /
                          result.total_rows) *
                        100
                      : 0;

                  return (
                    <div
                      className="c3-csv-sensor"
                      key={sensor}
                    >
                      <div>
                        <span>{sensor}</span>

                        <strong>
                          {available.toFixed(1)}%
                        </strong>
                      </div>

                      <div className="c3-csv-sensor-track">
                        <div
                          style={{
                            width: `${available}%`,
                          }}
                          className="c3-csv-sensor-fill"
                        />
                      </div>

                      <small>
                        {missing} missing reading(s)
                      </small>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="c3-csv-result-card">
              <h3>Dataset Metadata</h3>

              <div className="c3-csv-metadata-list">
                <div>
                  <span>Dataset</span>
                  <strong>{result.filename}</strong>
                </div>

                <div>
                  <span>Schema version</span>
                  <strong>
                    {result.schema_version}
                  </strong>
                </div>

                <div>
                  <span>First observation</span>
                  <strong>
                    {formatTimestamp(
                      result.timestamp_start,
                    )}
                  </strong>
                </div>

                <div>
                  <span>Last observation</span>
                  <strong>
                    {formatTimestamp(
                      result.timestamp_end,
                    )}
                  </strong>
                </div>

                <div>
                  <span>Errors</span>
                  <strong>{result.error_count}</strong>
                </div>

                <div>
                  <span>Warnings</span>
                  <strong>{result.warning_count}</strong>
                </div>
              </div>

              <h4>Operating Modes</h4>

              <div className="c3-csv-mode-list">
                {Object.entries(
                  result.operating_modes,
                ).map(([mode, count]) => (
                  <div key={mode}>
                    <span>{mode}</span>
                    <strong>
                      {formatNumber(count)}
                    </strong>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* --------------------------------------------------
              Validation Issues
              -------------------------------------------------- */}

          <div className="c3-csv-issues">
            <div className="c3-csv-issues-heading">
              <h3>Validation Findings</h3>

              <span>
                {result.error_count} errors ·{" "}
                {result.warning_count} warnings
              </span>
            </div>

            {result.issues.length === 0 ? (
              <p className="c3-csv-empty">
                No validation issues were reported.
              </p>
            ) : (
              <>
                {visibleIssues.map(
                  (issue, index) => (
                    <div
                      key={`${issue.code}-${issue.row}-${index}`}
                      className={`c3-csv-issue c3-csv-issue-${issue.severity.toLowerCase()}`}
                    >
                      <span>
                        {issue.severity}
                      </span>

                      <div>
                        <strong>
                          {issue.code}
                        </strong>

                        <p>
                          {issue.message}
                        </p>

                        {(issue.row !== null ||
                          issue.column !== null) && (
                          <small>
                            {issue.row !== null
                              ? `Row ${issue.row}`
                              : ""}

                            {issue.column
                              ? ` · Column: ${issue.column}`
                              : ""}
                          </small>
                        )}
                      </div>
                    </div>
                  ),
                )}

                {result.issues.length > 8 && (
                  <button
                    type="button"
                    className="c3-csv-text-button"
                    onClick={() =>
                      setShowAllIssues(
                        (value) => !value,
                      )
                    }
                  >
                    {showAllIssues
                      ? "Show fewer findings"
                      : `Show all ${result.issues.length} findings`}
                  </button>
                )}
              </>
            )}
          </div>

          <div className="c3-csv-research-notice">
            CSV validation verifies the currently implemented
            structural and row-level checks. It does not establish
            temporal forecast readiness, calibrated anomaly
            quality, model performance, or landslide-warning
            reliability.
          </div>
        </section>
      )}

      {/* ======================================================
          Activity Terminal
          ====================================================== */}

      <section className="panel c3-csv-terminal-panel">
        <div className="c3-csv-terminal-heading">
          <div>
            <span className="section-overline">
              INGESTION ACTIVITY
            </span>

            <h2>Activity Terminal</h2>
          </div>

          <div className="c3-csv-terminal-actions">
            <button
              type="button"
              onClick={() =>
                setAutoScroll((value) => !value)
              }
            >
              Auto-scroll:{" "}
              {autoScroll ? "ON" : "OFF"}
            </button>

            <button
              type="button"
              onClick={() =>
                setTerminalEntries([])
              }
            >
              Clear
            </button>

            <button
              type="button"
              onClick={() =>
                setTerminalExpanded(
                  (value) => !value,
                )
              }
            >
              {terminalExpanded
                ? "Collapse"
                : "Expand"}
            </button>
          </div>
        </div>

        {terminalExpanded && (
          <div
            ref={terminalRef}
            className="c3-csv-terminal"
            role="log"
            aria-label="CSV ingestion activity"
            aria-live="polite"
          >
            {terminalEntries.length === 0 ? (
              <div className="c3-csv-terminal-empty">
                <span>
                  geonex@c3:~$
                </span>{" "}
                Awaiting dataset activity...
              </div>
            ) : (
              terminalEntries.map(
                (entry) => (
                  <div
                    className={`c3-csv-terminal-line c3-csv-log-${entry.level.toLowerCase()}`}
                    key={entry.id}
                  >
                    <time>
                      {entry.timestamp}
                    </time>

                    <span className="c3-csv-terminal-level">
                      {entry.level}
                    </span>

                    <span>
                      {entry.message}
                    </span>
                  </div>
                ),
              )
            )}
          </div>
        )}

        <p className="c3-csv-terminal-footnote">
          Displays frontend upload activity and verified
          validation results returned by the backend.
          Live training-worker logs will be integrated
          separately when background training is implemented.
        </p>
      </section>
    </div>
  );
}