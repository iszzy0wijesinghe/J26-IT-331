"""Audit C3 V2 supervised examples against original synthetic telemetry."""

from collections import Counter, defaultdict
from datetime import datetime

from components.c3_forecasting.v2_dataset_reader import (
    group_v2_by_episode_device,
)
from components.c3_forecasting.v2_target_builder import (
    build_v2_fixed_horizon_examples,
)

DATASET_DIR = "data/synthetic/c3_v2"


def main() -> None:
    print("Loading original synthetic telemetry...")

    groups = group_v2_by_episode_device(DATASET_DIR)

    packet_lookup = {}
    episode_splits = defaultdict(set)

    for (episode_id, device_id), records in groups.items():
        for record in records:
            key = (episode_id, device_id, record["packet_id"])

            if key in packet_lookup:
                raise AssertionError(f"Duplicate packet key: {key}")

            packet_lookup[key] = record
            episode_splits[episode_id].add(record["split"])

    print("Building supervised training examples...")

    examples = build_v2_fixed_horizon_examples(DATASET_DIR)

    violations = []
    counts = Counter()
    mode_counts = Counter()
    deviations = defaultdict(list)

    for example in examples:
        key = (
            example.episode_id,
            example.device_id,
            example.target_packet_id,
        )

        original = packet_lookup.get(key)

        if original is None:
            violations.append(f"Missing target packet: {key}")
            continue

        feature = example.target_feature

        # Verify the target is a genuine observed measurement.
        if not original["masks"][feature]:
            violations.append(f"Unobserved target: {key}")

        if original["imputed_flags"][feature]:
            violations.append(f"Imputed target: {key}")

        if original["corrected_flags"][feature]:
            violations.append(f"Corrected target: {key}")

        if original["features"][feature] != example.target_value:
            violations.append(f"Target value mismatch: {key}")

        observed_at = datetime.fromisoformat(original["observed_at"])

        if observed_at != example.target_observed_at:
            violations.append(f"Target timestamp mismatch: {key}")

        if observed_at <= example.forecast_origin:
            violations.append(f"Target is not in the future: {key}")

        # Verify the entire input sequence is as-of safe.
        for step in example.input_sequence.steps:
            received_at = datetime.fromisoformat(
                step.provenance["received_at"]
            )

            if step.time > example.forecast_origin:
                violations.append(
                    f"Future observed input: {key}"
                )

            if received_at > example.forecast_origin:
                violations.append(
                    f"Future received input: {key}"
                )

            if step.provenance["device_id"] != example.device_id:
                violations.append(
                    f"Cross-device input: {key}"
                )

            mode_counts[
                (
                    example.split,
                    example.requested_horizon_minutes,
                    step.operating_mode.value,
                )
            ] += 1

        counts[
            (
                example.split,
                example.requested_horizon_minutes,
            )
        ] += 1

        deviations[example.requested_horizon_minutes].append(
            abs(
                example.actual_horizon_seconds
                - example.requested_horizon_minutes * 60
            )
        )

    # Verify episode-disjoint partitions.
    for episode_id, splits in episode_splits.items():
        if len(splits) != 1:
            violations.append(
                f"Episode {episode_id} appears in multiple splits"
            )

    print("\n=== C3 V2 DATASET INTEGRITY AUDIT ===")
    print(f"Original telemetry packets: {len(packet_lookup):,}")
    print(f"Supervised examples: {len(examples):,}")

    print("\nExamples by split and horizon:")

    for split in ("train", "validation", "test"):
        for horizon in (15, 30, 60):
            print(
                f"  {split:10s} | {horizon:2d} min | "
                f"{counts[(split, horizon)]:,}"
            )

    print("\nAbsolute horizon deviations:")

    for horizon in (15, 30, 60):
        values = deviations[horizon]

        if values:
            print(
                f"  {horizon:2d} min | "
                f"Mean: {sum(values) / len(values):.2f} sec | "
                f"Max: {max(values):.2f} sec"
            )

    print("\nOperating-mode distribution (historical steps):")

    for mode in (
        "DEEP_SLEEP",
        "IDLE",
        "RISK",
        "WARNING",
        "EMERGENCY",
    ):
        total = sum(
            count
            for (_, _, current_mode), count in mode_counts.items()
            if current_mode == mode
        )

        print(f"  {mode:12s}: {total:,}")

    print(f"\nIntegrity violations: {len(violations)}")

    if violations:
        for violation in violations[:20]:
            print(f"  FAIL: {violation}")

        raise SystemExit(1)

    print("\nPASS: Dataset integrity checks completed.")


if __name__ == "__main__":
    main()