/** @format */

const BASE = "/api/c3/research/forecasts";

export type ForecastRequest = {
  dataset_id: string;
  device_id: string;
  episode_id: string;
  forecast_origin: string;
};

export type ForecastPrediction = {
  prediction_id: string;
  dataset_id: string;
  device_id: string;
  episode_id: string;
  forecast_origin: string;
  forecast_type: string;
  horizon_minutes: number;
  target_timestamp: string;
  model_version_id: string;
  model_name: string;
  predicted_soil_moisture_pct: number;
  actual_soil_moisture_pct: number | null;
  absolute_error: number | null;
  input_window_start: string;
  input_window_end: string;
  sequence_length: number;
  source_origin: string;
  source_provenance_verified: boolean | number;
  receipt_time_basis: string;
  checkpoint_sha256: string;
  created_at: string;
};

export type GenerateForecastResponse = {
  status: string;
  forecast_type: "HISTORICAL_REPLAY";
  dataset_id: string;
  device_id: string;
  episode_id: string;
  forecast_origin: string;
  target_feature: "soil_moisture_pct";
  predictions: ForecastPrediction[];
  limitations: string[];
  warning: string;
};

export type ForecastHistoryResponse = {
  dataset_id: string;
  device_id: string;
  episode_id: string;
  total: number;
  predictions: ForecastPrediction[];
  warning: string;
};

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = `Forecast request failed (${response.status})`;

    try {
      const body = (await response.json()) as {
        detail?: string | { msg?: string }[];
      };

      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        message = body.detail
          .map((error) => error.msg || "Invalid request")
          .join("; ");
      }
    } catch {
      // Retain the HTTP status error.
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export const c3ForecastApi = {
  generate: (data: ForecastRequest, signal?: AbortSignal) =>
    request<GenerateForecastResponse>("/generate", {
      method: "POST",
      body: JSON.stringify(data),
      signal,
    }),

  history: (
    datasetId: string,
    deviceId: string,
    episodeId: string,
    limit = 100,
    signal?: AbortSignal,
  ) => {
    const params = new URLSearchParams({
      dataset_id: datasetId,
      device_id: deviceId,
      episode_id: episodeId,
      limit: String(limit),
    });

    return request<ForecastHistoryResponse>(
      `?${params.toString()}`,
      { signal },
    );
  },
};