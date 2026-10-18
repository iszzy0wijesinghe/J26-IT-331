"""Build leakage-safe fixed-horizon regression examples from C3 V2 data.

Targets must be genuinely observed future measurements.
This module does not create landslide-risk labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from components.c3_forecasting.data.v2_dataset_reader import (
    group_v2_by_episode_device,
)
from components.c3_forecasting.data.v2_temporal_adapter import (
    build_v2_temporal_sequence,
)
from shared.contracts.c3_forecasting import C3TemporalSequence


@dataclass(frozen=True)
class C3V2TrainingExample:
    """One historical sequence and a future observed regression target."""

    episode_id: str
    device_id: str
    zone_id: str
    split: str

    forecast_origin: datetime
    input_sequence: C3TemporalSequence

    target_feature: str
    target_value: float
    target_observed_at: datetime
    target_packet_id: str

    requested_horizon_minutes: int
    actual_horizon_seconds: float

    def to_record(self) -> dict[str, Any]:
        """Convert the training example to a JSON-compatible record."""

        return {
            "dataset_version": "c3-fixed-horizon-v2",
            "episode_id": self.episode_id,
            "device_id": self.device_id,
            "zone_id": self.zone_id,
            "split": self.split,
            "forecast_origin": self.forecast_origin.isoformat(),
            "input_sequence": self.input_sequence.model_dump(
                mode="json"
            ),
            "target": {
                "feature": self.target_feature,
                "value": self.target_value,
                "observed_at": self.target_observed_at.isoformat(),
                "packet_id": self.target_packet_id,
                "requested_horizon_minutes": (
                    self.requested_horizon_minutes
                ),
                "actual_horizon_seconds": (
                    self.actual_horizon_seconds
                ),
            },
        }


def build_v2_fixed_horizon_examples(
    dataset_dir: str,
    *,
    horizons_minutes: tuple[int, ...] = (15, 30, 60),
    tolerance_minutes: float = 2.0,
    target_feature: str = "soil_moisture_pct",
    min_history_steps: int = 3,
    max_history_steps: int = 32,
) -> list[C3V2TrainingExample]:
    """Build supervised examples using observed future sensor values."""

    if not horizons_minutes or any(h <= 0 for h in horizons_minutes):
        raise ValueError("Forecast horizons must be positive")

    if tolerance_minutes < 0:
        raise ValueError("Tolerance cannot be negative")

    if min_history_steps < 1:
        raise ValueError("min_history_steps must be positive")

    if max_history_steps < min_history_steps:
        raise ValueError(
            "max_history_steps must be >= min_history_steps"
        )

    groups = group_v2_by_episode_device(dataset_dir)

    examples: list[C3V2TrainingExample] = []

    tolerance = timedelta(minutes=tolerance_minutes)

    for (episode_id, device_id), records in sorted(groups.items()):
        parsed = [
            (
                datetime.fromisoformat(record["observed_at"]),
                datetime.fromisoformat(record["received_at"]),
                record,
            )
            for record in records
        ]

        for _, origin_received, origin_record in parsed:
            # Only records actually available at the forecast origin.
            history = [
                record
                for observed, received, record in parsed
                if observed <= origin_received
                and received <= origin_received
            ]

            if len(history) < min_history_steps:
                continue

            sequence = build_v2_temporal_sequence(
                history,
                forecast_origin=origin_received,
                max_steps=max_history_steps,
            )

            if len(sequence.steps) < min_history_steps:
                continue

            for horizon in horizons_minutes:
                requested_time = origin_received + timedelta(
                    minutes=horizon
                )

                candidates = []

                for observed, _, record in parsed:
                    if observed <= origin_received:
                        continue

                    deviation = abs(observed - requested_time)

                    if deviation > tolerance:
                        continue

                    if not record["masks"].get(target_feature, False):
                        continue

                    if record["imputed_flags"].get(target_feature, True):
                        continue

                    if record["corrected_flags"].get(target_feature, False):
                        continue

                    candidates.append(
                        (deviation, observed, record)
                    )

                if not candidates:
                    continue

                candidates.sort(
                    key=lambda item: (
                        item[0],
                        item[1],
                        item[2]["packet_id"],
                    )
                )

                _, target_observed_at, target_record = candidates[0]

                examples.append(
                    C3V2TrainingExample(
                        episode_id=episode_id,
                        device_id=device_id,
                        zone_id=origin_record["zone_id"],
                        split=origin_record["split"],
                        forecast_origin=origin_received,
                        input_sequence=sequence,
                        target_feature=target_feature,
                        target_value=float(
                            target_record["features"][target_feature]
                        ),
                        target_observed_at=target_observed_at,
                        target_packet_id=target_record["packet_id"],
                        requested_horizon_minutes=horizon,
                        actual_horizon_seconds=(
                            target_observed_at - origin_received
                        ).total_seconds(),
                    )
                )

    return examples