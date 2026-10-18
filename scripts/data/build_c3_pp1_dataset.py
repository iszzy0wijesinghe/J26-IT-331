
"""Export a reproducible synthetic C3 PP1 training dataset.

Usage:
    python -m scripts.build_c3_pp1_dataset --output-dir data/processed/c3_pp1_run1

The command refuses to overwrite any existing output directory.
"""

import argparse
import json
from hashlib import sha256
from pathlib import Path

from components.c3_forecasting.data.training_dataset import (
    DATASET_VERSION,
    C3TrainingExample,
    build_next_observation_examples,
    split_examples_by_device,
)
from shared.simulation.scheduled_telemetry import (
    ScheduledTelemetryConfig,
    generate_scheduled_demo_telemetry,
)


def write_jsonl(
    path: Path,
    examples: tuple[C3TrainingExample, ...],
) -> dict[str, str | int]:
    """Write deterministic JSONL and return count/checksum metadata."""

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for example in examples:
            handle.write(
                json.dumps(
                    example.to_record(),
                    sort_keys=True,
                    allow_nan=False,
                )
                + "\n"
            )

    return {
        "filename": path.name,
        "count": len(examples),
        "sha256": sha256(path.read_bytes()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export C3 synthetic PP1 training examples"
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="New directory for dataset files; must not already exist",
    )

    parser.add_argument("--seed", type=int, default=20261016)

    args = parser.parse_args()

    output_dir: Path = args.output_dir

    if output_dir.exists():
        parser.error(
            "Output directory already exists. "
            "Choose a new directory to preserve existing datasets."
        )

    scheduled = generate_scheduled_demo_telemetry(
        ScheduledTelemetryConfig(seed=args.seed)
    )

    examples = build_next_observation_examples(scheduled)

    split = split_examples_by_device(examples, seed=args.seed)

    output_dir.mkdir(parents=True, exist_ok=False)

    partitions = {
        "train": split.train,
        "validation": split.validation,
        "test": split.test,
    }

    files = {
        name: write_jsonl(
            output_dir / f"{name}.jsonl",
            partition,
        )
        for name, partition in partitions.items()
    }

    device_partitions = {
        name: sorted({
            f"{item.zone_id}/{item.device_id}"
            for item in partition
        })
        for name, partition in partitions.items()
    }

    manifest = {
        "dataset_version": DATASET_VERSION,
        "simulation_seed": args.seed,
        "source": "DETERMINISTIC_SYNTHETIC_ENGINEERING_FIXTURE",
        "objective": "NEXT_OBSERVATION_SOIL_MOISTURE_REGRESSION",
        "forecast_horizon": "VARIABLE_NEXT_OBSERVATION",
        "min_history_steps": 3,
        "max_history_steps": 8,
        "split_method": "DEVICE_DISJOINT",
        "files": files,
        "devices": device_partitions,
        "limitations": [
            "Not a landslide event dataset",
            "No real-world ground-truth landslide labels",
            "Mode transitions are predefined simulation schedules",
            "Not a fixed-time-horizon risk forecast",
        ],
    }

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Dataset created: {output_dir}")
    print(
        f"Examples: train={len(split.train)}, "
        f"validation={len(split.validation)}, "
        f"test={len(split.test)}"
    )
    print("Existing datasets were not overwritten.")


if __name__ == "__main__":
    main()
