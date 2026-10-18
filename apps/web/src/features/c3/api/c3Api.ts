export type Ablation = 'A' | 'B' | 'C';
export type Horizon = 15 | 30 | 60;
export type ModelAvailability = { model: string; horizon_minutes: number; available: boolean };
export type C3Health = { status: string; component: string; scope: string };
export type ModelsResponse = { models: ModelAvailability[]; note: string };
export type TemporalStep = {
  features?: Record<string, number | null>;
  masks?: Record<string, number | boolean | null>;
  delta_t_seconds?: number | null;
  operating_mode?: string;
  time?: string;
  [key: string]: unknown;
};
export type TemporalSequence = { steps: TemporalStep[]; [key: string]: unknown };
export type ValidationExample = {
  id: string;
  episode_id: string | null;
  device_id: string | null;
  forecast_origin: unknown;
  target_observed_at: string | null;
  actual_horizon_seconds: number | null;
  actual_soil_moisture_percent: number;
  temporal_sequence: TemporalSequence;
};
export type ExamplesResponse = {
  dataset: string;
  horizon_minutes: Horizon;
  offset: number;
  limit: number;
  has_more: boolean;
  examples: ValidationExample[];
  warning: string;
};
export type ForecastResponse = {
  model: string;
  horizon_minutes: Horizon;
  forecast_soil_moisture_percent: number;
  warning: string;
};
const BASE = '/api/c3';
async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${path}`, options);
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === 'string') detail = body.detail;
    } catch { /* response may not be JSON */ }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}
export const c3Api = {
  health: (signal?: AbortSignal) => requestJson<C3Health>('/health', { signal }),
  models: (signal?: AbortSignal) => requestJson<ModelsResponse>('/models', { signal }),
  examples: (horizon: Horizon, offset = 0, limit = 10, signal?: AbortSignal) =>
    requestJson<ExamplesResponse>(`/examples?horizon_minutes=${horizon}&offset=${offset}&limit=${limit}`, { signal }),
  predict: (ablation: Ablation, horizon: Horizon, temporal_sequence: TemporalSequence, signal?: AbortSignal) =>
    requestJson<ForecastResponse>('/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ablation, horizon_minutes: horizon, temporal_sequence }),
      signal,
    }),
};
