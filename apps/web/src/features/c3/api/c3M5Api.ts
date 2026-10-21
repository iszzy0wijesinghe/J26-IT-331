/** @format */

export interface M5Prediction {
  horizon_minutes: number;
  target_timestamp: string;
  sensors: Record<string, number>;
}
export interface M5OperationalResponse {
  status: string;
  device_id: string;
  forecast_origin: string;
  sequence_length: number;
  model: string;
  model_version: string;
  sensor_features: string[];
  predictions: M5Prediction[];
  warning: string;
  data_source: string;
  risk_status: string;
  alert_status: string;
}
const BASE = "/api/c3/research/forecasts/operational";
async function parseResponse<T>(response: Response): Promise<T> {
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? (data as { detail: unknown }).detail
        : null;
    throw new Error(
      typeof detail === "string"
        ? detail
        : `API request failed (${response.status})`,
    );
  }
  return data as T;
}
export async function listGoldenDevices(): Promise<string[]> {
  const result = await parseResponse<{ devices: string[] }>(
    await fetch(`${BASE}/devices`),
  );
  return result.devices;
}
export async function generateOperationalM5(request: {
  device_id: string;
  forecast_origin: string;
  target_timestamp?: string;
}): Promise<M5OperationalResponse> {
  return parseResponse<M5OperationalResponse>(
    await fetch(`${BASE}/m5/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }),
  );
}

export async function getLatestGoldenObservation(
  deviceId: string,
): Promise<string> {
  const response = await fetch(
    `${BASE}/devices/${encodeURIComponent(deviceId)}/latest`,
  );
  const data = await parseResponse<{ latest_observation: string }>(response);
  return data.latest_observation;
}
