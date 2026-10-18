/** @format */

export type Ablation = "A" | "B" | "C";
export type Horizon = 15 | 30 | 60;
export type ModelAvailability = {
  model: string;
  horizon_minutes: number;
  available: boolean;
};
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
export type TemporalSequence = {
  steps: TemporalStep[];
  [key: string]: unknown;
};
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
// ============================================================
// C3 Dataset Manager types
// ============================================================

export type C3DatasetSplitStatistics = {
  examples: number;
  episodes: number;
  devices: number;
  horizon_counts: Record<string, number>;
  mode_step_counts: Record<string, number>;
  sequence_length_distribution: Record<string, number>;
  missing_readings: number;
};

export type C3DatasetValidation = {
  status: string;
  dataset_version: string;
  export_version: string;
  source_origin: string;
  target_feature: string;
  forecast_horizons_minutes: number[];
  splits: {
    train: C3DatasetSplitStatistics;
    validation: C3DatasetSplitStatistics;
  };
  episode_disjoint: boolean;
  held_out_test_accessed: boolean;
  warning: string;
};

export type C3RegisteredDataset = {
  dataset_id: string;
  status: string;
  held_out_test_included: boolean;
  [key: string]: unknown;
};

export type C3DatasetListResponse = {
  datasets: C3RegisteredDataset[];
  total: number;
};

export type C3DatasetUploadResponse = {
  message: string;
  dataset: C3RegisteredDataset;
};

// ============================================================
// C3 CSV Dataset Validation
// ============================================================

export type C3CSVValidationIssue = {
  severity: "ERROR" | "WARNING";
  code: string;
  message: string;
  row: number | null;
  column: string | null;
};

export type C3CSVValidationResult = {
  status: "VALIDATED" | "FAILED";
  schema_version: string;
  filename: string;

  total_rows: number;
  valid_rows: number;
  invalid_rows: number;

  missing_values: Record<string, number>;
  operating_modes: Record<string, number>;

  devices: number;
  episodes: number;

  timestamp_start: string | null;
  timestamp_end: string | null;

  issues: C3CSVValidationIssue[];

  error_count: number;
  warning_count: number;
};

export type C3CSVValidationResponse = {
  message: string;
  validation: C3CSVValidationResult;
  registered: boolean;
  training_started: boolean;
};

export type C3GoldenDataset = {
  dataset_id: string;
  filename: string;
  file_hash: string;
  uploaded_at: string;
  total_rows: number;
  device_count: number;
  episode_count: number;
  quality_status: string;
  pipeline_status: string;
  source_type: "CSV";
};

export type C3GoldenDatasetDetails = C3GoldenDataset & {
  stored_observations: number;
  validation: C3CSVValidationResult;
};

export type C3GoldenDatasetListResponse = {
  datasets: C3GoldenDataset[];
  total: number;
};

export type C3CSVUploadResponse = C3CSVValidationResponse & {
  dataset?: {
    dataset_id: string;
    status: string;
    already_registered: boolean;
    observations: number;
    quality_status?: string;
    training_started: boolean;
  };
};

export type C3DatabaseBackup = {
  backup_id: string;
  filename: string;
  created_at: string;
  size_bytes: number;
  sha256: string;
  status: string;
  database_filename: string;
};

export type C3DatabaseBackupListResponse = {
  backups: C3DatabaseBackup[];
  total: number;
};

export type C3DatabaseBackupCreateResponse = {
  message: string;
  backup: C3DatabaseBackup;
};

