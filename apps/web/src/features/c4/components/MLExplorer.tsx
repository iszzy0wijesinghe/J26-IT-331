
import { useEffect, useState } from "react";

interface ModelOption {
  key: string;
  label: string;
  artifact: string;
  runtime_default: boolean;
  notes: string;
}

interface FeatureInfo {
  order: number;
  feature: string;
  family: string;
  description: string;
}

interface StoredMetrics {
  accuracy: number;
  precision_macro: number;
  recall_macro: number;
  f1_macro: number;
  precision_per_class?: Record<string, number>;
  recall_per_class?: Record<string, number>;
  f1_per_class?: Record<string, number>;
  confusion_matrix?: number[][];
}

interface ModelProfile {
  label: string;
  artifact: string;
  model_type: string;
  n_features: number;
  classes: string[];
  n_estimators: number | null;
  training_metadata: Record<string, unknown>;
  runtime_default: boolean;
  notes: string;
  stored_metrics: StoredMetrics | null;
  supports_probabilities: boolean;
}

interface ModelProfileResponse {
  key: string;
  profile: ModelProfile;
  features: FeatureInfo[];
}

interface TrainingPreview {
  filename: string;
  rows: number;
  columns: number;
  unique_devices: number;
  class_distribution: Record<string, number>;
  features: string[];
  preview: Record<string, unknown>[];
  message: string;
}

interface TrainingResult {
  training_id: string;
  filename: string;
  accuracy: number;
  classes: string[];
  classification_report: Record<string, unknown>;
  confusion_matrix: number[][];
  train_rows: number;
  validation_rows: number;
  test_rows: number;
  unique_devices: number;
  feature_importance: Record<string, unknown>[];
  sample_predictions: Record<string, unknown>[];
  runtime_compatibility_verified: boolean;
  message: string;
}


interface TrainingJobStatus {
  training_id: string;
  status: "running" | "completed" | "failed";
  stage: string;
  message: string;
  result?: TrainingResult;
}


interface SavedCandidate {
  saved: boolean;
  candidate_path: string;
  runtime_compatibility_verified: boolean;
  message: string;
}

const API_BASE = "http://127.0.0.1:8000";
const MAX_CSV_SIZE = 10 * 1024 * 1024;


const TRAINING_STAGES = [
  { key: "preparing_data", label: "Prepare telemetry data" },
  { key: "splitting_devices", label: "Split devices into datasets" },
  { key: "training_model", label: "Train Random Forest" },
  { key: "evaluating_model", label: "Evaluate test performance" },
  { key: "completed", label: "Training completed" },
];


