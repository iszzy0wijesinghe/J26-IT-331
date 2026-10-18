"""Compare GeoNex C3 Ridge models with and without operating-mode features."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from scripts.train_c3_m1_ridge import (
    ALPHAS,
    HORIZONS,
    prepare_data,
)

CONFIGURATIONS = ("WITHOUT_MODE", "WITH_MODE")


def evaluate(model, X, y):
    predictions = model.predict(X)

    return {
        "mae": float(mean_absolute_error(y, predictions)),
        "rmse": float(
            np.sqrt(mean_squared_error(y, predictions))
        ),
    }


def select_columns(feature_names, configuration):
    if configuration == "WITH_MODE":
        return list(range(len(feature_names)))

    return [
        index
        for index, name in enumerate(feature_names)
        if not name.startswith("mode_")
    ]


def train_configuration(
    X_train,
    y_train,
    X_val,
    y_val,
):
    candidates = []

    for alpha in ALPHAS:
        model = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("ridge", Ridge(alpha=alpha)),
            ]
        )

        model.fit(X_train, y_train)

        validation = evaluate(model, X_val, y_val)

        candidates.append(
            {
                "alpha": alpha,
                "model": model,
                "validation": validation,
            }
        )

    best = min(
        candidates,
        key=lambda item: (
            item["validation"]["mae"],
            item["alpha"],
        ),
    )

    return {
        "selected_alpha": best["alpha"],
        "train": evaluate(best["model"], X_train, y_train),
        "validation": best["validation"],
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("data/processed/c3_v2"),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/c3_m1_ablation"),
    )

    args = parser.parse_args()

    manifest = json.loads(
        (args.dataset_dir / "manifest.json").read_text(
            encoding="utf-8"
        )
    )

    if manifest["export_version"] != "c3-fixed-horizon-v2":
        raise ValueError("Unsupported dataset version")

    prepared, feature_names = prepare_data(args.dataset_dir)

    if len(feature_names) != 79:
        raise ValueError(
            f"Expected 79 features, found {len(feature_names)}"
        )

    results = {}

    for horizon in HORIZONS:
        print(f"\n=== {horizon}-MINUTE MODE ABLATION ===")

        X_train, y_train = prepared[("train", horizon)]
        X_val, y_val = prepared[("validation", horizon)]

        horizon_results = {}

        for configuration in CONFIGURATIONS:
            columns = select_columns(
                feature_names,
                configuration,
            )

            selected_train = X_train[:, columns]
            selected_val = X_val[:, columns]

            metrics = train_configuration(
                selected_train,
                y_train,
                selected_val,
                y_val,
            )

            metrics["feature_count"] = len(columns)

            horizon_results[configuration] = metrics

            print(
                f"{configuration:<15} | "
                f"Features: {len(columns):>2} | "
                f"Alpha: {metrics['selected_alpha']:<6} | "
                f"Validation MAE: "
                f"{metrics['validation']['mae']:.4f}"
            )

        without_mae = horizon_results[
            "WITHOUT_MODE"
        ]["validation"]["mae"]

        with_mae = horizon_results[
            "WITH_MODE"
        ]["validation"]["mae"]

        improvement = (
            (without_mae - with_mae) / without_mae * 100.0
            if without_mae > 0
            else 0.0
        )

        horizon_results["mode_mae_improvement_pct"] = improvement

        results[str(horizon)] = horizon_results

        print(f"Mode MAE improvement: {improvement:+.2f}%")

    report = {
        "experiment": "C3_M1_OPERATING_MODE_ABLATION",
        "dataset_version": manifest["export_version"],
        "source_origin": "SIMULATED",
        "selection_metric": "VALIDATION_MAE",
        "regularization_candidates": list(ALPHAS),
        "configurations": {
            "WITHOUT_MODE": {
                "description": "Ridge without explicit operating-mode indicators",
                "feature_count": 74,
            },
            "WITH_MODE": {
                "description": "Ridge with explicit operating-mode indicators",
                "feature_count": 79,
            },
        },
        "results": results,
        "limitations": [
            "Synthetic telemetry only",
            "No real landslide-event labels",
            "Mode indicators are generated by a synthetic controller",
            "Timing features remain in both configurations",
            "No EMERGENCY forecast-origin evaluation",
            "Overlapping examples are not statistically independent",
            "Validation results are exploratory, not final test estimates",
        ],
    }

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = args.output_dir / "metrics.json"

    output_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n=== MODE ABLATION COMPLETED ===")
    print(f"Saved results: {output_path}")


if __name__ == "__main__":
    main()