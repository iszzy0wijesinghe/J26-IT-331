import type { FeatureKey, Observation, RecentPrediction } from "./types";

export interface FieldMeta {
  key: FeatureKey;
  label: string;
  unit?: string;
  group: "Reading" | "Baseline" | "Rainfall" | "Neighbours" | "Device";
  step: number;
  min?: number;
  max?: number;
}

export const FIELD_GROUPS = ["Reading", "Baseline", "Rainfall", "Neighbours", "Device"] as const;

// min / max match the validation in apps/c1_api/app/schemas.py
export const FIELDS: FieldMeta[] = [
  { key: "value", label: "Soil moisture", unit: "%", group: "Reading", step: 0.1 },
  { key: "dt_s", label: "Sample interval", unit: "s", group: "Reading", step: 1, min: 1 },
  { key: "delta_prev_pct_per_min", label: "Change vs previous", unit: "%/min", group: "Reading", step: 0.01 },

  { key: "baseline_mean", label: "Baseline mean", unit: "%", group: "Baseline", step: 0.1 },
  { key: "baseline_std", label: "Baseline std", unit: "%", group: "Baseline", step: 0.01, min: 0 },
  { key: "value_minus_baseline", label: "Value minus baseline", unit: "%", group: "Baseline", step: 0.1 },
  { key: "stuck_run_len", label: "Stuck run length", unit: "steps", group: "Baseline", step: 1, min: 0 },

  { key: "rain_15m_mm", label: "Rain 15 min", unit: "mm", group: "Rainfall", step: 0.1, min: 0 },
  { key: "rain_1h_mm", label: "Rain 1 h", unit: "mm", group: "Rainfall", step: 0.1, min: 0 },
  { key: "rain_3h_mm", label: "Rain 3 h", unit: "mm", group: "Rainfall", step: 0.1, min: 0 },
  { key: "steps_since_rain", label: "Steps since rain", unit: "steps", group: "Rainfall", step: 1, min: 0 },

  { key: "n_neighbours_fresh", label: "Fresh neighbours", unit: "count", group: "Neighbours", step: 1, min: 0 },
  { key: "neighbour_consensus_change", label: "Neighbour consensus change", unit: "%", group: "Neighbours", step: 0.1 },
  { key: "target_minus_consensus", label: "Target minus consensus", unit: "%", group: "Neighbours", step: 0.1 },
  { key: "neighbour_change_spread", label: "Neighbour spread", unit: "%", group: "Neighbours", step: 0.01, min: 0 },
  { key: "neighbour_rise_agree_frac", label: "Neighbours rising", unit: "0 to 1", group: "Neighbours", step: 0.05, min: 0, max: 1 },

  { key: "device_voltage", label: "Battery voltage", unit: "V", group: "Device", step: 0.01, min: 0 },
  { key: "history_obs", label: "History observations", unit: "obs", group: "Device", step: 1, min: 0 },
];

export interface Preset {
  id: string;
  name: string;
  hint: string;
  values: Observation;
}

const QUIET_RAIN = { rain_15m_mm: 0, rain_1h_mm: 0, rain_3h_mm: 0, steps_since_rain: 120 };

// Simulated readings, for trying the dashboard. The model decides the label, the hint
// only describes the situation.
export const PRESETS: Preset[] = [
  {
    id: "stable",
    name: "Stable baseline",
    hint: "Quiet soil, no rain, neighbours steady",
    values: {
      dt_s: 300, value: 32.8, delta_prev_pct_per_min: 0.02, baseline_mean: 32.7, baseline_std: 0.35,
      value_minus_baseline: 0.1, stuck_run_len: 1, ...QUIET_RAIN, n_neighbours_fresh: 3,
      neighbour_consensus_change: 0.05, target_minus_consensus: 0.03, neighbour_change_spread: 0.12,
      neighbour_rise_agree_frac: 0, device_voltage: 3.95, history_obs: 24,
    },
  },
  {
    id: "spike",
    name: "Sudden spike",
    hint: "Large jump, no rain, neighbours unmoved",
    values: {
      dt_s: 300, value: 61.0, delta_prev_pct_per_min: 9.5, baseline_mean: 32.7, baseline_std: 0.4,
      value_minus_baseline: 28.3, stuck_run_len: 1, ...QUIET_RAIN, n_neighbours_fresh: 3,
      neighbour_consensus_change: 0.04, target_minus_consensus: 28.2, neighbour_change_spread: 0.1,
      neighbour_rise_agree_frac: 0, device_voltage: 3.9, history_obs: 24,
    },
  },
  {
    id: "rain-rise",
    name: "Rain-driven rise",
    hint: "Heavy rain, neighbours rise together",
    values: {
      dt_s: 300, value: 38.9, delta_prev_pct_per_min: 0.6, baseline_mean: 32.7, baseline_std: 0.5,
      value_minus_baseline: 6.2, stuck_run_len: 1, rain_15m_mm: 2.4, rain_1h_mm: 7.8, rain_3h_mm: 14.2,
      steps_since_rain: 0, n_neighbours_fresh: 3, neighbour_consensus_change: 5.8, target_minus_consensus: 0.4,
      neighbour_change_spread: 0.9, neighbour_rise_agree_frac: 1, device_voltage: 3.9, history_obs: 24,
    },
  },
  {
    id: "stuck",
    name: "Stuck sensor",
    hint: "Flat line while neighbours react to rain",
    values: {
      dt_s: 300, value: 32.8, delta_prev_pct_per_min: 0, baseline_mean: 32.8, baseline_std: 0,
      value_minus_baseline: 0, stuck_run_len: 48, rain_15m_mm: 1.8, rain_1h_mm: 5.2, rain_3h_mm: 9.6,
      steps_since_rain: 0, n_neighbours_fresh: 3, neighbour_consensus_change: 4.9, target_minus_consensus: -4.9,
      neighbour_change_spread: 0.7, neighbour_rise_agree_frac: 1, device_voltage: 3.85, history_obs: 24,
    },
  },
];

// Shown in the table only while the API is unreachable, always flagged as mock.
export const MOCK_RECENT: RecentPrediction[] = [
  ["CLEAN", 0.97, 32.8, 0.0, 3], ["VALID_EVENT", 0.91, 38.9, 7.8, 3], ["CLEAN", 0.95, 33.1, 0.0, 3],
  ["ANOMALY", 0.88, 61.0, 0.0, 3], ["CLEAN", 0.96, 32.6, 0.2, 2], ["VALID_EVENT", 0.84, 36.4, 5.1, 3],
].map(([label, confidence, value, rain, n], i) => ({
  id: `mock-${i}`,
  timestamp: new Date(Date.now() - i * 5 * 60_000).toISOString(),
  label: label as string,
  confidence: confidence as number,
  probabilities: {},
  input: { value: value as number, rain_1h_mm: rain as number, n_neighbours_fresh: n as number },
  source: "mock" as const,
}));