async function readApiError(response: Response): Promise<string> {
  try {
    const body = await response.json();

    if (typeof body.detail === "string") {
      return body.detail;
    }

    return body.detail
      ? JSON.stringify(body.detail)
      : `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function humanizeKey(value: string): string {
  return value.replaceAll("_", " ");
}

function formatPercentage(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "Unavailable";
  }

  return `${(value * 100).toFixed(2)}%`;
}

export default function MLExplorer() {
  const [models, setModels] = useState<ModelOption[]>([]);
  const [selectedModel, setSelectedModel] = useState(
    "random_forest_corrected",
  );
  const [profile, setProfile] = useState<ModelProfile | null>(null);
  const [features, setFeatures] = useState<FeatureInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [trainingFile, setTrainingFile] = useState<File | null>(null);
  const [trainingPreview, setTrainingPreview] =
    useState<TrainingPreview | null>(null);
  const [trainingResult, setTrainingResult] =
    useState<TrainingResult | null>(null);
  const [trainingError, setTrainingError] = useState("");
  const [trainingProgress, setTrainingProgress] =
  useState<TrainingJobStatus | null>(null);
  const [trainingLoading, setTrainingLoading] = useState(false);
  const [savingCandidate, setSavingCandidate] = useState(false);
  const [savedCandidate, setSavedCandidate] =
    useState<SavedCandidate | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadModels() {
      try {
        const response = await fetch(`${API_BASE}/api/c4/models`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(
            `Could not load model list (${response.status})`,
          );
        }

        const result = await response.json();
        const availableModels: ModelOption[] = result.models ?? [];

        setModels(availableModels);

        const defaultKey = availableModels.some(
          (model) => model.key === result.default_model,
        )
          ? result.default_model
          : availableModels[0]?.key;

        if (defaultKey) {
          setSelectedModel(defaultKey);
        } else {
          setError("No model artifacts are available.");
          setLoading(false);
        }
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
          setLoading(false);
        }
      }
    }

    void loadModels();

    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedModel) return;

    const controller = new AbortController();

    async function loadProfile() {
      setLoading(true);
      setError("");
      setProfile(null);
      setFeatures([]);

      try {
        const response = await fetch(
          `${API_BASE}/api/c4/models/${encodeURIComponent(selectedModel)}`,
          { signal: controller.signal },
        );

        if (!response.ok) {
          throw new Error(await readApiError(response));
        }

        const result: ModelProfileResponse = await response.json();

        setProfile(result.profile);
        setFeatures(result.features ?? []);
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadProfile();

    return () => controller.abort();
  }, [selectedModel]);

  async function previewTrainingFile(file: File) {
    setTrainingError("");
    setTrainingPreview(null);
    setTrainingResult(null);
    setSavedCandidate(null);
    setTrainingFile(null);

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setTrainingError("Please select a CSV file.");
      return;
    }

    if (file.size > MAX_CSV_SIZE) {
      setTrainingError("The file exceeds the 10 MB upload limit.");
      return;
    }

    if (file.size === 0) {
      setTrainingError("The selected file is empty.");
      return;
    }

    setTrainingFile(file);
    setTrainingLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE}/api/c4/training/preview`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      setTrainingPreview((await response.json()) as TrainingPreview);
    } catch (err) {
      setTrainingError(
        err instanceof Error ? err.message : "Dataset preview failed.",
      );
    } finally {
      setTrainingLoading(false);
    }
  }

  
