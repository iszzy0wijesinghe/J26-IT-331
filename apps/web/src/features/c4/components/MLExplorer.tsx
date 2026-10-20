
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

interface PredictionRow {
  device_id: string;
  device_timestamp: string;
  predicted_label: string;
  [key: string]: string | number | undefined;
}

interface FeatureInput {
  tx_interval_s: number;
  rssi_dbm: number;
  snr_db: number;
  retry_count: number;
  battery_pct: number;
  battery_voltage_v: number;
  current_ma: number;
  reboot_count_24h: number;
  sensor_fault_flag: boolean;
  freshness_status: string;
}

interface PredictionResult {
  filename: string;
  rows: number;
  predictions: PredictionRow[];
  message: string;
}

const API_BASE = "http://127.0.0.1:8000";
const MAX_CSV_SIZE = 10 * 1024 * 1024;

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
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatPercentage(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "Unavailable";
  }

  return `${(value * 100).toFixed(2)}%`;
}

function formatMetric(value: unknown): string {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Number.isInteger(value) ? String(value) : value.toFixed(4);
  }

  if (typeof value === "string" || typeof value === "boolean") {
    return String(value);
  }

  return "Unavailable";
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

  const [predictionFile, setPredictionFile] = useState<File | null>(null);
const [predictionResult, setPredictionResult] =
  useState<PredictionResult | null>(null);
const [predictionError, setPredictionError] = useState("");
const [predictionLoading, setPredictionLoading] = useState(false);
const [trustedFilter, setTrustedFilter] = useState<boolean>(false);
const [sendingToDatabase, setSendingToDatabase] = useState(false);
const [databaseMessage, setDatabaseMessage] = useState("");
const [selectedPrediction, setSelectedPrediction] = useState<PredictionRow | null>(null);

// Manual prediction demo
const [manualFeatures, setManualFeatures] = useState<FeatureInput>({
  tx_interval_s: 300,
  rssi_dbm: -75,
  snr_db: 10,
  retry_count: 0,
  battery_pct: 85,
  battery_voltage_v: 3.7,
  current_ma: 15,
  reboot_count_24h: 0,
  sensor_fault_flag: false,
  freshness_status: "fresh",
});
const [manualPrediction, setManualPrediction] = useState<{ label: string; score: number; debugInfo?: any } | null>(null);
const [manualPredictionLoading, setManualPredictionLoading] = useState(false);
const [manualPredictionError, setManualPredictionError] = useState("");


