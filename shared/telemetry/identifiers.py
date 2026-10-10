"""Deterministic identifiers for GeoNex telemetry observations."""

from hashlib import sha256


def make_observation_id(packet_id: str, measurement_index: int) -> str:
    """Generate a stable observation ID for a packet measurement.

    The packet ID and measurement position together identify the
    observation within the normalized telemetry packet.
    """
    if not packet_id:
        raise ValueError("packet_id must not be empty")

    if measurement_index < 0:
        raise ValueError("measurement_index must be nonnegative")

    identity = f"{len(packet_id)}:{packet_id}:{measurement_index}"

    digest = sha256(identity.encode("utf-8")).hexdigest()

    return f"obs_{digest}"