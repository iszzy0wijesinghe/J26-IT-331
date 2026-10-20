import type {
  HealthResponse, Metrics, ModelInfo, Observation, PredictResponse, RecentPrediction,
} from "../types";

// set VITE_C1_API_URL in apps/web/.env.local to point somewhere else
export const C1_API_BASE: string = (
  (import.meta.env.VITE_C1_API_URL as string | undefined) ?? "http://127.0.0.1:8033"
).replace(/\/+$/, "");

export class ApiError extends Error {
  status: number | null;
  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** FastAPI errors come as {detail: "text"} or {detail: [{loc, msg}]}. */
async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) {
      return body.detail
        .map((d: { loc?: (string | number)[]; msg?: string }) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg ?? "invalid"}`)
        .join("; ");
    }
  } catch {
    /* not json */
  }
  return `Request failed (${res.status})`;
}

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = 8000): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${C1_API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
    });
    if (!res.ok) throw new ApiError(await readError(res), res.status);
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError("The C1 API did not answer in time.");
    }
    throw new ApiError(`Cannot reach the C1 API at ${C1_API_BASE}. Is it running?`);
  } finally {
    window.clearTimeout(timer);
  }
}

export const c1Api = {
  health: () => request<HealthResponse>("/health", {}, 4000),
  model: () => request<ModelInfo>("/models"),
  metrics: () => request<Metrics>("/metrics"),
  recent: (limit = 10) => request<RecentPrediction[]>(`/predictions/recent?limit=${limit}`),
  predict: (body: Observation | Observation[]) =>
    request<PredictResponse>("/predict", { method: "POST", body: JSON.stringify(body) }),
};