async function predictUploadedFile(file: File) {
  setPredictionFile(file);
  setPredictionResult(null);
  setPredictionError("");

  if (!file.name.toLowerCase().endsWith(".csv")) {
    setPredictionError("Please select a CSV file.");
    return;
  }

  if (file.size === 0) {
    setPredictionError("The CSV file is empty.");
    return;
  }

  if (file.size > MAX_CSV_SIZE) {
    setPredictionError("The CSV file must be 10 MB or smaller.");
    return;
  }

  setPredictionLoading(true);

  try {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE}/api/c4/predict`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await readApiError(response));
    }

    const result: PredictionResult = await response.json();
    setPredictionResult(result);
  } catch (err) {
    setPredictionError(
      err instanceof Error ? err.message : "Prediction failed.",
    );
  } finally {
    setPredictionLoading(false);
  }
}

async function predictManualFeatures() {
  setManualPrediction(null);
  setManualPredictionError("");
  setManualPredictionLoading(true);

  try {
    const response = await fetch(`${API_BASE}/api/c4/predict-manual`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(manualFeatures),
    });

    if (!response.ok) {
      throw new Error(await readApiError(response));
    }

    const result = await response.json();
    setManualPrediction({
      label: result.predicted_label,
      score: result.behavioural_score,
      debugInfo: result.debug_info,
    });
  } catch (err) {
    setManualPredictionError(
      err instanceof Error ? err.message : "Manual prediction failed.",
    );
  } finally {
    setManualPredictionLoading(false);
  }
}

  useEffect(() => {
    const controller = new AbortController();

    async function loadModels() {
      try {
        const response = await fetch(`${API_BASE}/api/c4/models`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(
            await readApiError(response),
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
            Inspect saved model artifacts, review evaluation metrics, and train
            separate candidate models without replacing the active runtime model.
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
                <dd className="c4-ml-metadata-value">
                  {Object.keys(profile.training_metadata ?? {}).length
                    ? JSON.stringify(profile.training_metadata, null, 2)
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
              <>
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

                {profile.stored_metrics.precision_per_class && (
                  <>
                    <h4>Precision by class</h4>
                    <div className="c4-ml-table-wrapper">
                      <table className="c4-ml-table">
                        <thead>
                          <tr>
                            <th>Class</th>
                            <th>Precision</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(
                            profile.stored_metrics.precision_per_class,
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
            ) : (
              <div className="c4-ml-placeholder">
                <h4>No stored evaluation metrics</h4>
                <p>
                  This artifact does not provide stored evaluation metrics.
                  That does not mean the model has zero accuracy.
                </p>
              </div>
            )}
          </section>

          <section className="c4-ml-section">
            <div className="c4-ml-section-heading">
              <div>
                <h3>Actual feature schema</h3>
                <p>Inspect the feature names expected by the selected model.</p>
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

          <section className="c4-ml-section">
            <div className="c4-ml-section-heading">
              <div>
                <span className="c4-ml-eyebrow">QUICK ML DEMO</span>
                <h3>Test ML Model with Manual Input</h3>
                <p>
                  Enter feature values manually to see the ML model's prediction in real-time.
                  Perfect for demonstrating how the model works during presentations.
                </p>
              </div>
            </div>

            <div className="c4-ml-manual-input-grid">
              <div className="c4-ml-input-group">
                <label>TX Interval (s)</label>
                <input
                  type="number"
                  step="1"
                  value={manualFeatures.tx_interval_s}
                  onChange={(e) => setManualFeatures({...manualFeatures, tx_interval_s: parseFloat(e.target.value) || 0})}
                />
              </div>

              <div className="c4-ml-input-group">
                <label>RSSI (dBm) <span style={{color: manualFeatures.rssi_dbm > -30 ? "#dc2626" : "#64748b", fontSize: "10px"}}>{manualFeatures.rssi_dbm > -30 ? "(⚠ Unusual)" : ""}</span></label>
                <input
                  type="number"
                  step="0.1"
                  value={manualFeatures.rssi_dbm}
                  onChange={(e) => setManualFeatures({...manualFeatures, rssi_dbm: parseFloat(e.target.value) || 0})}
                  style={{borderColor: manualFeatures.rssi_dbm > -30 ? "#dc2626" : "#e2e8f0"}}
                />
                <span style={{fontSize: "10px", color: "#64748b"}}>Normal: -60 to -80 dBm</span>
              </div>

              <div className="c4-ml-input-group">
                <label>SNR (dB)</label>
                <input
                  type="number"
                  step="0.1"
                  value={manualFeatures.snr_db}
                  onChange={(e) => setManualFeatures({...manualFeatures, snr_db: parseFloat(e.target.value) || 0})}
                />
              </div>

              <div className="c4-ml-input-group">
                <label>Retry Count</label>
                <input
                  type="number"
                  step="1"
                  value={manualFeatures.retry_count}
                  onChange={(e) => setManualFeatures({...manualFeatures, retry_count: parseInt(e.target.value) || 0})}
                />
              </div>

              <div className="c4-ml-input-group">
                <label>Battery (%)</label>
                <input
                  type="number"
                  step="1"
                  min="0"
                  max="100"
                  value={manualFeatures.battery_pct}
                  onChange={(e) => setManualFeatures({...manualFeatures, battery_pct: parseFloat(e.target.value) || 0})}
                />
              </div>

              <div className="c4-ml-input-group">
                <label>Battery Voltage (V)</label>
                <input
                  type="number"
                  step="0.1"
                  value={manualFeatures.battery_voltage_v}
                  onChange={(e) => setManualFeatures({...manualFeatures, battery_voltage_v: parseFloat(e.target.value) || 0})}
                />
              </div>

              <div className="c4-ml-input-group">
                <label>Current (mA)</label>
                <input
                  type="number"
                  step="0.1"
                  value={manualFeatures.current_ma}
                  onChange={(e) => setManualFeatures({...manualFeatures, current_ma: parseFloat(e.target.value) || 0})}
                />
              </div>

              <div className="c4-ml-input-group">
                <label>Reboot Count (24h)</label>
                <input
                  type="number"
                  step="1"
                  value={manualFeatures.reboot_count_24h}
                  onChange={(e) => setManualFeatures({...manualFeatures, reboot_count_24h: parseInt(e.target.value) || 0})}
                />
              </div>

              <div className="c4-ml-input-group">
                <label>Sensor Fault</label>
                <select
                  value={manualFeatures.sensor_fault_flag ? "true" : "false"}
                  onChange={(e) => setManualFeatures({...manualFeatures, sensor_fault_flag: e.target.value === "true"})}
                >
                  <option value="false">No</option>
                  <option value="true">Yes</option>
                </select>
              </div>

              <div className="c4-ml-input-group">
                <label>Freshness Status</label>
                <select
                  value={manualFeatures.freshness_status}
                  onChange={(e) => setManualFeatures({...manualFeatures, freshness_status: e.target.value})}
                >
                  <option value="fresh">Fresh</option>
                  <option value="delayed">Delayed</option>
                  <option value="stale">Stale</option>
                </select>
              </div>
            </div>

            <button
              type="button"
              className="c4-ml-button"
              onClick={predictManualFeatures}
              disabled={manualPredictionLoading}
              style={{ marginTop: "16px" }}
            >
              {manualPredictionLoading ? "Predicting..." : "Run ML Prediction"}
            </button>

            {manualPredictionError && (
              <div className="c4-ml-state c4-ml-state-error" role="alert" style={{ marginTop: "16px" }}>
                <p>{manualPredictionError}</p>
              </div>
            )}

            {manualPrediction && (
              <div className="c4-ml-manual-result" style={{ marginTop: "20px", padding: "20px", background: manualPrediction.label === "TRUSTED" ? "#f0fdf4" : "#fef2f2", border: `2px solid ${manualPrediction.label === "TRUSTED" ? "#22c55e" : "#dc2626"}`, borderRadius: "8px" }}>
                <h4 style={{ margin: "0 0 12px 0", color: manualPrediction.label === "TRUSTED" ? "#166534" : "#991b1b" }}>ML Model Prediction Result</h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "16px" }}>
                  <div>
                    <span style={{ display: "block", fontSize: "12px", color: "#64748b", textTransform: "uppercase", fontWeight: "bold" }}>Predicted Label</span>
                    <strong style={{ fontSize: "24px", color: manualPrediction.label === "TRUSTED" ? "#16a34a" : "#dc2626" }}>
                      {manualPrediction.label}
                    </strong>
                  </div>
                  <div>
                    <span style={{ display: "block", fontSize: "12px", color: "#64748b", textTransform: "uppercase", fontWeight: "bold" }}>Behavioral Score</span>
                    <strong style={{ fontSize: "24px", color: manualPrediction.label === "TRUSTED" ? "#16a34a" : "#dc2626" }}>
                      {manualPrediction.score.toFixed(4)}
                    </strong>
                  </div>
                </div>
                <p style={{ margin: "12px 0 0 0", fontSize: "13px", color: "#475569" }}>
                  {manualPrediction.label === "TRUSTED"
                    ? "✓ The ML model predicts this packet is from a trusted device with normal behavior."
                    : "⚠ The ML model predicts this packet shows suspicious or anomalous behavior."}
                </p>
                {manualPrediction.label !== "TRUSTED" && (
                  <div style={{ marginTop: "12px", padding: "12px", background: "#fff7ed", border: "1px solid #fed7aa", borderRadius: "6px", fontSize: "12px", color: "#9a3412" }}>
                    <strong>Why Untrusted?</strong>
                    <ul style={{ margin: "8px 0 0 0", paddingLeft: "20px" }}>
                      <li>RSSI of {manualFeatures.rssi_dbm} dBm is {manualFeatures.rssi_dbm > -30 ? "extremely high" : "unusual"} (normal: -60 to -80 dBm)</li>
                      <li>Check if your RSSI value is realistic</li>
                      <li>Try: RSSI = -75, SNR = 10, Battery = 85% for TRUSTED</li>
                    </ul>
                    {manualPrediction.debugInfo && (
                      <details style={{ marginTop: "8px" }}>
                        <summary style={{ cursor: "pointer", fontWeight: "bold" }}>Debug Info</summary>
                        <pre style={{ marginTop: "8px", padding: "8px", background: "#fff", border: "1px solid #fed7aa", borderRadius: "4px", fontSize: "11px", overflow: "auto" }}>
                          {JSON.stringify(manualPrediction.debugInfo, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                )}
              </div>
            )}
          </section>

<section className="c4-ml-section c4-ml-csv-panel">
  <div className="c4-ml-csv-heading">
    <div>
      <span className="c4-ml-eyebrow">EXISTING RUNTIME MODEL</span>
      <h3>Predict Trust Class</h3>
      <p>
        Upload unlabeled telemetry and predict its trust class using the
        existing C4 Random Forest model. No training is performed.
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
      {predictionFile?.name ?? "Choose an unlabeled telemetry CSV"}
    </strong>
    <span>
      {predictionFile
        ? formatBytes(predictionFile.size)
        : "CSV without a trust_label column, up to 10 MB"}
    </span>
    <input
      type="file"
      accept=".csv,text/csv"
      aria-label="Choose an unlabeled CSV for prediction"
      disabled={predictionLoading}
      onChange={(event) => {
        const file = event.target.files?.[0] ?? null;
        if (file) void predictUploadedFile(file);
        event.currentTarget.value = "";
      }}
    />
  </label>

  <p className="c4-ml-csv-model">
    The file must contain the raw telemetry columns required by C4,
    excluding trust_label. ML predictions do not replace cryptographic
    verification or device identity checks.
  </p>

  {predictionLoading && (
    <div className="c4-ml-state" role="status">
      <span className="c4-ml-spinner" />
      Predicting trust classes using the existing model...
    </div>
  )}

  {predictionError && (
    <div className="c4-ml-csv-findings is-error" role="alert">
      <h5>Prediction error</h5>
      <p>{predictionError}</p>
    </div>
  )}

  {predictionResult && (
    <div className="c4-ml-csv-results">
      <h4>Prediction results</h4>
      <p>{predictionResult.message}</p>

      <div className="c4-ml-csv-stats">
        <div>
          <span>Rows predicted</span>
          <strong>{predictionResult.rows}</strong>
        </div>
        <div>
          <span>Input file</span>
          <strong>{predictionResult.filename}</strong>
        </div>
      </div>

      <div style={{ margin: "16px 0" }}>
        <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <input
            type="checkbox"
            checked={trustedFilter}
            onChange={(e) => setTrustedFilter(e.target.checked)}
          />
          <span>Show only TRUSTED predictions</span>
        </label>
      </div>

      {predictionResult.predictions.length > 0 && (
        <>
          <div className="c4-ml-table-wrapper">
            <table className="c4-ml-table">
              <thead>
                <tr>
                  <th>View JSON</th>
                  {Object.keys(predictionResult.predictions[0]).map(
                    (column) => (
                      <th key={column}>{humanizeKey(column)}</th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {predictionResult.predictions
                  .filter((row) => !trustedFilter || row.predicted_label?.toUpperCase() === "TRUSTED")
                  .map((row, index) => (
                  <tr
                    key={`${row.device_id}-${index}`}
                    className={selectedPrediction === row ? "c4-ml-table-row-selected" : ""}
                  >
                    <td>
                      <button
                        type="button"
                        className="c4-ml-json-button"
                        onClick={() => setSelectedPrediction(row)}
                      >
                        View
                      </button>
                    </td>
                    {Object.keys(predictionResult.predictions[0]).map(
                      (column) => (
                        <td key={column}>
                          {row[column] === undefined
                            ? "—"
                            : String(row[column])}
                        </td>
                      ),
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {selectedPrediction && (
            <div className="c4-ml-json-panel">
              <div className="c4-ml-json-panel-header">
                <h4>Prediction Details</h4>
                <button
                  type="button"
                  className="c4-ml-button"
                  onClick={() => setSelectedPrediction(null)}
                >
                  Close
                </button>
              </div>
              <pre className="c4-ml-json-content">
                {JSON.stringify(selectedPrediction, null, 2)}
              </pre>
            </div>
          )}

          <div style={{ display: "flex", gap: "12px", marginTop: "16px" }}>
            <button
              type="button"
              className="c4-ml-button"
              onClick={() => {
                const columns = Object.keys(
                  predictionResult.predictions[0],
                );

                const escapeCsv = (value: unknown) =>
                  `"${String(value ?? "").replaceAll('"', '""')}"`;

                const csv = [
                  columns.map(escapeCsv).join(","),
                  ...predictionResult.predictions.map((row) =>
                    columns
                      .map((column) => escapeCsv(row[column]))
                      .join(","),
                  ),
                ].join("\r\n");

                const url = URL.createObjectURL(
                  new Blob([csv], { type: "text/csv;charset=utf-8;" }),
                );

                const anchor = document.createElement("a");
                anchor.href = url;
                anchor.download = "c4_trust_predictions.csv";
                anchor.click();
                URL.revokeObjectURL(url);
              }}
            >
              Download predictions CSV
            </button>

            <button
              type="button"
              className="c4-ml-button"
              disabled={sendingToDatabase}
              onClick={async () => {
                setSendingToDatabase(true);
                setDatabaseMessage("");

                try {
                  const trustedPredictions = predictionResult.predictions.filter(
                    (row) => row.predicted_label?.toUpperCase() === "TRUSTED"
                  );

                  if (trustedPredictions.length === 0) {
                    setDatabaseMessage("No TRUSTED predictions to send to database.");
                    setSendingToDatabase(false);
                    return;
                  }

                  const response = await fetch(`${API_BASE}/api/c4/persist-trusted`, {
                    method: "POST",
                    headers: {
                      "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                      predictions: trustedPredictions,
                      filename: predictionResult.filename,
                    }),
                  });

                  if (!response.ok) {
                    throw new Error(await readApiError(response));
                  }

                  const result = await response.json();
                  setDatabaseMessage(
                    `Successfully sent ${trustedPredictions.length} TRUSTED packets to database. ${result.message}`
                  );
                } catch (err) {
                  if (err instanceof Error) {
                    // Try to parse the error detail from the response
                    const errorDetail = err.message;
                    setDatabaseMessage(
                      `Error sending to database: ${errorDetail}`
                    );
                  } else {
                    setDatabaseMessage(
                      `Error sending to database: Unknown error`
                    );
                  }
                } finally {
                  setSendingToDatabase(false);
                }
              }}
            >
              {sendingToDatabase ? "Sending..." : "Send TRUSTED to Database"}
            </button>
          </div>

          {databaseMessage && (
            <div style={{ marginTop: "12px", padding: "12px", background: "#f0f9ff", border: "1px solid #bae6fd", borderRadius: "4px" }}>
              {databaseMessage}
            </div>
          )}
        </>
      )}
    </div>
  )}
</section>
        </>
      )}
    </main>
  );
}
