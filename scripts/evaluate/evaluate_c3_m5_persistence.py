"""
GeoNex C3 — M5 Persistence Baseline Evaluation.

Compares a persistence forecasting baseline against the
trained M5 GRU using the exact same held-out test episodes.

Persistence:
    Predicted future sensor value = latest observed value.

Dataset:
    Synthetic variable-rate engineering simulation.

Research status:
    Experimental. Not approved for real-world deployment.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from components.c3_forecasting.models.m5_multivariate_gru import (
    SENSOR_FEATURES,
    FORECAST_HORIZONS,
)

from components.c3_forecasting.preprocessing.m5_dataset import (
    M5DatasetConfig,
)

from components.c3_forecasting.preprocessing.m5_reference_dataset import (
    build_reference_aligned_samples,
)

from scripts.train.train_c3_m5_multivariate import (
    load_observations,
)


def group_key(row):
    return (
        str(row["dataset_id"]),
        str(row["device_id"]),
        str(row["episode_id"]),
    )


def calculate_metrics(samples):

    metrics = {}

    for horizon_index, horizon in enumerate(
        FORECAST_HORIZONS
    ):

        horizon_metrics = {}

        for sensor_index, sensor in enumerate(
            SENSOR_FEATURES
        ):

            errors = []

            for sample in samples:

                if (
                    sample.target_mask[
                        horizon_index,
                        sensor_index
                    ] == 0
                ):
                    continue

                # The first seven feature channels contain
                # the historical sensor measurements.
                #
                # Persistence uses the latest observed value.
                prediction = float(
                    sample.features[-1, sensor_index]
                )

                actual = float(
                    sample.targets[
                        horizon_index,
                        sensor_index
                    ]
                )

                errors.append(
                    prediction - actual
                )

            if not errors:
                horizon_metrics[sensor] = {
                    "mae": None,
                    "rmse": None,
                    "count": 0,
                }
                continue

            errors = np.asarray(
                errors,
                dtype=np.float64,
            )

            horizon_metrics[sensor] = {
                "mae": float(
                    np.mean(np.abs(errors))
                ),
                "rmse": float(
                    np.sqrt(
                        np.mean(errors ** 2)
                    )
                ),
                "count": int(len(errors)),
            }

        metrics[str(horizon)] = horizon_metrics

    return metrics


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
    )

    parser.add_argument(
        "--reference",
        required=True,
    )

    parser.add_argument(
        "--training-report",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # LOAD ORIGINAL TRAINING REPORT
    # --------------------------------------------------------

    report = json.loads(
        Path(args.training_report).read_text()
    )

    test_groups = {
        tuple(group)
        for group in report[
            "split_manifest"
        ]["test_groups"]
    }

    print("\nGEONEX C3 — MATCHED PERSISTENCE BASELINE")
    print("=" * 60)

    print(
        "Held-out test episode groups:",
        len(test_groups),
    )

    # --------------------------------------------------------
    # LOAD DATASETS
    # --------------------------------------------------------

    observations = load_observations(
        Path(args.input)
    )

    reference = load_observations(
        Path(args.reference)
    )

    # --------------------------------------------------------
    # FILTER EXACT ORIGINAL TEST GROUPS
    # --------------------------------------------------------

    test_observations = [
        row
        for row in observations
        if group_key(row) in test_groups
    ]

    test_reference = [
        row
        for row in reference
        if group_key(row) in test_groups
    ]

    assert test_observations, (
        "No matching test observations."
    )

    assert test_reference, (
        "No matching reference observations."
    )

    print(
        "Test observations:",
        len(test_observations),
    )

    print(
        "Test reference rows:",
        len(test_reference),
    )

    # --------------------------------------------------------
    # BUILD MATCHED TEST SAMPLES
    # --------------------------------------------------------

    config = M5DatasetConfig(
        sequence_length=32,
        minimum_sequence_length=3,
        minimum_valid_targets=1,
        require_all_horizons=False,
    )

    samples = build_reference_aligned_samples(
        test_observations,
        test_reference,
        config,
    )

    print(
        "Generated test samples:",
        len(samples),
    )

    expected_samples = int(
        report["test_samples"]
    )

    assert len(samples) == expected_samples, (
        "Test sample count mismatch. "
        f"Expected {expected_samples}, "
        f"received {len(samples)}."
    )

    # --------------------------------------------------------
    # CALCULATE PERSISTENCE METRICS
    # --------------------------------------------------------

    persistence_metrics = calculate_metrics(
        samples
    )

    gru_metrics = report["test_metrics"]

    comparison = {}

    print("\nMATCHED TEST COMPARISON")
    print("=" * 60)

    for horizon in FORECAST_HORIZONS:

        horizon_key = str(horizon)

        comparison[horizon_key] = {}

        print(
            f"\nForecast horizon: +{horizon} minutes"
        )

        print(
            f"{'Sensor':25s} "
            f"{'GRU MAE':>12s} "
            f"{'Persistence':>12s} "
            f"{'Improvement':>12s}"
        )

        print("-" * 65)

        for sensor in SENSOR_FEATURES:

            gru_mae = float(
                gru_metrics[
                    horizon_key
                ][sensor]["mae"]
            )

            persistence_mae = float(
                persistence_metrics[
                    horizon_key
                ][sensor]["mae"]
            )

            improvement_pct = (
                (
                    persistence_mae - gru_mae
                )
                / persistence_mae
                * 100.0
                if persistence_mae > 0
                else None
            )

            comparison[horizon_key][sensor] = {
                "gru_mae": gru_mae,
                "persistence_mae": persistence_mae,
                "improvement_pct": improvement_pct,
            }

            improvement_display = (
                f"{improvement_pct:+.2f}%"
                if improvement_pct is not None
                else "N/A"
            )

            print(
                f"{sensor:25s} "
                f"{gru_mae:12.6f} "
                f"{persistence_mae:12.6f} "
                f"{improvement_display:>12s}"
            )

    # --------------------------------------------------------
    # SAVE COMPARISON
    # --------------------------------------------------------

    output = Path(args.output)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = {
        "experiment": "M5_V3_MATCHED_PERSISTENCE_BASELINE",
        "dataset_type": "SYNTHETIC_ENGINEERING_SIMULATION",
        "research_status": "EXPERIMENTAL",
        "test_episode_groups": len(test_groups),
        "test_samples": len(samples),
        "persistence_metrics": persistence_metrics,
        "comparison": comparison,
    }

    output.write_text(
        json.dumps(
            result,
            indent=2,
        )
    )

    print("\n" + "=" * 60)
    print("MATCHED BASELINE EVALUATION COMPLETED")
    print("=" * 60)

    print("Saved:", output)


if __name__ == "__main__":
    main()