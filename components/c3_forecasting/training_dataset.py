
"""Build supervised C3 engineering datasets from scheduled telemetry.

PP1 baseline task: predict the next observed soil-moisture value.
This is NOT a calibrated landslide-risk dataset.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from components.c3_forecasting.feature_extractor import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    extract_simulator_sensor_features,
)
from components.c3_forecasting.sequence_builder import (
    build_pipe_temporal_sequence,
)
from shared.contracts.c3_forecasting import C3TemporalSequence
from shared.simulation.scheduled_telemetry import ScheduledTelemetry

DATASET_VERSION = "c3-next-observation-v1"
DEFAULT_TARGET_FEATURE = "soil_moisture_pct"


@dataclass(frozen=True)
class C3TrainingExample:
    """One historical sequence and its future regression target."""

    zone_id: str
    device_id: str
    forecast_origin: datetime
    input_sequence: C3TemporalSequence
    target_feature: str
    target_value: float
    target_observed_at: datetime
    target_packet_id: str
    horizon_seconds: float

    def to_record(self) -> dict[str, object]:
        """Return a JSON-serializable training example."""
        return {
            "dataset_version": DATASET_VERSION,
            "zone_id": self.zone_id,
            "device_id": self.device_id,
            "forecast_origin": self.forecast_origin.isoformat(),
            "input_sequence": self.input_sequence.model_dump(mode="json"),
            "target": {
                "feature": self.target_feature,
                "value": self.target_value,
                "observed_at": self.target_observed_at.isoformat(),
                "packet_id": self.target_packet_id,
                "horizon_seconds": self.horizon_seconds,
            },
        }


@dataclass(frozen=True)
class C3DatasetSplit:
    """Device-disjoint experimental train/validation/test partitions."""

    train: tuple[C3TrainingExample, ...]
    validation: tuple[C3TrainingExample, ...]
    test: tuple[C3TrainingExample, ...]


def build_next_observation_examples(
    items: Sequence[ScheduledTelemetry],
    *,
    min_history_steps: int = 3,
    max_history_steps: int = 8,
    target_feature: str = DEFAULT_TARGET_FEATURE,
) -> list[C3TrainingExample]:
    """Create supervised examples without future features leaking into X.

    A prediction is made at the source packet's received_at time.
    Its label is the normalized target value in the next observation,
    but only when that observation occurs after the forecast origin.

    The horizon is measured and recorded; it is NOT fixed.
    """

    if min_history_steps < 1:
        raise ValueError("min_history_steps must be positive")

    if max_history_steps < min_history_steps:
        raise ValueError(
            "max_history_steps must be >= min_history_steps"
        )

    if target_feature not in FEATURE_NAMES:
        raise ValueError(
            f"Unknown target feature: {target_feature}"
        )

    grouped: dict[
        tuple[str, str],
        list[ScheduledTelemetry],
    ] = defaultdict(list)

    for item in items:
        packet = item.packet
        grouped[(packet.zone_id, packet.device_id)].append(item)

    results: list[C3TrainingExample] = []

    for (zone_id, device_id), records in sorted(grouped.items()):
        records.sort(
            key=lambda item: (
                item.packet.observed_at,
                item.packet.sequence_no
                if item.packet.sequence_no is not None
                else -1,
                item.packet.packet_id,
            )
        )

        seen_packet_ids: set[str] = set()
        for item in records:
            packet_id = item.packet.packet_id
            if packet_id in seen_packet_ids:
                raise ValueError(
                    f"Duplicate packet_id in C3 dataset: {packet_id}"
                )
            seen_packet_ids.add(packet_id)

        for index in range(min_history_steps - 1, len(records) - 1):
            origin_packet = records[index].packet
            future_packet = records[index + 1].packet

            forecast_origin = origin_packet.received_at

            # The label must represent a later observation, not
            # a reading already observed when the forecast was made.
            if future_packet.observed_at <= forecast_origin:
                continue

            future_features = extract_simulator_sensor_features(
                future_packet
            )

            target_value = future_features[target_feature]
            if target_value is None:
                continue

            sequence = build_pipe_temporal_sequence(
                records[: index + 1],
                zone_id=zone_id,
                device_id=device_id,
                forecast_origin=forecast_origin,
                feature_extractor=extract_simulator_sensor_features,
                feature_schema_version=FEATURE_SCHEMA_VERSION,
                max_steps=max_history_steps,
            )

            if len(sequence.steps) < min_history_steps:
                continue

            horizon_seconds = (
                future_packet.observed_at - forecast_origin
            ).total_seconds()

            results.append(
                C3TrainingExample(
                    zone_id=zone_id,
                    device_id=device_id,
                    forecast_origin=forecast_origin,
                    input_sequence=sequence,
                    target_feature=target_feature,
                    target_value=target_value,
                    target_observed_at=future_packet.observed_at,
                    target_packet_id=future_packet.packet_id,
                    horizon_seconds=horizon_seconds,
                )
            )

    return results


def split_examples_by_device(
    examples: Sequence[C3TrainingExample],
    *,
    seed: int = 20261016,
) -> C3DatasetSplit:
    """Create reproducible device-disjoint partitions.

    This is an engineering split for the small six-pipe simulator.
    It is not sufficient to prove generalization to real landslide sites.
    """

    device_keys = sorted(
        {(item.zone_id, item.device_id) for item in examples}
    )

    if len(device_keys) < 3:
        raise ValueError(
            "At least three distinct devices are required for splitting"
        )

    def stable_rank(key: tuple[str, str]) -> bytes:
        identity = f"{seed}:{key[0]}:{key[1]}"
        return sha256(identity.encode("utf-8")).digest()

    ordered = sorted(device_keys, key=stable_rank)

    # Reserve one device each for validation and testing.
    training_devices = set(ordered[:-2])
    validation_device = ordered[-2]
    testing_device = ordered[-1]

    return C3DatasetSplit(
        train=tuple(
            item
            for item in examples
            if (item.zone_id, item.device_id) in training_devices
        ),
        validation=tuple(
            item
            for item in examples
            if (item.zone_id, item.device_id) == validation_device
        ),
        test=tuple(
            item
            for item in examples
            if (item.zone_id, item.device_id) == testing_device
        ),
    )