const BASE = "/api/c3";
async function requestJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${BASE}${path}`, options);
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* response may not be JSON */
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}
export const c3Api = {
  health: (signal?: AbortSignal) =>
    requestJson<C3Health>("/health", { signal }),
  models: (signal?: AbortSignal) =>
    requestJson<ModelsResponse>("/models", { signal }),
  examples: (horizon: Horizon, offset = 0, limit = 10, signal?: AbortSignal) =>
    requestJson<ExamplesResponse>(
      `/examples?horizon_minutes=${horizon}&offset=${offset}&limit=${limit}`,
      { signal },
    ),
  predict: (
    ablation: Ablation,
    horizon: Horizon,
    temporal_sequence: TemporalSequence,
    signal?: AbortSignal,
  ) =>
    requestJson<ForecastResponse>("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ablation,
        horizon_minutes: horizon,
        temporal_sequence,
      }),
      signal,
    }),
};

// ============================================================
// C3 Dataset Manager API
// ============================================================

export const c3DatasetApi = {
  /**
   * Retrieve all registered datasets.
   */
  list: (signal?: AbortSignal) =>
    requestJson<C3DatasetListResponse>("/datasets", {
      signal,
    }),

  /**
   * Retrieve one registered dataset.
   */
  get: (datasetId: string, signal?: AbortSignal) =>
    requestJson<C3RegisteredDataset>(
      `/datasets/${encodeURIComponent(datasetId)}`,
      {
        signal,
      },
    ),

  /**
   * Upload a dataset ZIP for validation and registration.
   *
   * Uploading does not initiate model training.
   */
  upload: (file: File, signal?: AbortSignal) => {
    const formData = new FormData();

    formData.append("file", file);

    return requestJson<C3DatasetUploadResponse>("/datasets/upload", {
      method: "POST",
      body: formData,
      signal,
    });
  },
};

export const c3CSVApi = {
  validate: (
    file: File,
    signal?: AbortSignal,
  ): Promise<C3CSVValidationResponse> => {
    const formData = new FormData();
    formData.append("file", file);

    return requestJson<C3CSVValidationResponse>("/datasets/csv/validate", {
      method: "POST",
      body: formData,
      signal,
    });
  },

  upload: (file: File, signal?: AbortSignal): Promise<C3CSVUploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);

    return requestJson<C3CSVUploadResponse>("/datasets/csv/upload", {
      method: "POST",
      body: formData,
      signal,
    });
  },
};

export const c3GoldenApi = {
  list: (signal?: AbortSignal) =>
    requestJson<C3GoldenDatasetListResponse>("/datasets/golden", { signal }),

  get: (datasetId: string, signal?: AbortSignal) =>
    requestJson<C3GoldenDatasetDetails>(
      `/datasets/golden/${encodeURIComponent(datasetId)}`,
      { signal },
    ),
};

export const c3DatabaseApi = {
  listBackups: (signal?: AbortSignal) =>
    requestJson<C3DatabaseBackupListResponse>(
      "/database/backups",

      { signal },
    ),

  createBackup: (signal?: AbortSignal) =>
    requestJson<C3DatabaseBackupCreateResponse>(
      "/database/backups",

      {
        method: "POST",

        signal,
      },
    ),

  verifyBackup: (
    backupId: string,

    signal?: AbortSignal,
  ) =>
    requestJson<C3DatabaseBackup>(
      `/database/backups/${encodeURIComponent(backupId)}`,
      { signal },
    ),
  downloadBackup: (backupId: string) =>
    `${BASE}/database/backups/${encodeURIComponent(backupId)}/download`,
};

// ============================================================
// C3 Golden Database Explorer
// ============================================================

export type C3GoldenObservation = {
  observation_id: number;
  dataset_id: string;
  device_id: string;
  episode_id: string;
  timestamp: string;
  operating_mode: string;

  soil_moisture_pct: number;
  rainfall_proxy_counts: number;
  tilt_deg: number;
  vibration_g: number;
  fsr_adc: number;
  air_temperature_c: number;
  humidity_pct: number;

  created_at: string;
};

export type C3ObservationSortBy =
  | "timestamp"
  | "observation_id"
  | "device_id"
  | "episode_id"
  | "operating_mode"
  | "soil_moisture_pct"
  | "rainfall_proxy_counts"
  | "tilt_deg"
  | "vibration_g"
  | "fsr_adc"
  | "air_temperature_c"
  | "humidity_pct";

export type C3ObservationQuery = {
  dataset_id?: string;
  device_id?: string;
  episode_id?: string;
  operating_mode?: string;
  timestamp_from?: string;
  timestamp_to?: string;
  search?: string;
  sort_by?: C3ObservationSortBy;
  sort_order?: "asc" | "desc";
  limit?: number;
  offset?: number;
};

export type C3ObservationListResponse = {
  observations: C3GoldenObservation[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  sort_by: string;
  sort_order: string;
};

export type C3ObservationFiltersResponse = {
  datasets: {
    dataset_id: string;
    filename: string;
    total_rows: number;
  }[];
  devices: string[];
  episodes: string[];
  operating_modes: string[];
};

function buildObservationQuery(
  query: C3ObservationQuery,
): string {
  const parameters = new URLSearchParams();

  for (const [key, value] of Object.entries(query)) {
    if (
      value !== undefined &&
      value !== null &&
      value !== ""
    ) {
      parameters.set(key, String(value));
    }
  }

  return parameters.toString();
}

export const c3ExplorerApi = {
  list: (
    query: C3ObservationQuery,
    signal?: AbortSignal,
  ) =>
    requestJson<C3ObservationListResponse>(
      `/database/observations?${buildObservationQuery(query)}`,
      { signal },
    ),

  filters: (
    datasetId?: string,
    signal?: AbortSignal,
  ) => {
    const parameters = new URLSearchParams();

    if (datasetId) {
      parameters.set("dataset_id", datasetId);
    }

    const suffix = parameters.toString();

    return requestJson<C3ObservationFiltersResponse>(
      `/database/observations/filters${
        suffix ? `?${suffix}` : ""
      }`,
      { signal },
    );
  },

  exportUrl: (query: C3ObservationQuery) =>
    `${BASE}/database/observations/export?${buildObservationQuery(
      query,
    )}`,
};