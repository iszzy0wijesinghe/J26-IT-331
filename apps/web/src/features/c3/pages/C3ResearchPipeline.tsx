/** @format */

import { useCallback, useEffect, useRef, useState } from "react";

import { c3CSVApi, c3GoldenApi, type C3GoldenDataset } from "../api/c3Api";

import { c3TrainingApi } from "../api/c3TrainingApi";

import { c3ModelReviewApi } from "../api/c3ModelReviewApi";

import "../styles/c3ResearchPipeline.css";

type PipelineStatus =
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "BLOCKED";

type PipelineStep = {
  id: number;
  title: string;
  description: string;
  status: PipelineStatus;
  message?: string;
};

type TrainingJob = {
  job_id: string;
  dataset_id?: string;
  status?: string;
  current_stage?: string;
  error_message?: string | null;
};

type TrainingReadiness = {
  temporal_ready?: boolean;
  training_approved?: boolean;
  training_approval_reason?: string;
  [key: string]: unknown;
};

type Candidate = {
  model_version_id: string;
  dataset_id: string;
  model_name: string;
  horizon_minutes: number;
  validation_mae: number | null;
  validation_rmse: number | null;
};

type Props = {
  onOpenEvaluation?: () => void;
};

const INITIAL_STEPS: PipelineStep[] = [
  {
    id: 1,
    title: "Dataset validation",
    description: "Validate CSV structure and observations.",
    status: "PENDING",
  },
  {
    id: 2,
    title: "Golden Dataset registration",
    description: "Register validated observations.",
    status: "PENDING",
  },
  {
    id: 3,
    title: "Training readiness",
    description: "Assess temporal suitability and research approval.",
    status: "PENDING",
  },
  {
    id: 4,
    title: "Model training",
    description: "Train models for the supported forecast horizons.",
    status: "PENDING",
  },
  {
    id: 5,
    title: "Model evaluation",
    description: "Compare registered model candidates.",
    status: "PENDING",
  },
];

const TERMINAL_JOB_STATUSES = new Set([
  "COMPLETED",
  "FAILED",
  "CANCELLED",
  "CANCELED",
]);

function getError(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "An unexpected error occurred.";
}

function getJobStatus(job: TrainingJob): string {
  return String(job.status || "UNKNOWN").toUpperCase();
}

