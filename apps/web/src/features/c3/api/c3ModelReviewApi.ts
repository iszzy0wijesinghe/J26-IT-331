/** @format */

export type ModelCandidate = {
  model_version_id: string;
  job_id: string;
  dataset_id: string;
  model_name: string;
  horizon_minutes: number;
  validation_mae: number | null;
  validation_rmse: number | null;
  status: string;
  created_at: string;
};
export type ActiveAssignment = {
  horizon_minutes: number;
  model_version_id: string;
  model_name: string;
  dataset_id: string;
  job_id: string;
  validation_mae: number | null;
  validation_rmse: number | null;
  activated_at: string;
  activated_by: string;
  activation_reason: string;
};
async function read<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api/c3/research/models/${path}`, { signal });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      /* retain HTTP status */
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
export const c3ModelReviewApi = {
  candidates: (signal?: AbortSignal) =>
    read<{ candidates: ModelCandidate[]; total: number }>("candidates", signal),
  active: (signal?: AbortSignal) =>
    read<{ assignments: ActiveAssignment[] }>("active", signal),
  history: (signal?: AbortSignal) =>
    read<{ events: Record<string, unknown>[] }>("history", signal),
};
