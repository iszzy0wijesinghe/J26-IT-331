"""Evaluate the C3 M0 persistence baseline on exported V2 data."""

from __future__ import annotations

import argparse
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path

from components.c3_forecasting.models.persistence_baseline import (
    predict_persistence,
)


def load_examples(path: Path):
    """Read compressed JSONL training examples."""

    with gzip.open(path, "rt", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                yield json.loads(line)


def evaluate_split(
    dataset_dir: Path,
    split: str,
) -> dict:
    """Evaluate persistence predictions by forecast horizon."""

    path = dataset_dir / f"{split}.jsonl.gz"

    results = defaultdict(
        lambda: {
            "total": 0,
            "predicted": 0,
            "absolute_errors": [],
            "squared_errors": [],
            "source_ages_seconds": [],
        }
    )

    for example in load_examples(path):
        target = example["target"]

        horizon = target["requested_horizon_minutes"]
        actual = float(target["value"])

        prediction = predict_persistence(
            example["input_sequence"],
            target_feature=target["feature"],
        )

        result = results[horizon]
        result["total"] += 1

        if prediction.prediction is None:
            continue

        error = prediction.prediction - actual

        result["predicted"] += 1
        result["absolute_errors"].append(abs(error))
        result["squared_errors"].append(error**2)
        result["source_ages_seconds"].append(
            prediction.source_age_seconds
        )

    summary = {}

    for horizon, result in sorted(results.items()):
        total = result["total"]
        predicted = result["predicted"]

        if predicted:
            mae = (
                sum(result["absolute_errors"]) / predicted
            )

            rmse = math.sqrt(
                sum(result["squared_errors"]) / predicted
            )

            mean_source_age = (
                sum(result["source_ages_seconds"]) / predicted
            )
        else:
            mae = None
            rmse = None
            mean_source_age = None

        summary[str(horizon)] = {
            "total_examples": total,
            "predicted_examples": predicted,
            "unavailable_examples": total - predicted,
            "prediction_coverage": (
                predicted / total if total else 0.0
            ),
            "mae": mae,
            "rmse": rmse,
            "mean_source_age_seconds": mean_source_age,
        }

    return summary


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("data/processed/c3_v2"),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/c3_m0_results"),
    )

    args = parser.parse_args()

    manifest_path = args.dataset_dir / "manifest.json"

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    if manifest["export_version"] != "c3-fixed-horizon-v2":
        raise ValueError("Unsupported dataset version")

    summaries = {}

    for split in ("train", "validation", "test"):
        summaries[split] = evaluate_split(
            args.dataset_dir,
            split,
        )

    report = {
        "model": "M0_STRICT_PERSISTENCE",
        "model_version": "c3-m0-v1",
        "dataset_version": manifest["export_version"],
        "source_origin": "SIMULATED",
        "target_feature": manifest["target_feature"],
        "evaluation": summaries,
        "limitations": [
            "Synthetic sensor-value forecasting only",
            "Not a landslide-event prediction model",
            "No real-world accuracy claims",
            "No EMERGENCY forecast-origin coverage",
            "Overlapping forecasting examples are dependent",
        ],
    }

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = args.output_dir / "metrics.json"

    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n=== GEONEX C3 M0 PERSISTENCE BASELINE ===")

    for split, horizons in summaries.items():
        print(f"\n{split.upper()}")

        for horizon, metrics in horizons.items():
            mae = metrics["mae"]
            rmse = metrics["rmse"]

            print(
                f"  {horizon:>2} min | "
                f"MAE: {mae:.4f} | "
                f"RMSE: {rmse:.4f} | "
                f"Coverage: "
                f"{metrics['prediction_coverage'] * 100:.2f}%"
                if mae is not None and rmse is not None
                else f"  {horizon} min | No valid predictions"
            )

    print(f"\nSaved metrics: {report_path}")


if __name__ == "__main__":
    main()