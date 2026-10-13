"""Run a deterministic GeoNex simulation through the demo-only C4 gate."""

from collections import Counter

from apps.ingestion.simulation_loader import (
    load_simulated_telemetry_with_c4,
)
from database.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)
from shared.simulation.c4_demo import (
    build_demo_c4_gate,
    prepare_and_sign_demo_packet,
)
from shared.simulation.scheduled_telemetry import (
    ScheduledTelemetryConfig,
    generate_scheduled_demo_telemetry,
)


def main() -> None:
    """Generate, validate, persist, and summarize demo telemetry."""

    config = ScheduledTelemetryConfig(seed=2026101301)
    items = generate_scheduled_demo_telemetry(config)

    print("\nGeoNex Demonstration Simulation")
    print("=" * 40)
    print("SECURITY MODE: DEMO ONLY — NOT PRODUCTION SECURITY")
    print(f"Simulation seed: {config.seed}")
    print(f"Generated packets: {len(items)}")

    device_counts = Counter(item.packet.device_id for item in items)

    print("\nPackets per device:")
    for device_id, count in sorted(device_counts.items()):
        print(f"  {device_id}: {count}")

    gate, credentials = build_demo_c4_gate()

    def prepare_and_sign(item):
        return prepare_and_sign_demo_packet(item, credentials)

    engine = create_database_engine()
    session_factory = create_session_factory(engine)

    try:
        with session_scope(session_factory) as session:
            result = load_simulated_telemetry_with_c4(
                session=session,
                items=items,
                gate=gate,
                prepare_and_sign=prepare_and_sign,
                now_provider=lambda packet: packet.observed_at,
            )

        print("\nC4-Gated Database Load Result")
        print("=" * 40)
        print(f"Status: {result.status.value}")
        print(f"Total packets: {result.total_packets}")
        print(f"C4-accepted packets: {result.accepted_packets}")
        print(f"Created packets: {result.created_packets}")
        print(f"Existing packets: {result.existing_packets}")
        print(f"Quarantined packets: {result.quarantined_packets}")
        print(f"Created observations: {result.created_observations}")

        print("\nDatabase transaction committed successfully.")
        print(
            "Note: simulated timestamps are used for this historical demo; "
            "this is not a real-time freshness test."
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