export function C3ResearchPipeline({ onOpenEvaluation }: Props) {
  const [file, setFile] = useState<File | null>(null);

  const [datasetId, setDatasetId] = useState("");

  const [datasets, setDatasets] = useState<C3GoldenDataset[]>([]);

  const [steps, setSteps] = useState<PipelineStep[]>(INITIAL_STEPS);

  const [readiness, setReadiness] = useState<TrainingReadiness | null>(null);

  const [job, setJob] = useState<TrainingJob | null>(null);

  const [candidates, setCandidates] = useState<Candidate[]>([]);

  const [busy, setBusy] = useState(false);

  const [polling, setPolling] = useState(false);

  const [error, setError] = useState("");

  const [notice, setNotice] = useState("");

  const mounted = useRef(true);

  const pollingRef = useRef(false);

  const currentJobId = useRef("");

  const updateStep = useCallback(
    (id: number, status: PipelineStatus, message?: string) => {
      setSteps((previous) =>
        previous.map((step) =>
          step.id === id ? { ...step, status, message } : step,
        ),
      );
    },
    [],
  );

  const refreshDatasets = useCallback(async () => {
    const response = await c3GoldenApi.list();

    if (mounted.current) {
      setDatasets(response.datasets);
    }

    return response.datasets;
  }, []);

  const loadCandidates = useCallback(
    async (id: string) => {
      const response = await c3ModelReviewApi.candidates();

      const matches = response.candidates.filter(
        (candidate) => candidate.dataset_id === id,
      );

      if (mounted.current) {
        setCandidates(matches);
      }

      if (matches.length > 0) {
        updateStep(
          5,
          "COMPLETED",
          `${matches.length} registered model candidates found.`,
        );
      }

      return matches;
    },
    [updateStep],
  );

  const checkReadiness = useCallback(
    async (id: string) => {
      updateStep(3, "RUNNING", "Checking training readiness...");

      const response = (await c3TrainingApi.readiness(id)) as TrainingReadiness;

      if (mounted.current) {
        setReadiness(response);
      }

      if (response.temporal_ready === true) {
        updateStep(
          3,
          "COMPLETED",
          response.training_approved === true
            ? "Temporal readiness passed; research approval reported."
            : "Temporal readiness passed; research approval not granted.",
        );
      } else {
        updateStep(
          3,
          "BLOCKED",
          "Dataset has not passed temporal readiness checks.",
        );
      }

      return response;
    },
    [updateStep],
  );

  const inspectExistingTraining = useCallback(
    async (id: string) => {
      const response = await c3TrainingApi.jobs();

      const records = (response as { jobs?: TrainingJob[] }).jobs || [];

      const matching = records.filter((record) => record.dataset_id === id);

      const latest = matching[0];

      if (!latest) {
        return null;
      }

      if (mounted.current) {
        setJob(latest);
      }

      const status = getJobStatus(latest);

      if (status === "COMPLETED") {
        updateStep(
          4,
          "COMPLETED",
          `Existing completed training job: ${latest.job_id}`,
        );

        await loadCandidates(id);
      } else if (
        status === "RUNNING" ||
        status === "QUEUED" ||
        status === "PENDING"
      ) {
        updateStep(4, "RUNNING", `Existing training job: ${latest.job_id}`);
      } else {
        updateStep(4, "FAILED", `Previous training job status: ${status}`);
      }

      return latest;
    },
    [loadCandidates, updateStep],
  );

  useEffect(() => {
    mounted.current = true;

    void refreshDatasets().catch((err) => {
      if (mounted.current) {
        setError(getError(err));
      }
    });

    return () => {
      mounted.current = false;
      pollingRef.current = false;
    };
  }, [refreshDatasets]);

  async function selectExistingDataset(id: string) {
    if (!id || busy) {
      return;
    }

    setDatasetId(id);
    setFile(null);
    setReadiness(null);
    setJob(null);
    setCandidates([]);
    setError("");
    setNotice("");
    setSteps(INITIAL_STEPS);

    updateStep(1, "COMPLETED", "Existing registered dataset selected.");

    updateStep(2, "COMPLETED", `Dataset ${id} is already registered.`);

    setBusy(true);

    try {
      await checkReadiness(id);
      await inspectExistingTraining(id);
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function prepareDataset() {
    if (!file || busy) {
      return;
    }

    setBusy(true);
    setError("");
    setNotice("");
    setDatasetId("");
    setReadiness(null);
    setJob(null);
    setCandidates([]);
    setSteps(INITIAL_STEPS);

    try {
      // STEP 1: Validate the selected CSV.

      updateStep(1, "RUNNING", "Validating uploaded observations...");

      const validation = await c3CSVApi.validate(file);

      if (validation.validation.status !== "VALIDATED") {
        updateStep(
          1,
          "FAILED",
          "CSV validation failed. Review the validation report.",
        );

        setError(
          "Dataset validation failed. Correct the CSV before registration.",
        );

        return;
      }

      updateStep(1, "COMPLETED", "CSV validation passed.");

      // STEP 2: Register validated observations.
      // The backend validates the file again before ingestion.

      updateStep(2, "RUNNING", "Registering Golden Dataset...");

      const upload = await c3CSVApi.upload(file);

      if (!upload.registered || !upload.dataset?.dataset_id) {
        updateStep(
          2,
          "FAILED",
          "Golden Dataset registration was not completed.",
        );

        setError("The backend did not confirm dataset registration.");

        return;
      }

      const id = upload.dataset.dataset_id;

      setDatasetId(id);

      updateStep(2, "COMPLETED", `Registered dataset: ${id}`);

      await refreshDatasets();

      // STEP 3: Check readiness.

      await checkReadiness(id);

      // Detect already completed training.
      // Do not submit duplicate training automatically.

      await inspectExistingTraining(id);

      setNotice(
        "Dataset preparation completed. Review training readiness before starting a job.",
      );
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function startTraining() {
    if (
      !datasetId ||
      busy ||
      polling ||
      readiness?.training_approved !== true
    ) {
      return;
    }

    const confirmed = window.confirm(
      [
        "Start C3 model training?",
        "",
        `Dataset: ${datasetId}`,
        "",
        "Training may take several minutes.",
        "Registered candidates will not be activated automatically.",
      ].join("\n"),
    );

    if (!confirmed) {
      return;
    }

    setBusy(true);
    setError("");
    setNotice("");

    updateStep(4, "RUNNING", "Submitting training job...");

    try {
      // Check again before creating a new job.

      const existing = await inspectExistingTraining(datasetId);

      if (
        existing &&
        ["QUEUED", "PENDING", "RUNNING"].includes(getJobStatus(existing))
      ) {
        setNotice("An existing training job is already in progress.");

        return;
      }

      const response = (await c3TrainingApi.start(datasetId)) as TrainingJob;

      if (!response.job_id) {
        throw new Error("Training API did not return a job identifier.");
      }

      setJob(response);

      setNotice(`Training job submitted: ${response.job_id}`);
    } catch (err) {
      updateStep(4, "FAILED", getError(err));

      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  // Poll existing and newly submitted training jobs.

  useEffect(() => {
    const jobId = job?.job_id;

    if (!jobId) {
      return;
    }

    const initialStatus = getJobStatus(job);

    if (TERMINAL_JOB_STATUSES.has(initialStatus)) {
      return;
    }

    currentJobId.current = jobId;

    pollingRef.current = true;

    setPolling(true);

    let stopped = false;
    let inFlight = false;

    const poll = async () => {
      if (stopped || inFlight || currentJobId.current !== jobId) {
        return;
      }

      inFlight = true;

      try {
        const response = (await c3TrainingApi.job(jobId)) as TrainingJob;

        if (stopped) {
          return;
        }

        setJob(response);

        const status = getJobStatus(response);

        if (status === "COMPLETED") {
          updateStep(4, "COMPLETED", "Training completed successfully.");

          pollingRef.current = false;
          setPolling(false);

          if (datasetId) {
            await loadCandidates(datasetId);
          }
        } else if (
          status === "FAILED" ||
          status === "CANCELLED" ||
          status === "CANCELED"
        ) {
          updateStep(
            4,
            "FAILED",
            response.error_message || `Training ended with status ${status}.`,
          );

          pollingRef.current = false;
          setPolling(false);
        } else {
          updateStep(
            4,
            "RUNNING",
            `${status} · ${response.current_stage || "Processing"}`,
          );
        }
      } catch (err) {
        if (!stopped) {
          setError(getError(err));
        }
      } finally {
        inFlight = false;
      }
    };

    void poll();

    const timer = window.setInterval(() => {
      void poll();
    }, 5000);

    return () => {
      stopped = true;
      pollingRef.current = false;
      window.clearInterval(timer);
      setPolling(false);
    };
  }, [job?.job_id, datasetId, loadCandidates, updateStep]);

  const completedCount = steps.filter(
    (step) => step.status === "COMPLETED",
  ).length;

  const progress = Math.round((completedCount / steps.length) * 100);

  const canStartTraining =
    Boolean(datasetId) &&
    readiness?.training_approved === true &&
    !busy &&
    !polling &&
    !(
      job &&
      ["COMPLETED", "RUNNING", "QUEUED", "PENDING"].includes(getJobStatus(job))
    );

  return (
    <div className="c3-pipeline">
      <header className="c3-pipeline-header">
        <div>
          <span className="c3-pipeline-eyebrow">
            GEONEX / C3 RESEARCH PIPELINE
          </span>

          <h3>Dataset-to-model workflow</h3>

          <p>
            Prepare a research dataset, assess readiness, execute training, and
            review registered models.
          </p>
        </div>

        <div className="c3-pipeline-progress-card">
          <strong>{progress}%</strong>
          <span>Pipeline stages completed</span>
        </div>
      </header>

      <div className="c3-pipeline-progress-track">
        <div style={{ width: `${progress}%` }} />
      </div>

      {error && (
        <div className="c3-pipeline-message error" role="alert">
          {error}
        </div>
      )}

      {notice && (
        <div className="c3-pipeline-message success" role="status">
          {notice}
        </div>
      )}

      <section className="c3-pipeline-card">
        <div className="c3-pipeline-section-heading">
          <span>01</span>

          <div>
            <h4>Research dataset</h4>

            <p>Upload a new CSV or continue with an existing Golden Dataset.</p>
          </div>
        </div>

        <div className="c3-pipeline-upload">
          <label htmlFor="c3-pipeline-file">Select observations CSV</label>

          <input
            id="c3-pipeline-file"
            type="file"
            accept=".csv,text/csv"
            disabled={busy || polling}
            onChange={(event) => {
              const selected = event.target.files?.[0] || null;

              setFile(selected);
            }}
          />

          <button
            type="button"
            className="c3-pipeline-primary"
            disabled={!file || busy || polling}
            onClick={() => void prepareDataset()}>
            {busy ? "Processing dataset..." : "Validate & register dataset"}
          </button>
        </div>

        <div className="c3-pipeline-divider" />

        <label htmlFor="c3-pipeline-existing">
          Continue with registered dataset
        </label>

        <select
          id="c3-pipeline-existing"
          value={datasetId}
          disabled={busy || polling}
          onChange={(event) => {
            void selectExistingDataset(event.target.value);
          }}>
          <option value="">Select existing dataset</option>

          {datasets.map((dataset) => (
            <option key={dataset.dataset_id} value={dataset.dataset_id}>
              {dataset.filename} — {dataset.dataset_id}
            </option>
          ))}
        </select>

        {datasetId && (
          <div className="c3-pipeline-dataset-id">
            <span>ACTIVE DATASET</span>
            <strong>{datasetId}</strong>
          </div>
        )}
      </section>

      <section className="c3-pipeline-card">
        <div className="c3-pipeline-section-heading">
          <span>02</span>

          <div>
            <h4>Pipeline execution</h4>

            <p>Actual status reported by the C3 backend.</p>
          </div>
        </div>

        <div className="c3-pipeline-steps">
          {steps.map((step) => (
            <div
              key={step.id}
              className={`c3-pipeline-step ${step.status.toLowerCase()}`}>
              <div className="c3-pipeline-step-index">{step.id}</div>

              <div className="c3-pipeline-step-content">
                <strong>{step.title}</strong>

                <p>{step.description}</p>

                {step.message && <small>{step.message}</small>}
              </div>

              <span className="c3-pipeline-status">{step.status}</span>
            </div>
          ))}
        </div>
      </section>

      {readiness && (
        <section className="c3-pipeline-card">
          <div className="c3-pipeline-section-heading">
            <span>03</span>

            <div>
              <h4>Research readiness</h4>

              <p>
                Temporal suitability and research approval are separate
                assessments.
              </p>
            </div>
          </div>

          <div className="c3-pipeline-readiness">
            <div>
              <span>Temporal readiness</span>

              <strong>
                {readiness.temporal_ready ? "PASSED" : "NOT PASSED"}
              </strong>
            </div>

            <div>
              <span>Research approval</span>

              <strong>
                {readiness.training_approved ? "APPROVED" : "NOT APPROVED"}
              </strong>
            </div>
          </div>

          {readiness.training_approval_reason && (
            <p className="c3-pipeline-explanation">
              {readiness.training_approval_reason}
            </p>
          )}

          <button
            type="button"
            className="c3-pipeline-primary"
            disabled={!canStartTraining}
            onClick={() => void startTraining()}>
            {polling ? "Training in progress..." : "Start model training"}
          </button>

          {readiness.training_approved !== true && (
            <p className="c3-pipeline-explanation">
              New training is disabled because the backend has not granted
              research approval. This interface does not override that decision.
            </p>
          )}
        </section>
      )}

      {job && (
        <section className="c3-pipeline-card">
          <div className="c3-pipeline-section-heading">
            <span>04</span>

            <div>
              <h4>Training execution</h4>

              <p>Current backend training job.</p>
            </div>
          </div>

          <div className="c3-pipeline-job">
            <div>
              <span>JOB ID</span>
              <strong>{job.job_id}</strong>
            </div>

            <div>
              <span>STATUS</span>
              <strong>{job.status || "UNKNOWN"}</strong>
            </div>

            <div>
              <span>STAGE</span>
              <strong>{job.current_stage || "—"}</strong>
            </div>
          </div>
        </section>
      )}

      {candidates.length > 0 && (
        <section className="c3-pipeline-card">
          <div className="c3-pipeline-section-heading">
            <span>05</span>

            <div>
              <h4>Registered model candidates</h4>

              <p>
                {candidates.length} models available for research evaluation.
              </p>
            </div>
          </div>

          <div className="c3-pipeline-model-summary">
            {[15, 30, 60].map((horizon) => {
              const models = candidates
                .filter((candidate) => candidate.horizon_minutes === horizon)
                .sort(
                  (a, b) =>
                    (a.validation_mae ?? Infinity) -
                    (b.validation_mae ?? Infinity),
                );

              const best = models[0];

              return (
                <div key={horizon}>
                  <span>{horizon}-minute horizon</span>

                  <strong>{best?.model_name || "No candidate"}</strong>

                  <small>
                    {best?.validation_mae != null
                      ? `Validation MAE: ${best.validation_mae.toFixed(4)}`
                      : "No validation metric"}
                  </small>
                </div>
              );
            })}
          </div>

          <button
            type="button"
            className="c3-pipeline-primary"
            onClick={onOpenEvaluation}>
            Open model evaluation →
          </button>
        </section>
      )}

      <footer className="c3-pipeline-disclaimer">
        Research demonstration only. Training metrics represent validation
        performance, not held-out test performance or field reliability. Model
        activation, operational forecasting, and adaptive replay require
        separate actions.
      </footer>
    </div>
  );
}
