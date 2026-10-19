/**
 * C3 training endpoints. The backend's job/readiness JSON remains the source of truth.
 *
 * @format
 */

export type C3TrainingRecord = Record<string, unknown>;
const BASE = "/api/c3";
async function json<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init);
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}
export const c3TrainingApi = {
  readiness: (id: string, signal?: AbortSignal) =>
    json<C3TrainingRecord>(`/training/readiness/${encodeURIComponent(id)}`, {
      signal,
    }),
  jobs: (signal?: AbortSignal) =>
    json<unknown>("/training/jobs?limit=50", { signal }),
  job: (id: string, signal?: AbortSignal) =>
    json<C3TrainingRecord>(`/training/jobs/${encodeURIComponent(id)}`, {
      signal,
    }),
  start: (datasetId: string) =>
    json<C3TrainingRecord>(`/training/jobs/${encodeURIComponent(datasetId)}`, {
      method: "POST",
    }),
};
