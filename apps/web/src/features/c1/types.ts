// Types shared by the C1 page, hook and API client. They mirror apps/c1_api/app/schemas.py.

export const FEATURE_KEYS = [
  "dt_s", "value", "delta_prev_pct_per_min", "baseline_mean",
  "baseline_std", "value_minus_baseline", "stuck_run_len",
  "rain_15m_mm", "rain_1h_mm", "rain_3h_mm", "steps_since_rain",
  "n_neighbours_fresh", "neighbour_consensus_change",
  "target_minus_consensus", "neighbour_change_spread",
  "neighbour_rise_agree_frac", "device_voltage", "history_obs",
] as const;

export type FeatureKey = (typeof FEATURE_KEYS)[number];

/** One observation, null = missing value (the model handles it). */
export type Observation = Record<FeatureKey, number | null>;

/** Raw text of every input box, so a field can be empty. */
export type FormValues = Record<FeatureKey, string>;

export type C1Label = "CLEAN" | "ANOMALY" | "VALID_EVENT";

export interface PredictionResult {
  label: string;
  confidence: number;
  probabilities: Record<string, number>;
  missing_features: string[];
}

export interface PredictResponse {
  model_version: string;
  count: number;
  latency_ms: number;
  results: PredictionResult[];
}

export interface HealthResponse {
  status: "ok" | "degraded";
  model_loaded: boolean;
  model_version: string | null;
  uptime_s: number;
  error: string | null;
}

export interface ModelInfo {
  name: string;
  version: string;
  trained_at: string | null;
  format: string;
  objective: string | null;
  n_features: number;
  features: string[];
  classes: string[];
  class_order_source: string;
  class_order_verified: boolean;
}

export interface Metrics {
  available: boolean;
  macro_f1: number | null;
  anomaly_recall: number | null;
  valid_event_recall: number | null;
  evaluated_on: string | null;
}

export interface RecentPrediction {
  id: string;
  timestamp: string;
  label: string;
  confidence: number;
  probabilities: Record<string, number>;
  input: Partial<Record<FeatureKey, number | null>>;
  source: "api" | "mock";
}

export type Connection = "checking" | "online" | "degraded" | "offline";
