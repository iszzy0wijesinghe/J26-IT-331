/** @format */

export type C3MonitoringMode =
  | "DEEP_SLEEP"
  | "IDLE"
  | "RISK"
  | "WARNING";

export type C3AdaptiveReplayRequest = {
  dataset_id: string;
  device_id: string;
  episode_id: string;
  start_index: number;
  observation_count: number;
};

export type C3AdaptiveDecision = {
  previous_mode: C3MonitoringMode | null;
  selected_mode: C3MonitoringMode;
  monitoring_interval_s: number;
  stable_evaluation_count: number;
  safety_override_applied: boolean;
  reasons: string[];
};

export type C3AdaptiveReplayStep = {
  dataset_id: string;
  device_id: string;
  episode_id: string;
  forecast_origin: string;
  forecast_type: string;
  research_status: string;
  current_sensor_values: Record<string, unknown>;
  observation_quality: Record<string, unknown>;
  forecasts: Array<Record<string, unknown>>;
  risk_assessment: Record<string, unknown>;
  adaptive_decision: C3AdaptiveDecision;
  limitations: string[];
};

export type C3EnergyEstimate = {
  duration_s: number;
  total_monitoring_cycles: number;
  baseline_energy_mj: number;
  monitoring_energy_mj: number;
  total_energy_mj: number;
  total_energy_wh: number;
  average_power_mw: number;
  monitoring_interval_s?: number;
};

export type C3AdaptiveEnergyReplay = C3EnergyEstimate & {
  segments: Array<Record<string, unknown>>;
};

export type C3AdaptiveReplayResponse = {
  dataset_id: string;
  device_id: string;
  episode_id: string;
  replay_type: "HISTORICAL_OPEN_LOOP_REPLAY";
  research_status: string;
  start_timestamp: string;
  end_timestamp: string;
  observation_count: number;
  decisions: C3AdaptiveReplayStep[];
  energy_evaluation: {
    adaptive: C3AdaptiveEnergyReplay;
    fixed_baselines: Array<{
      monitoring_interval_s: number;
      energy: C3EnergyEstimate;
    }>;
    saving_vs_fixed_5s_pct: number;
    assumptions: Record<string, unknown>;
  };
  limitations: string[];
};

async function postJson<T>(
  path: string,
  body: unknown,
): Promise<T> {
  const response = await fetch(`/api/c3${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;

    try {
      const payload: unknown = await response.json();

      if (
        typeof payload === "object" &&
        payload !== null &&
        "detail" in payload
      ) {
        const value = payload.detail;

        detail =
          typeof value === "string"
            ? value
            : JSON.stringify(value);
      }
    } catch {
      // Keep the HTTP status message if the response is not JSON.
    }

    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export const c3AdaptiveApi = {
  replay(
    request: C3AdaptiveReplayRequest,
  ): Promise<C3AdaptiveReplayResponse> {
    return postJson<C3AdaptiveReplayResponse>(
      "/research/adaptive/replay",
      request,
    );
  },
};
