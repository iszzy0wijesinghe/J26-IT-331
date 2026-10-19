/** @format */

import { useCallback, useEffect, useMemo, useState } from "react";

import { C3TrainingMonitor } from "./C3TrainingMonitor";

import {
  c3GoldenApi,
  type C3GoldenDataset,
} from "../api/c3Api";

import {
  c3TrainingApi,
  c3ExperimentApi,
  type C3TrainingRecord,
} from "../api/c3TrainingApi";

import "../styles/c3TrainingWorkspace.css";

/* ============================================================
   TYPES
============================================================ */

type Row = Record<string, unknown>;

type TrainingStage =
  | "IDLE"
  | "PREPARING"
  | "AUTHORIZING"
  | "VERIFYING"
  | "SUBMITTING";

/* ============================================================
   HELPERS
============================================================ */

const object = (v: unknown): Row =>
  v !== null && typeof v === "object" && !Array.isArray(v)
    ? (v as Row)
    : {};

const value = (v: unknown): string =>
  v === null || v === undefined
    ? "—"
    : typeof v === "object"
      ? JSON.stringify(v)
      : String(v);

const first = (r: Row, keys: string[]): unknown =>
  keys.map((k) => r[k]).find((v) => v !== undefined && v !== null);

const jobId = (r: Row): string =>
  value(first(r, ["job_id", "id", "training_job_id"]));

const jobStatus = (r: Row): string =>
  value(first(r, ["status", "state", "job_status"]));

const datasetId = (r: Row): string =>
  value(first(r, ["dataset_id", "source_dataset_id"]));

const jobList = (v: unknown): Row[] => {
  if (Array.isArray(v)) {
    return v.map(object);
  }

  const r = object(v);

  const list = first(r, [
    "jobs",
    "training_jobs",
    "items",
    "results",
  ]);

  return Array.isArray(list) ? list.map(object) : [];
};

const stateTone = (s: string) =>
  /fail|error|cancel/i.test(s)
    ? "error"
    : /complete|success|finish|ready/i.test(s)
      ? "success"
      : /run|progress|queue|pending|prepar|evaluat/i.test(s)
        ? "active"
        : "neutral";

const isReady = (r: Row | null): boolean | null => {
  if (!r) {
    return null;
  }

  const v = first(r, [
    "training_approved",
    "ready",
    "is_ready",
    "training_ready",
    "can_train",
    "eligible",
  ]);

  return typeof v === "boolean" ? v : null;
};

const compactFields = (
  r: Row,
  exclude: string[] = [],
) =>
  Object.entries(r)
    .filter(
      ([k, v]) =>
        !exclude.includes(k) &&
        (typeof v !== "object" || v === null),
    )
    .slice(0, 14);

const isActiveJob = (status: string): boolean =>
  /queued|pending|preparing|training|running|evaluating|registering|artifact_review|candidates_registered/i.test(
    status,
  ) &&
  !/completed|failed|cancelled|canceled/i.test(status);

const trainingStageMessage = (
  stage: TrainingStage,
): string => {
  switch (stage) {
    case "PREPARING":
      return "Preparing the research dataset…";

    case "AUTHORIZING":
      return "Recording synthetic-research authorization…";

    case "VERIFYING":
      return "Verifying server-side training readiness…";

    case "SUBMITTING":
      return "Creating and launching the automatic training job…";

    default:
      return "";
  }
};

/* ============================================================
   COMPONENT
============================================================ */

