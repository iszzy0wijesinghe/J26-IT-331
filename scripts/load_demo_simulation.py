"""Load a deterministic GeoNex demonstration simulation into PostgreSQL."""

from collections import Counter

from apps.ingestion.simulation_loader import load_simulated_telemetry
from database.session import create_database_engine, create_session_factory, session_scope
from shared.simulation.scheduled_telemetry import (
    ScheduledTelemetryConfig,
    generate_scheduled_demo_telemetry,
)


def main() -> None:
    """Generate, persist, and summarize a GeoNex simulation."""

    config = ScheduledTelemetryConfig(
        seed=2026101001,
    )

    items = generate_scheduled_demo_telemetry(config)

    print("\nGeoNex Demonstration Simulation")
    print("=" * 40)

    print(f"Simulation seed: {config.seed}")
    print(f"Generated packets: {len(items)}")

    device_counts = Counter(item.packet.device_id for item in items)

    print("\nPackets per device:")

    for device_id, count in sorted(device_counts.items()):
        print(f"  {device_id}: {count}")

    engine = create_database_engine()
    session_factory = create_session_factory(engine)

    try:
        with session_scope(session_factory) as session:
            result = load_simulated_telemetry(
                session=session,
                items=items,
            )

        print("\nDatabase Load Result")
        print("=" * 40)

        print(f"Status: {result.status.value}")
        print(f"Total packets: {result.total_packets}")
        print(f"Created packets: {result.created_packets}")
        print(f"Existing packets: {result.existing_packets}")
        print(f"Created observations: {result.created_observations}")

        print("\nDatabase transaction committed successfully.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()