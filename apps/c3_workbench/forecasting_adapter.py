"""GeoNex C3 forecasting feature adapter.

Converts Golden Database historical observations into the exact
feature representations used during model training.

Research safeguards:
- Reuses the existing Golden training sequence builder.
- Does not include observations after the forecast origin.
- Does not cross dataset, device, or episode boundaries.
- Does not fabricate original sensor receipt timestamps.
- Preserves Golden CSV provenance limitations.
- Does not load models or generate predictions.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from apps.c3_workbench.forecasting_reader import (
    load_historical_sequence,
    parse_timestamp,
)

from apps.c3_workbench.golden_training_adapter import (
    build_sequence,
)

from components.c3_forecasting.features.tabular_features import (
    extract_tabular_features,
)

from components.c3_forecasting.preprocessing.gru_dataset import (
    extract_gru_sequence,
)

from components.c3_forecasting.preprocessing.m4_features import (
    extract_m4_sequence,
)


class ForecastingAdapterError(ValueError):
    """Raised when forecasting inputs are invalid."""


def _validate_array(
    name: str,
    values: np.ndarray,
    expected_features: int,
) -> None:
    """Validate numerical model inputs."""

    if values.ndim != 2:
        raise ForecastingAdapterError(
            f"{name} must be a two-dimensional array."
        )

    if values.shape[1] != expected_features:
        raise ForecastingAdapterError(
            f"{name} expected {expected_features} features, "
            f"received {values.shape[1]}."
        )

    if not np.isfinite(values).all():
        raise ForecastingAdapterError(
            f"{name} contains non-finite values."
        )


def prepare_forecasting_inputs(
    *,
    dataset_id: str,
    device_id: str,
    episode_id: str,
    forecast_origin: str,
    max_sequence_length: int = 32,
) -> dict[str, Any]:
    """Prepare model-compatible inputs for a forecast origin."""

    history = load_historical_sequence(
        dataset_id=dataset_id,
        device_id=device_id,
        episode_id=episode_id,
        forecast_origin=forecast_origin,
        max_sequence_length=max_sequence_length,
    )

    origin_dt = parse_timestamp(
        history["forecast_origin"]
    )

    observations = history["observations"]

    # Additional identity checks protect against accidental
    # cross-device or cross-episode inference.
    for observation in observations:
        if observation["dataset_id"] != dataset_id:
            raise ForecastingAdapterError(
                "Cross-dataset observation detected."
            )

        if observation["device_id"] != device_id:
            raise ForecastingAdapterError(
                "Cross-device observation detected."
            )

        if observation["episode_id"] != episode_id:
            raise ForecastingAdapterError(
                "Cross-episode observation detected."
            )

        if parse_timestamp(
            observation["timestamp"]
        ) > origin_dt:
            raise ForecastingAdapterError(
                "Future observation detected."
            )

    # IMPORTANT:
    # Use the exact sequence builder used during training.
    sequence = build_sequence(
        observations,
        forecast_origin=origin_dt,
        dataset_id=dataset_id,
        episode_id=episode_id,
        device_id=device_id,
    )

    # M1 / M2: fixed-length tabular features.
    tabular_features = extract_tabular_features(
        sequence
    )

    tabular_feature_count = len(
        tabular_features
    )

    if tabular_feature_count != 79:
        raise ForecastingAdapterError(
            "Unexpected tabular feature count: "
            f"{tabular_feature_count}"
        )

    tabular_values = np.asarray(
        list(tabular_features.values()),
        dtype=np.float32,
    )

    if not np.isfinite(tabular_values).all():
        raise ForecastingAdapterError(
            "Tabular features contain non-finite values."
        )

    # M3: sensor values + validity masks.
    m3_features = extract_gru_sequence(
        sequence
    )

    _validate_array(
        "M3",
        m3_features,
        expected_features=14,
    )

    # M4-A: time-aware, without operating-mode encoding.
    m4_a_features = extract_m4_sequence(
        sequence,
        include_time=True,
        include_mode=False,
    )

    _validate_array(
        "M4-A",
        m4_a_features,
        expected_features=20,
    )

    # M4-B: mode-aware, without explicit time features.
    m4_b_features = extract_m4_sequence(
        sequence,
        include_time=False,
        include_mode=True,
    )

    _validate_array(
        "M4-B",
        m4_b_features,
        expected_features=20,
    )

    # M4-C: both elapsed-time and operating-mode features.
    m4_c_features = extract_m4_sequence(
        sequence,
        include_time=True,
        include_mode=True,
    )

    _validate_array(
        "M4-C",
        m4_c_features,
        expected_features=20,
    )

    return {
        "dataset_id": dataset_id,
        "device_id": device_id,
        "episode_id": episode_id,
        "forecast_origin": history["forecast_origin"],
        "forecast_type": "HISTORICAL_REPLAY",
        "source_origin": "GOLDEN_CSV",
        "source_provenance_verified": False,
        "receipt_time_basis": (
            "ASSUMED_EQUAL_TO_OBSERVATION_TIME"
        ),
        "sequence_length": history["sequence_length"],
        "window_start": history["window_start"],
        "window_end": history["window_end"],
        "temporal_sequence": sequence,
        "tabular_features": tabular_features,
        "tabular_feature_names": list(
            tabular_features.keys()
        ),
        "tabular_values": tabular_values,
        "m3_features": m3_features,
        "m4_a_features": m4_a_features,
        "m4_b_features": m4_b_features,
        "m4_c_features": m4_c_features,
    }