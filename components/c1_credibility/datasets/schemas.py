"""Column schema for the C1 credibility dataset (spec v1.1, section 13)."""
from __future__ import annotations
SCHEMA_VERSION = "c1_dataset_schema_v1"
DATASET_CODE = "C1_CREDIBILITY"
TARGET_COLUMN = "credibility_label"
METADATA_COLUMNS = ["record_id", "observation_id", "scenario_id", "zone_id", "device_id", "sensor_instance_id", "observed_at", "source_origin", "test_run_id", "dataset_version"]
SUPPORT_COLUMNS = ["label_source", "event_id", "calibration_version", "context_status", "ambiguous", "ambiguity_reason", "borderline_extreme", "train_eligible"]
SPLIT_COLUMNS = ["split", "split_temporal", "split_device"]
FEATURE_COLUMNS = [
    "mode", "dt_s", "value", "value_present", "delta_prev_pct_per_min", "obs_gap_steps",
    "baseline_mean", "baseline_std", "value_minus_baseline", "stuck_run_len",
    "rain_15m_mm", "rain_1h_mm", "rain_3h_mm", "steps_since_rain", "rainfall_regime",
    "n_neighbours_fresh", "neighbour_consensus_change", "target_minus_consensus",
    "neighbour_change_spread", "neighbour_rise_agree_frac", "device_voltage",
    "recent_read_failures", "history_obs",
]
DATASET_COLUMNS = METADATA_COLUMNS + [TARGET_COLUMN] + SUPPORT_COLUMNS + SPLIT_COLUMNS + FEATURE_COLUMNS
TRUTH_COLUMNS = ["record_id", "truth_label", "fault_id", "fault_type", "fault_effect", "event_id", "event_component", "true_value"]
EXCLUSION_COLUMNS = ["record_id", "scenario_id", "sensor_instance_id", "observed_at", "context_status", "split"]
FORBIDDEN_FEATURES = frozenset({
    "packet_id", "observation_id", "record_id", "scenario_id", "zone_id", "device_id", "sensor_instance_id",
    "device_serial", "row_number", "event_id", "credibility_label", "truth_label", "event_flag",
    "fault_flag", "fault_id", "fault_type", "fault_window", "fault_effect", "event_component",
    "true_value", "label_source", "ambiguous", "ambiguity_reason", "borderline_extreme",
    "train_eligible", "context_status", "c3_risk_probability", "future_mode", "c1_prediction",
    "split", "split_temporal", "split_device", "observed_at", "test_run_id", "dataset_version",
    "source_origin", "calibration_version",
})