async function trainUploadedFile() {
  if (!trainingFile) {
    setTrainingError("Choose a training CSV first.");
    return;
  }

  setTrainingError("");
  setTrainingResult(null);
  setTrainingProgress(null);
  setSavedCandidate(null);
  setTrainingLoading(true);

  try {
    const formData = new FormData();
    formData.append("file", trainingFile);

    const response = await fetch(`${API_BASE}/api/c4/training/train`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await readApiError(response));
    }

    const started = (await response.json()) as TrainingJobStatus;
    setTrainingProgress(started);

    while (true) {
      const statusResponse = await fetch(
        `${API_BASE}/api/c4/training/${encodeURIComponent(started.training_id)}/status`,
      );

      if (!statusResponse.ok) {
        throw new Error(await readApiError(statusResponse));
      }

      const status = (await statusResponse.json()) as TrainingJobStatus;
      setTrainingProgress(status);

      if (status.status === "failed") {
        throw new Error(status.message || "Model training failed.");
      }

      if (status.status === "completed") {
        if (!status.result) {
          throw new Error("Training completed without returning its results.");
        }

        setTrainingResult(status.result);
        break;
      }

      await new Promise((resolve) => window.setTimeout(resolve, 650));
    }
  } catch (err) {
    setTrainingError(
      err instanceof Error ? err.message : "Model training failed.",
    );
  } finally {
    setTrainingLoading(false);
  }
}


  async function saveCandidate() {
    if (!trainingResult || savingCandidate || savedCandidate) return;

    setTrainingError("");
    setSavingCandidate(true);

    try {
      const response = await fetch(
        `${API_BASE}/api/c4/training/${encodeURIComponent(trainingResult.training_id)}/save`,
        { method: "POST" },
      );

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      const result = (await response.json()) as SavedCandidate;
      setSavedCandidate(result);
    } catch (err) {
      setTrainingError(
        err instanceof Error
          ? err.message
          : "Saving the candidate failed.",
      );
    } finally {
      setSavingCandidate(false);
    }
  }

  const selectedOption = models.find(
    (model) => model.key === selectedModel,
  );

  return (
    <main className="c4-ml-explorer">
      <header className="c4-ml-header">
        <div>
          <span className="c4-ml-eyebrow">C4 / MODEL EXPLORER</span>
          <h2 className="c4-ml-page-title">Behavioral ML Models</h2>
          <p className="c4-ml-page-description">
            Inspect saved model artifacts, review their metadata and
            evaluation metrics, and train separate candidate models.
          </p>
        </div>
      </header>

      <section className="c4-ml-model-filter">
        <div className="c4-ml-model-filter-copy">
          <span className="c4-ml-eyebrow">MODEL SELECTION</span>
          <h3>Choose a C4 model</h3>
          <p>
            Inspect a saved artifact. Changing this selection does not retrain
            or replace the runtime model.
          </p>
        </div>

        <div className="c4-ml-model-filter-control">
          <label htmlFor="c4-model-select">Model artifact</label>
          <select
            id="c4-model-select"
            value={selectedModel}
            onChange={(event) => setSelectedModel(event.target.value)}
            disabled={models.length === 0}
          >
            {models.map((model) => (
              <option key={model.key} value={model.key}>
                {model.label}
              </option>
            ))}
          </select>
          <span className="c4-ml-model-filter-path">
            {selectedOption?.artifact ?? "Artifact not selected"}
          </span>
        </div>
      </section>

      {loading && (
        <div className="c4-ml-state" role="status">
          <span className="c4-ml-spinner" />
          <p>Loading metadata from the selected model artifact…</p>
        </div>
      )}

      {error && (
        <div className="c4-ml-state c4-ml-state-error" role="alert">
          <h3>Model metadata could not be loaded</h3>
          <p>{error}</p>
          <p>Check that the Python API is running and the artifact exists.</p>
        </div>
      )}

      {!loading && !error && profile && (
        <>
          <section className="c4-ml-metrics">
            <article className="c4-ml-metric-card c4-ml-metric-model">
              <span className="c4-ml-metric-label">Model type</span>
              <strong className="c4-ml-metric-value">
                {profile.model_type}
              </strong>
              <small>{profile.label}</small>
            </article>

            <article className="c4-ml-metric-card c4-ml-metric-features">
              <span className="c4-ml-metric-label">Features</span>
              <strong className="c4-ml-metric-value">
                {profile.n_features}
              </strong>
              <small>Reported by the artifact</small>
            </article>

            <article className="c4-ml-metric-card c4-ml-metric-classes">
              <span className="c4-ml-metric-label">Classes</span>
              <strong className="c4-ml-metric-value">
                {profile.classes?.length ?? 0}
              </strong>
              <small>
                {profile.classes?.length
                  ? profile.classes.join(", ")
                  : "No class labels"}
              </small>
            </article>

            <article className="c4-ml-metric-card c4-ml-metric-runtime">
              <span className="c4-ml-metric-label">Runtime default</span>
              <strong className="c4-ml-metric-value">
                {profile.runtime_default ? "YES" : "NO"}
              </strong>
              <small>
                {profile.runtime_default
                  ? "Configured C4 runtime artifact"
                  : "Inspection/comparison artifact"}
              </small>
            </article>
          </section>

          <section className="c4-ml-section">
            <div className="c4-ml-section-heading">
              <div>
                <h3>Model details</h3>
                <p>Information read from the selected model artifact.</p>
              </div>
            </div>

            <dl className="c4-ml-details">
              <div>
                <dt>Artifact path</dt>
                <dd>{profile.artifact}</dd>
              </div>
              <div>
                <dt>Estimator count</dt>
                <dd>
                  {profile.n_estimators ?? "Not applicable / unavailable"}
                </dd>
              </div>
              <div>
                <dt>Training metadata</dt>
                <dd>
                  {Object.keys(profile.training_metadata ?? {}).length
                    ? JSON.stringify(profile.training_metadata)
                    : "Not stored in this artifact"}
                </dd>
              </div>
              <div>
                <dt>Probability support</dt>
                <dd>
                  {profile.supports_probabilities
                    ? "Supported"
                    : "Not supported by this explorer's scoring contract"}
                </dd>
              </div>
              <div>
                <dt>Description</dt>
                <dd>{profile.notes || "No description stored."}</dd>
              </div>
            </dl>
          </section>

          <section className="c4-ml-section">
            <div className="c4-ml-section-heading">
              <div>
                <h3>Stored evaluation metrics</h3>
                <p>Previously saved metrics, not newly calculated scores.</p>
              </div>
            </div>

            {profile.stored_metrics ? (
              <div className="c4-ml-submetrics c4-ml-submetrics-four">
                {(
                  [
                    ["Accuracy", profile.stored_metrics.accuracy],
                    ["Macro precision", profile.stored_metrics.precision_macro],
                    ["Macro recall", profile.stored_metrics.recall_macro],
                    ["Macro F1", profile.stored_metrics.f1_macro],
                  ] as [string, number][]
                ).map(([label, value]) => (
                  <article className="c4-ml-metric-card" key={label}>
                    <span className="c4-ml-metric-label">{label}</span>
                    <strong className="c4-ml-metric-value">
                      {formatPercentage(value)}
                    </strong>
                  </article>
                ))}
              </div>
            ) : (
              <div className="c4-ml-placeholder">
                <h4>No stored evaluation metrics</h4>
                <p>
                  This artifact does not provide stored evaluation metrics.
                  That does not mean the model has zero accuracy.
                </p>
              </div>
            )}

            {profile.stored_metrics && (
              <>
                {profile.stored_metrics.recall_per_class && (
                  <>
                    <h4>Recall by class</h4>
                    <div className="c4-ml-table-wrapper">
                      <table className="c4-ml-table">
                        <thead>
                          <tr>
                            <th>Class</th>
                            <th>Recall</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(
                            profile.stored_metrics.recall_per_class,
                          ).map(([label, value]) => (
                            <tr key={label}>
                              <td>{label}</td>
                              <td>{formatPercentage(value)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </>
            )}
          </section>

          <section className="c4-ml-section">
            <div className="c4-ml-section-heading">
              <div>
                <h3>Actual feature schema</h3>
                <p>
                  Inspect the feature names expected by the selected model.
                </p>
              </div>
              <span className="c4-ml-count-badge">
                {features.length} features
              </span>
            </div>

            {features.length > 0 ? (
              <div className="c4-ml-table-wrapper">
                <table className="c4-ml-table">
                  <thead>
                    <tr>
                      <th>Order</th>
                      <th>Feature</th>
                      <th>Family</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {features.map((feature) => (
                      <tr key={feature.feature}>
                        <td>{feature.order}</td>
                        <td>
                          <code className="c4-ml-feature-name">
                            {feature.feature}
                          </code>
                        </td>
                        <td>
                          <span className="c4-ml-family">
                            {feature.family}
                          </span>
                        </td>
                        <td>
                          {feature.description || "No description available"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="c4-ml-placeholder">
                <p>No feature schema is available for this artifact.</p>
              </div>
            )}
          </section>

          {profile.model_type.toLowerCase().includes("isolation") && (
            <div className="c4-ml-notice c4-ml-notice-warning">
              <span className="c4-ml-notice-icon">!</span>
              <div>
                <h3>Unsupervised anomaly detector</h3>
                <p>
                  Isolation Forest is an unsupervised anomaly detector. It
                  should not be treated as a drop-in replacement for the
                  current C4 behavioral-score fusion pipeline.
                </p>
              </div>
            </div>
          )}

          <section className="c4-ml-section c4-ml-csv-panel">
            <div className="c4-ml-csv-heading">
              <div>
                <span className="c4-ml-eyebrow">MODEL DEVELOPMENT</span>
                <h3>Upload &amp; Train Candidate</h3>
                <p>
                  Upload labelled telemetry data, preview the prepared
                  dataset, train a Random Forest candidate, and review its
                  held-out test results.
                </p>
              </div>
              <div className="c4-ml-csv-icon" aria-hidden="true">
                ML
              </div>
            </div>

            <label className="c4-ml-upload-area">
              <span className="c4-ml-upload-symbol" aria-hidden="true">
                ↑
              </span>
              <strong>
                {trainingFile ? trainingFile.name : "Choose a training CSV"}
              </strong>
              <span>
                {trainingFile
                  ? formatBytes(trainingFile.size)
                  : "Select a labelled telemetry CSV up to 10 MB."}
              </span>
              <input
                type="file"
                accept=".csv,text/csv"
                aria-label="Choose a CSV file for model training"
                disabled={trainingLoading || savingCandidate}
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  if (file) void previewTrainingFile(file);
                  event.currentTarget.value = "";
                }}
              />
            </label>

            <p className="c4-ml-csv-model">
              Training creates a separate candidate model. It does not replace
              the active C4 runtime model.
            </p>

           
{trainingLoading && (
  <div className="c4-ml-state c4-ml-training-progress" role="status">
    <div className="c4-ml-progress-heading">
      <span className="c4-ml-spinner" />
      <div>
        <h4>Training candidate model</h4>
        <p>
          {trainingProgress?.message ?? "Starting training job..."}
        </p>
      </div>
    </div>

    <ol className="c4-ml-progress-steps">
      {TRAINING_STAGES.map((stage, index) => {
        const currentIndex = TRAINING_STAGES.findIndex(
          (item) => item.key === trainingProgress?.stage,
        );
        const activeIndex = currentIndex < 0 ? 0 : currentIndex;
        const isComplete = index < activeIndex;
        const isActive = index === activeIndex;

        return (
          <li
            key={stage.key}
            className={
              isComplete
                ? "is-complete"
                : isActive
                  ? "is-active"
                  : "is-pending"
            }
          >
            <span className="c4-ml-progress-marker">
              {isComplete ? "✓" : index + 1}
            </span>
            <span>{stage.label}</span>
            {isActive && (
              <span className="c4-ml-progress-current">Current</span>
            )}
          </li>
        );
      })}
    </ol>
  </div>
)}


            {trainingError && (
              <div className="c4-ml-csv-findings is-error" role="alert">
                <h5>Training error</h5>
                <p>{trainingError}</p>
              </div>
            )}

            {trainingPreview && (
              <div className="c4-ml-csv-results">
                <h4>Dataset preview</h4>
                <p>{trainingPreview.message}</p>

                <div className="c4-ml-csv-stats">
                  <div>
                    <span>Prepared rows</span>
                    <strong>{trainingPreview.rows}</strong>
                  </div>
                  <div>
                    <span>CSV columns</span>
                    <strong>{trainingPreview.columns}</strong>
                  </div>
                  <div>
                    <span>Unique devices</span>
                    <strong>{trainingPreview.unique_devices}</strong>
                  </div>
                  <div>
                    <span>Model features</span>
                    <strong>{trainingPreview.features.length}</strong>
                  </div>
                </div>

                <h4>Label distribution</h4>
                <ul>
                  {Object.entries(trainingPreview.class_distribution).map(
                    ([label, count]) => (
                      <li key={label}>
                        {label}: {count} rows
                      </li>
                    ),
                  )}
                </ul>

                <details>
                  <summary>Required training columns</summary>
                  <p>
                    The training CSV must contain the raw telemetry columns
                    required by the backend training pipeline, including
                    device identifiers, timestamps, sensor and network
                    measurements, and the target trust label.
                  </p>
                  <p>
                    Prepared feature names:{" "}
                    {trainingPreview.features.join(", ")}
                  </p>
                  {trainingPreview.preview.length > 0 && (
                    <pre
                      style={{
                        overflowX: "auto",
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {JSON.stringify(trainingPreview.preview, null, 2)}
                    </pre>
                  )}
                </details>

                <button
                  type="button"
                  className="c4-ml-button"
                  disabled={
                    trainingLoading ||
                    savingCandidate ||
                    !trainingFile
                  }
                  onClick={() => void trainUploadedFile()}
                >
                  Train Random Forest
                </button>
              </div>
            )}

            {trainingResult && (
              <div className="c4-ml-csv-results" aria-live="polite">
                <h4>Candidate evaluation results</h4>
                <p>{trainingResult.message}</p>

                <div className="c4-ml-csv-stats">
                  <div>
                    <span>Test accuracy</span>
                    <strong>
                      {formatPercentage(trainingResult.accuracy)}
                    </strong>
                  </div>
                  <div>
                    <span>Training rows</span>
                    <strong>{trainingResult.train_rows}</strong>
                  </div>
                  <div>
                    <span>Validation rows</span>
                    <strong>{trainingResult.validation_rows}</strong>
                  </div>
                  <div>
                    <span>Test rows</span>
                    <strong>{trainingResult.test_rows}</strong>
                  </div>
                  <div>
                    <span>Unique devices</span>
                    <strong>{trainingResult.unique_devices}</strong>
                  </div>
                </div>

                <h4>Classification report</h4>
                <pre style={{ overflowX: "auto", whiteSpace: "pre-wrap" }}>
                  {JSON.stringify(
                    trainingResult.classification_report,
                    null,
                    2,
                  )}
                </pre>

                <h4>Confusion matrix</h4>
                <div style={{ overflowX: "auto" }}>
                  <table className="c4-ml-table">
                    <thead>
                      <tr>
                        <th>Actual / Predicted</th>
                        {trainingResult.classes.map((label) => (
                          <th key={label}>{label}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {trainingResult.confusion_matrix.map((row, index) => (
                        <tr key={trainingResult.classes[index] ?? index}>
                          <th>
                            {trainingResult.classes[index] ?? `Class ${index}`}
                          </th>
                          {row.map((count, columnIndex) => (
                            <td key={columnIndex}>{count}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <h4>Feature importance</h4>
                {trainingResult.feature_importance.length > 0 ? (
                  <div style={{ overflowX: "auto" }}>
                    <table className="c4-ml-table">
                      <thead>
                        <tr>
                          {Object.keys(
                            trainingResult.feature_importance[0],
                          ).map((key) => (
                            <th key={key}>{humanizeKey(key)}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {trainingResult.feature_importance.map(
                          (item, index) => (
                            <tr key={index}>
                              {Object.entries(item).map(([key, value]) => (
                                <td key={key}>{String(value ?? "")}</td>
                              ))}
                            </tr>
                          ),
                        )}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p>No feature-importance results were returned.</p>
                )}

                <details>
                  <summary>Sample predictions</summary>
                  <pre style={{ overflowX: "auto", whiteSpace: "pre-wrap" }}>
                    {JSON.stringify(
                      trainingResult.sample_predictions,
                      null,
                      2,
                    )}
                  </pre>
                </details>

                <div
                  className={
                    trainingResult.runtime_compatibility_verified
                      ? "c4-ml-csv-findings"
                      : "c4-ml-csv-findings is-warning"
                  }
                >
                  <h4>
                    {trainingResult.runtime_compatibility_verified
                      ? "Runtime compatibility verified"
                      : "Evaluation-only candidate"}
                  </h4>
                  <p>
                    Runtime compatibility verified:{" "}
                    <strong>
                      {trainingResult.runtime_compatibility_verified
                        ? "Yes"
                        : "No"}
                    </strong>
                  </p>
                  {!trainingResult.runtime_compatibility_verified && (
                    <p>
                      This candidate has not been verified for runtime use.
                      Saving it does not authorize deployment or activation.
                    </p>
                  )}
                </div>

                <button
                  type="button"
                  className="c4-ml-button"
                  disabled={savingCandidate || Boolean(savedCandidate)}
                  onClick={() => void saveCandidate()}
                >
                  {savingCandidate
                    ? "Saving candidate…"
                    : savedCandidate
                      ? "Candidate Saved"
                      : "Save Evaluation Candidate"}
                </button>

                {savedCandidate && (
                  <div className="c4-ml-csv-findings" role="status">
                    <h4>
                      {savedCandidate.saved
                        ? "Candidate saved separately"
                        : "Candidate save status"}
                    </h4>
                    <p>{savedCandidate.message}</p>
                    <p>
                      File: <code>{savedCandidate.candidate_path}</code>
                    </p>
                    <p>
                      Runtime compatibility verified:{" "}
                      <strong>
                        {savedCandidate.runtime_compatibility_verified
                          ? "Yes"
                          : "No — evaluation only"}
                      </strong>
                    </p>
                    <p>
                      The candidate has not been activated and does not
                      replace the current runtime model.
                    </p>
                  </div>
                )}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