export function C3TrainingWorkspace() {
  /* ----------------------------------------------------------
     DATASET STATE
  ---------------------------------------------------------- */

  const [datasets, setDatasets] = useState<
    C3GoldenDataset[]
  >([]);

  const [selectedDataset, setSelectedDataset] =
    useState("");

  const [readiness, setReadiness] =
    useState<C3TrainingRecord | null>(null);

  const [researcher, setResearcher] = useState("");

  /* ----------------------------------------------------------
     TRAINING STATE
  ---------------------------------------------------------- */

  const [jobs, setJobs] = useState<Row[]>([]);

  const [selectedJob, setSelectedJob] = useState("");

  const [details, setDetails] =
    useState<C3TrainingRecord | null>(null);

  /* ----------------------------------------------------------
     UI STATE
  ---------------------------------------------------------- */

  const [loading, setLoading] = useState(true);

  const [checking, setChecking] = useState(false);

  const [starting, setStarting] = useState(false);

  const [refreshing, setRefreshing] = useState(false);

  const [showAdvanced, setShowAdvanced] =
    useState(false);

  const [trainingStage, setTrainingStage] =
    useState<TrainingStage>("IDLE");

  const [error, setError] = useState("");

  const [notice, setNotice] = useState("");

  /* ============================================================
     REFRESH DATA
  ============================================================ */

  const refresh = useCallback(
    async (signal?: AbortSignal) => {
      setRefreshing(true);

      try {
        const [ds, js] = await Promise.all([
          c3GoldenApi.list(signal),
          c3TrainingApi.jobs(signal),
        ]);

        if (signal?.aborted) {
          return;
        }

        setDatasets(ds.datasets);

        setSelectedDataset(
          (current) =>
            current ||
            ds.datasets[0]?.dataset_id ||
            "",
        );

        const items = jobList(js);

        setJobs(items);

        setSelectedJob(
          (current) =>
            current ||
            (items.length ? jobId(items[0]) : ""),
        );

        setError("");
      } catch (e) {
        if (!signal?.aborted) {
          setError(
            e instanceof Error
              ? e.message
              : "Unable to load training workspace.",
          );
        }
      } finally {
        if (!signal?.aborted) {
          setRefreshing(false);
          setLoading(false);
        }
      }
    },
    [],
  );

  /* ============================================================
     INITIAL LOAD
  ============================================================ */

  useEffect(() => {
    const ctrl = new AbortController();

    void refresh(ctrl.signal);

    return () => ctrl.abort();
  }, [refresh]);

  /* ============================================================
     DATASET READINESS
  ============================================================ */

  useEffect(() => {
    if (!selectedDataset) {
      setReadiness(null);
      return;
    }

    const ctrl = new AbortController();

    setChecking(true);

    setReadiness(null);

    setError("");

    setNotice("");

    void c3TrainingApi
      .readiness(selectedDataset, ctrl.signal)
      .then((result) => {
        if (!ctrl.signal.aborted) {
          setReadiness(result);
        }
      })
      .catch((e) => {
        if (!ctrl.signal.aborted) {
          setError(
            e instanceof Error
              ? e.message
              : "Readiness check failed.",
          );
        }
      })
      .finally(() => {
        if (!ctrl.signal.aborted) {
          setChecking(false);
        }
      });

    return () => ctrl.abort();
  }, [selectedDataset]);

  /* ============================================================
     SELECTED JOB DETAILS
  ============================================================ */

  useEffect(() => {
    if (!selectedJob || selectedJob === "—") {
      setDetails(null);
      return;
    }

    const ctrl = new AbortController();

    void c3TrainingApi
      .job(selectedJob, ctrl.signal)
      .then((result) => {
        if (!ctrl.signal.aborted) {
          setDetails(result);
        }
      })
      .catch((e) => {
        if (!ctrl.signal.aborted) {
          setError(
            e instanceof Error
              ? e.message
              : "Unable to load training job.",
          );
        }
      });

    return () => ctrl.abort();
  }, [selectedJob]);

  /* ============================================================
     DERIVED VALUES
  ============================================================ */

  const selectedDatasetInfo = useMemo(
    () =>
      datasets.find(
        (d) => d.dataset_id === selectedDataset,
      ),
    [datasets, selectedDataset],
  );

  const selectedJobSummary = jobs.find(
    (j) => jobId(j) === selectedJob,
  );

  const ready = isReady(readiness);

  const temporalReady =
    readiness?.temporal_ready === true;

  const readinessFields = readiness
    ? compactFields(readiness)
    : [];

  const result = object(details);

  const resultFields = compactFields(result, [
    "job_id",
    "id",
    "dataset_id",
    "status",
  ]);

  const activeJobs = useMemo(
    () =>
      jobs.filter((job) =>
        isActiveJob(jobStatus(job)),
      ),
    [jobs],
  );

  const selectedDatasetActiveJob = useMemo(
    () =>
      activeJobs.find(
        (job) =>
          datasetId(job) === selectedDataset,
      ),
    [activeJobs, selectedDataset],
  );

  const canAuthorizeAndTrain =
    Boolean(selectedDataset) &&
    temporalReady &&
    !checking &&
    !starting &&
    !selectedDatasetActiveJob &&
    (ready === true ||
      researcher.trim().length > 0);

  /* ============================================================
     AUTOMATIC TRAINING
  ============================================================ */

  async function startTraining() {
    if (
      !selectedDataset ||
      starting ||
      checking
    ) {
      return;
    }

    setError("");
    setNotice("");

    if (!temporalReady) {
      setError(
        "The selected dataset has not passed temporal readiness.",
      );
      return;
    }

    if (selectedDatasetActiveJob) {
      setSelectedJob(
        jobId(selectedDatasetActiveJob),
      );

      setNotice(
        "An active training job already exists for this dataset. The existing job has been selected.",
      );

      return;
    }

    const alreadyApproved = ready === true;

    if (
      !alreadyApproved &&
      !researcher.trim()
    ) {
      setError(
        "Enter the researcher's name before authorizing the experiment.",
      );

      return;
    }

    const confirmation = alreadyApproved
      ? [
          "Start automatic GeoNex C3 training?",
          "",
          `Dataset: ${selectedDataset}`,
          "",
          "GeoNex will:",
          "1. Create the training job.",
          "2. Launch the background worker.",
          "3. Execute the model training pipeline.",
          "4. Verify generated model artifacts.",
          "5. Register successful model candidates.",
          "6. Complete the training job.",
          "",
          "Models will not be activated automatically.",
        ].join("\n")
      : [
          "Authorize synthetic research and start training?",
          "",
          `Dataset: ${selectedDataset}`,
          `Researcher: ${researcher.trim()}`,
          "",
          "I confirm:",
          "",
          "• The dataset is used for synthetic research.",
          "• The experiment is not approved for field deployment.",
          "• Forecasts are not landslide probabilities.",
          "• Training may start automatically after authorization.",
          "",
          "Models will not be activated automatically.",
        ].join("\n");

    if (!window.confirm(confirmation)) {
      return;
    }

    setStarting(true);

    setTrainingStage("PREPARING");

    try {
      /* --------------------------------------------------------
         STEP 1: PREPARE + AUTHORIZE
      -------------------------------------------------------- */

      if (!alreadyApproved) {
        setNotice(
          "Preparing the synthetic research dataset…",
        );

        await c3ExperimentApi.prepare(
          selectedDataset,
        );

        setTrainingStage("AUTHORIZING");

        setNotice(
          "Recording research authorization…",
        );

        await c3ExperimentApi.authorize(
          selectedDataset,
          researcher.trim(),
          "Explicit synthetic-only GeoNex C3 research experiment. Not approved for field deployment.",
        );
      }

      /* --------------------------------------------------------
         STEP 2: VERIFY READINESS
      -------------------------------------------------------- */

      setTrainingStage("VERIFYING");

      setNotice(
        "Verifying training readiness…",
      );

      const updatedReadiness =
        await c3TrainingApi.readiness(
          selectedDataset,
        );

      setReadiness(updatedReadiness);

      if (
        updatedReadiness.training_approved !==
        true
      ) {
        throw new Error(
          "Research authorization was not confirmed by the backend. Training was not started.",
        );
      }

      if (
        updatedReadiness.temporal_ready !==
        true
      ) {
        throw new Error(
          "Temporal readiness is no longer valid. Training was not started.",
        );
      }

      /* --------------------------------------------------------
         STEP 3: SUBMIT AUTOMATIC JOB
      -------------------------------------------------------- */

      setTrainingStage("SUBMITTING");

      setNotice(
        "Submitting the automatic training job…",
      );

      const created =
        await c3TrainingApi.start(
          selectedDataset,
        );

      const createdJobId = jobId(created);

      if (
        !createdJobId ||
        createdJobId === "—"
      ) {
        throw new Error(
          "The backend did not return a valid training job ID.",
        );
      }

      /* --------------------------------------------------------
         STEP 4: UPDATE WORKSPACE
      -------------------------------------------------------- */

      setSelectedJob(createdJobId);

      await refresh();

      setSelectedJob(createdJobId);

      const reused =
        created.automatic_worker_launched ===
        false;

      setNotice(
        reused
          ? `Existing training job ${createdJobId} selected. No duplicate job was created.`
          : `Training job ${createdJobId} submitted successfully. Automatic worker execution has been requested.`,
      );
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Automatic training could not be started.",
      );
    } finally {
      setStarting(false);

      setTrainingStage("IDLE");
    }
  }

  /* ============================================================
     AUTOMATIC JOB REFRESH
  ============================================================ */

  useEffect(() => {
    if (!activeJobs.length) {
      return;
    }

    const interval = window.setInterval(() => {
      if (!starting && !refreshing) {
        void refresh();
      }
    }, 5000);

    return () => {
      window.clearInterval(interval);
    };
  }, [
    activeJobs.length,
    starting,
    refreshing,
    refresh,
  ]);

  /* ============================================================
     RENDER
  ============================================================ */

  return (
    <div
      className="c3-training"
      aria-label="C3 model training workspace"
    >
      {/* ======================================================
          HEADER
      ====================================================== */}

      <div className="c3-training-topline">
        <div>
          <span className="c3-training-eyebrow">
            TRAINING PIPELINE
          </span>

          <h3>Experiment control</h3>

          <p>
            Review dataset readiness, authorize
            synthetic research, and launch automatic
            model training.
          </p>
        </div>

        <button
          className="c3-training-secondary"
          type="button"
          onClick={() => void refresh()}
          disabled={refreshing}
        >
          {refreshing
            ? "Refreshing…"
            : "↻ Refresh jobs"}
        </button>
      </div>

      {/* ======================================================
          ALERTS
      ====================================================== */}

      {error && (
        <div
          className="c3-training-alert error"
          role="alert"
        >
          {error}

          <button
            type="button"
            onClick={() => setError("")}
            aria-label="Dismiss error"
          >
            ×
          </button>
        </div>
      )}

      {notice && (
        <div
          className="c3-training-alert success"
          role="status"
        >
          {notice}
        </div>
      )}

      {/* ======================================================
          MAIN GRID
      ====================================================== */}

      <div className="c3-training-columns">

        {/* ====================================================
            DATASET + AUTHORIZATION
        ==================================================== */}

        <section className="c3-training-card c3-training-setup">

          <div className="c3-training-section-heading">
            <span className="c3-training-step">
              01
            </span>

            <div>
              <h4>Choose research dataset</h4>

              <p>
                Validated, registered research
                datasets
              </p>
            </div>
          </div>

          <label
            className="c3-training-label"
            htmlFor="c3-train-dataset"
          >
            Dataset
          </label>

          <select
            id="c3-train-dataset"
            value={selectedDataset}
            onChange={(e) =>
              setSelectedDataset(
                e.target.value,
              )
            }
            disabled={
              loading ||
              starting ||
              !datasets.length
            }
          >
            <option value="">
              {loading
                ? "Loading datasets…"
                : "Select dataset"}
            </option>

            {datasets.map((d) => (
              <option
                key={d.dataset_id}
                value={d.dataset_id}
              >
                {d.filename || d.dataset_id}
                {" · "}
                {d.dataset_id}
              </option>
            ))}
          </select>

          {/* DATASET METRICS */}

          {selectedDatasetInfo && (
            <div className="c3-training-metrics">
              <div>
                <strong>
                  {selectedDatasetInfo.total_rows.toLocaleString()}
                </strong>

                <span>Observations</span>
              </div>

              <div>
                <strong>
                  {selectedDatasetInfo.device_count}
                </strong>

                <span>Devices</span>
              </div>

              <div>
                <strong>
                  {selectedDatasetInfo.episode_count}
                </strong>

                <span>Episodes</span>
              </div>
            </div>
          )}

          <div className="c3-training-divider" />

          {/* ==================================================
              READINESS
          ================================================== */}

          <div className="c3-training-section-heading">
            <span className="c3-training-step">
              02
            </span>

            <div>
              <h4>Training readiness</h4>

              <p>
                Server-side eligibility assessment
              </p>
            </div>
          </div>

          <div
            className={`c3-training-readiness ${
              ready === true
                ? "success"
                : ready === false
                  ? "error"
                  : "neutral"
            }`}
          >
            <span className="c3-training-indicator" />

            <strong>
              {checking
                ? "Checking dataset…"
                : ready === true
                  ? "Ready to train"
                  : temporalReady
                    ? "Research authorization required"
                    : readiness
                      ? "Dataset is not ready"
                      : "Choose a dataset"}
            </strong>
          </div>

          {readiness && (
            <p className="c3-training-footnote">
              Temporal suitability:{" "}
              <strong>
                {temporalReady
                  ? "PASSED"
                  : "NOT VERIFIED"}
              </strong>
              . Research approval:{" "}
              <strong>
                {ready === true
                  ? "APPROVED"
                  : "NOT APPROVED"}
              </strong>
              .
            </p>
          )}

          {/* ==================================================
              TECHNICAL DETAILS
          ================================================== */}

          <button
            className="c3-training-secondary c3-training-advanced-toggle"
            type="button"
            onClick={() =>
              setShowAdvanced(
                (v) => !v,
              )
            }
            aria-expanded={showAdvanced}
          >
            {showAdvanced
              ? "Hide technical details"
              : "Show technical details"}
          </button>

          {showAdvanced && readiness && (
            <dl className="c3-training-keyvalues">
              {readinessFields.map(([k, v]) => (
                <div key={k}>
                  <dt>
                    {k.replace(/_/g, " ")}
                  </dt>

                  <dd>{value(v)}</dd>
                </div>
              ))}
            </dl>
          )}

          {showAdvanced &&
            readiness &&
            Object.entries(readiness)
              .filter(
                ([, v]) =>
                  Array.isArray(v) ||
                  (v !== null &&
                    typeof v === "object"),
              )
              .map(([k, v]) => (
                <details
                  className="c3-training-details"
                  key={k}
                >
                  <summary>
                    {k.replace(/_/g, " ")}
                  </summary>

                  <pre>
                    {JSON.stringify(v, null, 2)}
                  </pre>
                </details>
              ))}

          {/* ==================================================
              RESEARCH AUTHORIZATION
          ================================================== */}

          {temporalReady &&
            ready !== true && (
              <div className="c3-training-authorization">

                <label
                  htmlFor="c3-researcher"
                  className="c3-training-label"
                >
                  Researcher name
                </label>

                <input
                  id="c3-researcher"
                  type="text"
                  value={researcher}
                  onChange={(event) =>
                    setResearcher(
                      event.target.value,
                    )
                  }
                  placeholder="Enter researcher name"
                  disabled={starting}
                  autoComplete="name"
                  style={{
                    width: "100%",
                    padding: "12px 14px",
                    borderRadius: 8,
                    border:
                      "1px solid #cbd5e1",
                    marginBottom: 12,
                    boxSizing: "border-box",
                  }}
                />

                <p className="c3-training-footnote">
                  Authorization permits synthetic
                  research training only. It does
                  not authorize deployment or
                  operational landslide warnings.
                </p>
              </div>
            )}

          {/* ACTIVE JOB WARNING */}

          {selectedDatasetActiveJob && (
            <div
              className="c3-training-alert success"
              role="status"
            >
              An active training job already
              exists for this dataset:{" "}
              <strong>
                {jobId(selectedDatasetActiveJob)}
              </strong>
            </div>
          )}

          {/* ==================================================
              TRAINING BUTTON
          ================================================== */}

          <button
            className="c3-training-primary"
            type="button"
            disabled={!canAuthorizeAndTrain}
            onClick={() =>
              void startTraining()
            }
          >
            {starting
              ? trainingStageMessage(
                  trainingStage,
                )
              : selectedDatasetActiveJob
                ? "Training already in progress"
                : ready === true
                  ? "Start automatic training →"
                  : "Authorize & start automatic training →"}
          </button>

          {ready !== true && (
            <p className="c3-training-footnote">
              Upload automatically validates and
              registers your dataset. Enter your
              researcher name and authorize the
              experiment to begin automatic
              training.
            </p>
          )}
        </section>

        {/* ====================================================
            TRAINING HISTORY
        ==================================================== */}

        <section className="c3-training-card c3-training-history">

          <div className="c3-training-section-heading">
            <span className="c3-training-step">
              03
            </span>

            <div>
              <h4>Training runs</h4>

              <p>
                {jobs.length} backend-reported
                {" "}
                job{jobs.length === 1 ? "" : "s"}
              </p>
            </div>
          </div>

          {loading ? (
            <p className="c3-training-empty">
              Loading training history…
            </p>
          ) : !jobs.length ? (
            <div className="c3-training-empty">
              <strong>
                No training jobs yet
              </strong>

              <p>
                Automatic training jobs will
                appear here.
              </p>
            </div>
          ) : (
            <div className="c3-training-joblist">
              {jobs.map((job, i) => (
                <button
                  type="button"
                  key={`${jobId(job)}-${i}`}
                  className={
                    selectedJob === jobId(job)
                      ? "selected"
                      : ""
                  }
                  onClick={() =>
                    setSelectedJob(
                      jobId(job),
                    )
                  }
                >
                  <span className="c3-training-jobhead">
                    <strong>
                      {jobId(job)}
                    </strong>

                    <span
                      className={`c3-training-badge ${
                        stateTone(
                          jobStatus(job),
                        )
                      }`}
                    >
                      {jobStatus(job)}
                    </span>
                  </span>

                  <small>
                    {datasetId(job)}
                  </small>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* ======================================================
          TRAINING INSPECTOR
      ====================================================== */}

      <section className="c3-training-card c3-training-inspector">

        <div className="c3-training-section-heading">
          <span className="c3-training-step">
            04
          </span>

          <div>
            <h4>Run inspector</h4>

            <p>
              Actual training job metadata
              and outcomes
            </p>
          </div>
        </div>

        {!selectedJob ||
        selectedJob === "—" ? (
          <p className="c3-training-empty">
            Select a training run to inspect
            its details.
          </p>
        ) : (
          <>
            <div className="c3-training-inspector-head">

              <div>
                <span className="c3-training-eyebrow">
                  SELECTED RUN
                </span>

                <h4>
                  {selectedJob}
                </h4>

                <p>
                  {datasetId(
                    selectedJobSummary ||
                      result,
                  )}
                </p>
              </div>

              <span
                className={`c3-training-badge ${
                  stateTone(
                    jobStatus(
                      details ||
                        selectedJobSummary ||
                        {},
                    ),
                  )
                }`}
              >
                {jobStatus(
                  details ||
                    selectedJobSummary ||
                    {},
                )}
              </span>
            </div>

            <dl className="c3-training-keyvalues grid">
              {resultFields
                .filter(([k]) =>
                  [
                    "current_stage",
                    "created_at",
                    "started_at",
                    "completed_at",
                    "error_message",
                  ].includes(k),
                )
                .map(([k, v]) => (
                  <div key={k}>
                    <dt>
                      {k.replace(/_/g, " ")}
                    </dt>

                    <dd>
                      {value(v)}
                    </dd>
                  </div>
                ))}
            </dl>

            {showAdvanced &&
              Object.entries(result)
                .filter(
                  ([, v]) =>
                    Array.isArray(v) ||
                    (v !== null &&
                      typeof v === "object"),
                )
                .map(([k, v]) => (
                  <details
                    className="c3-training-details"
                    key={k}
                  >
                    <summary>
                      {k.replace(/_/g, " ")}
                    </summary>

                    <pre>
                      {JSON.stringify(
                        v,
                        null,
                        2,
                      )}
                    </pre>
                  </details>
                ))}
          </>
        )}

        {selectedJob &&
          selectedJob !== "—" && (
            <C3TrainingMonitor
              jobId={selectedJob}
            />
          )}

        <p className="c3-training-footnote">
          Training and model activation are
          separate operations. Completed models
          must be independently reviewed before
          activation. This research interface
          does not generate artificial training
          progress.
        </p>
      </section>
    </div>
  );
}