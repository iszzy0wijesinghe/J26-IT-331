
"""Build time-aware C3 sequences from scheduled simulation telemetry.

This module prepares initial PP1 engineering sequences. It does not
replace the future multi-pipe Golden Timeline builder.
"""

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime

from shared.contracts.c3_forecasting import (
    C3TemporalSequence,
    C3TemporalStep,
)
from shared.contracts.telemetry import TelemetryPacket
from shared.simulation.scheduled_telemetry import ScheduledTelemetry

FeatureValues = Mapping[str, float | int | None]
FeatureExtractor = Callable[[TelemetryPacket], FeatureValues]

BUILDER_VERSION = "c3-pipe-sequence-v1"


def build_pipe_temporal_sequence(
    items: Sequence[ScheduledTelemetry],
    *,
    zone_id: str,
    device_id: str,
    forecast_origin: datetime,
    feature_extractor: FeatureExtractor,
    feature_schema_version: str = "c3-features-v1",
    max_steps: int | None = None,
) -> C3TemporalSequence:
    """Build a chronological, as-of-safe sequence for one pipe.

    Only measurements observed AND received by forecast_origin qualify.

    Masks use True = feature present and False = feature missing.
    The first retained step uses delta_t_seconds=0.0 as a placeholder,
    with a flag identifying its unavailable preceding interval.

    Sensor feature extraction is explicitly supplied by the caller
    until the shared telemetry-to-feature mapping is finalized.
    """

    if forecast_origin.utcoffset() is None:
        raise ValueError("forecast_origin must be timezone-aware")

    if not zone_id or not device_id:
        raise ValueError("zone_id and device_id must not be empty")

    if max_steps is not None and max_steps <= 0:
        raise ValueError("max_steps must be positive")

    eligible: list[ScheduledTelemetry] = []

    for item in items:
        packet = item.packet

        if packet.zone_id != zone_id or packet.device_id != device_id:
            continue

        if (
            packet.observed_at.utcoffset() is None
            or packet.received_at.utcoffset() is None
        ):
            raise ValueError("Packet timestamps must be timezone-aware")

        if (
            packet.observed_at <= forecast_origin
            and packet.received_at <= forecast_origin
        ):
            eligible.append(item)

    eligible.sort(
        key=lambda item: (
            item.packet.observed_at,
            item.packet.sequence_no,
        )
    )

    if max_steps is not None:
        eligible = eligible[-max_steps:]

    if not eligible:
        raise ValueError(
            "No observations available for this pipe at forecast_origin"
        )

    steps: list[C3TemporalStep] = []
    previous_time: datetime | None = None

    for item in eligible:
        packet = item.packet

        first_step = previous_time is None

        elapsed = (
            0.0
            if first_step
            else (packet.observed_at - previous_time).total_seconds()
        )

        features = dict(feature_extractor(packet))

        if not features:
            raise ValueError(
                "feature_extractor must return at least one feature"
            )

        masks = {
            name: value is not None
            for name, value in features.items()
        }

        # At this stage, features describe the current packet only.
        # We do not impute stale readings from other devices.
        ages = {
            name: 0.0 if value is not None else None
            for name, value in features.items()
        }

        steps.append(
            C3TemporalStep(
                time=packet.observed_at,
                delta_t_seconds=elapsed,
                operating_mode=item.operating_mode,
                features=features,
                masks=masks,
                ages_seconds=ages,
                quality={
                    "source": "SIMULATED",
                    "first_interval_unknown": first_step,
                },
                provenance={
                    "device_id": packet.device_id,
                    "sequence_no": packet.sequence_no,
                    "received_at": packet.received_at.isoformat(),
                },
            )
        )

        previous_time = packet.observed_at

    return C3TemporalSequence(
        schema_version="1.0",
        zone_id=zone_id,
        forecast_origin=forecast_origin,
        feature_schema_version=feature_schema_version,
        builder_version=BUILDER_VERSION,
        steps=steps,
    )
