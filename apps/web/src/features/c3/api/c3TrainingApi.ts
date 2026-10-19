/** C3 training endpoints. The backend's job/readiness JSON remains the source of truth. */
export type C3TrainingRecord = Record<string, unknown>;
const BASE = "/api/c3";
async function json<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init);
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try { const body = await response.json() as { detail?: unknown }; if (typeof body.detail === "string") detail = body.detail; } catch { /* non-JSON error */ }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}
export const c3TrainingApi = {
  readiness: (id: string, signal?: AbortSignal) => json<C3TrainingRecord>(`/training/readiness/${encodeURIComponent(id)}`, { signal }),
  jobs: (signal?: AbortSignal) => json<unknown>("/training/jobs?limit=50", { signal }),
  job: (id: string, signal?: AbortSignal) => json<C3TrainingRecord>(`/training/jobs/${encodeURIComponent(id)}`, { signal }),
  start: (datasetId: string) => json<C3TrainingRecord>(`/training/jobs/${encodeURIComponent(datasetId)}`, { method: "POST" }),
};

export type C3TrainingTelemetry = {
  job_id: string;
  status: string;
  current_stage: string;
  completed_tasks: number;
  total_tasks: number;
  progress_percent: number;
  progress_basis: string;
  current_epoch: number | null;
  max_epochs: number | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  events: Array<{ event_id?: number; timestamp?: string; level?: string; stage: string; message: string }>;
  metric_points: Array<{ stage: string; timestamp?: string; epoch: number | null; metrics: Record<string, number> }>;
};
export const c3TrainingMonitorApi = {
  telemetry: (id: string, signal?: AbortSignal) => json<C3TrainingTelemetry>(`/training/jobs/${encodeURIComponent(id)}/telemetry`, { signal }),
};

export type C3ExperimentAdmission = {
  dataset_id: string;
  temporal_ready: boolean;
  synthetic_experiment_authorized: boolean;
  field_approved: false;
  mode: "SYNTHETIC_RESEARCH";
  approval: Record<string, unknown>;
};
export const c3ExperimentApi = {
  admission: (id: string) => json<C3ExperimentAdmission>(`/training/experiments/${encodeURIComponent(id)}/admission`),
  prepare: (id: string) => json<Record<string, unknown>>(`/training/experiments/${encodeURIComponent(id)}/prepare`, { method: "POST" }),
  authorize: (id: string, researcher: string, reason: string) => json<Record<string, unknown>>(`/training/experiments/${encodeURIComponent(id)}/authorize`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ researcher, reason, confirm_synthetic: true, acknowledge_not_field_approved: true }),
  }),
  revoke: (id: string) => json<Record<string, unknown>>(`/training/experiments/${encodeURIComponent(id)}/revoke`, { method: "POST" }),
};
