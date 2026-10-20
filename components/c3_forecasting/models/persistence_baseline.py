"""Strict persistence forecasting baseline for GeoNex C3."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class PersistencePrediction:
    """Result of a persistence forecast."""

    prediction: float | None
    source_observed_at: datetime | None
    source_age_seconds: float | None
    unavailable_reason: str | None = None


def predict_persistence(
    sequence: Mapping[str, Any],
    *,
    target_feature: str = "soil_moisture_pct",
) -> PersistencePrediction:
    """Predict using the latest valid observed historical value.

    The input is the serialized C3TemporalSequence dictionary.

    This strict baseline rejects:
    - Missing observations
    - Imputed observations
    - Corrected observations

    It never uses future observations.
    """

    forecast_origin = datetime.fromisoformat(
        sequence["forecast_origin"]
    )

    steps = sequence["steps"]

    candidates = []

    for step in steps:
        observed_at = datetime.fromisoformat(step["time"])

        received_at = datetime.fromisoformat(
            step["provenance"]["received_at"]
        )

        # Enforce as-of causality.
        if observed_at > forecast_origin:
            continue

        if received_at > forecast_origin:
            continue

        if not step["masks"].get(target_feature, False):
            continue

        quality = step.get("quality", {})

        imputed_flags = quality.get("imputed_flags", {})
        corrected_flags = quality.get("corrected_flags", {})

        if imputed_flags.get(target_feature, False):
            continue

        if corrected_flags.get(target_feature, False):
            continue

        value = step["features"].get(target_feature)

        if value is None:
            continue

        candidates.append(
            (observed_at, received_at, float(value))
        )

    if not candidates:
        return PersistencePrediction(
            prediction=None,
            source_observed_at=None,
            source_age_seconds=None,
            unavailable_reason="NO_VALID_HISTORICAL_OBSERVATION",
        )

    observed_at, _, value = max(
        candidates,
        key=lambda item: (item[0], item[1]),
    )

    age_seconds = (
        forecast_origin - observed_at
    ).total_seconds()

    return PersistencePrediction(
        prediction=value,
        source_observed_at=observed_at,
        source_age_seconds=age_seconds,
    )