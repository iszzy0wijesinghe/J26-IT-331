"""
Generate GeoNex C3 synthetic variable-rate datasets.
"""

import argparse
import csv
import json
from pathlib import Path

from components.c3_forecasting.simulation.m5_variable_rate_simulator import (
    SimulationConfig,
    generate_dataset,
    MODE_INTERVALS,
)


def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        raise ValueError("Cannot save an empty dataset")

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--episodes", type=int, default=36)
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output-dir",
        default="data/processed/c3_m5_variable_rate",
    )

    args = parser.parse_args()

    config = SimulationConfig(
        episodes=args.episodes,
        duration_hours=args.hours,
        seed=args.seed,
    )

    reference, observations = generate_dataset(config)

    output_dir = Path(args.output_dir)

    save_csv(
        output_dir / "reference_timeline.csv",
        reference,
    )

    save_csv(
        output_dir / "variable_rate_observations.csv",
        observations,
    )

    metadata = {
        "dataset_type": "SYNTHETIC_ENGINEERING_SIMULATION",
        "research_training_approved": False,
        "episodes": args.episodes,
        "duration_hours": args.hours,
        "seed": args.seed,
        "reference_interval_seconds": config.reference_interval_seconds,
        "mode_intervals": MODE_INTERVALS,
        "reference_rows": len(reference),
        "observation_rows": len(observations),
        "warning": (
            "Simulated environmental relationships; "
            "not independently validated landslide data."
        ),
    }

    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()