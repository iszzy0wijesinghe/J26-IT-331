"""Build research-aligned C3 temporal sequences from V2 synthetic telemetry.

This adapter preserves variable sampling intervals, operating modes,
observation masks, measurement ages, and synthetic provenance.

It does not perform forecasting, imputation, or risk classification.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from components.c3_forecasting.v2_dataset_reader import (
    validate_v2_record,
)
from shared.contracts.c3_forecasting import (
    C3TemporalSequence,
    C3TemporalStep,
)

FEATURE_SCHEMA_VERSION = "c3-synthetic-features-v2"
BUILDER_VERSION = "c3-v2-temporal-adapter-v1"


def _parse_time(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value)

    if timestamp.utcoffset() is None:
        raise ValueError("Timestamp must be timezone-aware")

    return timestamp


def build_v2_temporal_sequence(
    records: Sequence[Mapping[str, Any]],
    *,
    forecast_origin: datetime,
    max_steps: int = 32,
) -> C3TemporalSequence:
    """Build an as-of-safe temporal sequence for one episode and device."""

    if forecast_origin.utcoffset() is None:
        raise ValueError("forecast_origin must be timezone-aware")

    if max_steps <= 0:
        raise ValueError("max_steps must be positive")

    if not records:
        raise ValueError("At least one telemetry record is required")

    eligible = []

    expected_identity = None
    seen_packet_ids = set()

    for raw_record in records:
        record = dict(raw_record)

        validate_v2_record(record)

        identity = (
            record["scenario_id"],
            record["device_id"],
            record["zone_id"],
            record["split"],
        )

        if expected_identity is None:
            expected_identity = identity
        elif identity != expected_identity:
            raise ValueError(
                "Cannot mix episodes, devices, zones, or dataset splits"
            )

        packet_id = record["packet_id"]

        if packet_id in seen_packet_ids:
            raise ValueError(f"Duplicate packet ID: {packet_id}")

        seen_packet_ids.add(packet_id)

        observed_at = _parse_time(record["observed_at"])
        received_at = _parse_time(record["received_at"])

        if (
            observed_at <= forecast_origin
            and received_at <= forecast_origin
        ):
            eligible.append(
                (observed_at, received_at, record)
            )

    eligible.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2]["packet_id"],
        )
    )

    eligible = eligible[-max_steps:]

    if not eligible:
        raise ValueError(
            "No telemetry available at forecast_origin"
        )

    steps = []
    previous_time = None

    for observed_at, received_at, record in eligible:
        first_step = previous_time is None

        delta_t_seconds = (
            0.0
            if first_step
            else (observed_at - previous_time).total_seconds()
        )

        features = {
            name: float(value)
            for name, value in record["features"].items()
        }

        masks = dict(record["masks"])

        ages_seconds = {
            name: (
                float(age)
                if age >= 0
                else None
            )
            for name, age in record["ages_seconds"].items()
        }

        step = C3TemporalStep(
            time=observed_at,
            delta_t_seconds=delta_t_seconds,
            operating_mode=record["effective_mode"],
            features=features,
            masks=masks,
            ages_seconds=ages_seconds,
            quality={
                "source_origin": record["source_origin"],
                "imputed_flags": dict(record["imputed_flags"]),
                "corrected_flags": dict(record["corrected_flags"]),
                "imputation_methods": dict(
                    record["imputation_methods"]
                ),
                "first_interval_unknown": first_step,
            },
            provenance={
                "scenario_id": record["scenario_id"],
                "scenario_family": record["scenario_family"],
                "split": record["split"],
                "device_id": record["device_id"],
                "packet_id": record["packet_id"],
                "received_at": received_at.isoformat(),
                "scheduled_mode": record["scheduled_mode"],
                "mode_change_reason": record["mode_change_reason"],
            },
        )

        steps.append(step)

        previous_time = observed_at

    assert expected_identity is not None

    return C3TemporalSequence(
        schema_version="1.0",
        zone_id=expected_identity[2],
        forecast_origin=forecast_origin,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        builder_version=BUILDER_VERSION,
        steps=steps,
        test_run_id=expected_identity[0],
    )