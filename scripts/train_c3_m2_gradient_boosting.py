"""Train GeoNex C3 M2 histogram gradient boosting baselines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from scripts.train_c3_m1_ridge import (
    HORIZONS,
    prepare_data,
    sha256_file,
)

RANDOM_STATE = 20261018

PARAMETER_CANDIDATES = (
    {
        "learning_rate": 0.05,
        "max_iter": 100,
        "max_leaf_nodes": 15,
        "l2_regularization": 1.0,
    },
    {
        "learning_rate": 0.05,
        "max_iter": 200,
        "max_leaf_nodes": 15,
        "l2_regularization": 1.0,
    },
    {
        "learning_rate": 0.05,
        "max_iter": 200,
        "max_leaf_nodes": 31,
        "l2_regularization": 1.0,
    },
    {
        "learning_rate": 0.1,
        "max_iter": 200,
        "max_leaf_nodes": 15,
        "l2_regularization": 10.0,
    },
)


def evaluate(model, X, y):
    predictions = model.predict(X)

    return {
        "mae": float(mean_absolute_error(y, predictions)),
        "rmse": float(
            np.sqrt(mean_squared_error(y, predictions))
        ),
    }


def train_horizon(X_train, y_train, X_val, y_val):
    """Select a boosting configuration using validation MAE."""

    candidates = []

    for parameters in PARAMETER_CANDIDATES:
        model = HistGradientBoostingRegressor(
            **parameters,
            random_state=RANDOM_STATE,
            early_stopping=False,
        )

        model.fit(X_train, y_train)

        validation = evaluate(model, X_val, y_val)

        candidates.append(
            {
                "parameters": parameters,
                "model": model,
                "validation": validation,
            }
        )

        print(
            f"Params={parameters} | "
            f"Validation MAE={validation['mae']:.4f} | "
            f"RMSE={validation['rmse']:.4f}"
        )

    best_index = min(
        range(len(candidates)),
        key=lambda index: (
            candidates[index]["validation"]["mae"],
            index,
        ),
    )

    return candidates[best_index]


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
        default=Path("data/processed/c3_m2_results"),
    )

    args = parser.parse_args()

    manifest_path = args.dataset_dir / "manifest.json"

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    if manifest["export_version"] != "c3-fixed-horizon-v2":
        raise ValueError("Unsupported dataset version")

    print("Extracting C3 tabular features...")

    prepared, feature_names = prepare_data(args.dataset_dir)

    if len(feature_names) != 79:
        raise ValueError(
            f"Expected 79 features, found {len(feature_names)}"
        )

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    results = {}

    for horizon in HORIZONS:
        X_train, y_train = prepared[("train", horizon)]
        X_val, y_val = prepared[("validation", horizon)]

        print(f"\n=== {horizon}-MINUTE GRADIENT BOOSTING ===")

        best = train_horizon(
            X_train,
            y_train,
            X_val,
            y_val,
        )

        model = best["model"]

        training_metrics = evaluate(
            model,
            X_train,
            y_train,
        )

        model_path = (
            args.output_dir
            / f"gradient_boosting_{horizon}min.joblib"
        )

        joblib.dump(
            {
                "model": model,
                "feature_names": feature_names,
                "horizon_minutes": horizon,
                "target_feature": manifest["target_feature"],
                "dataset_manifest_sha256": sha256_file(
                    manifest_path
                ),
                "random_state": RANDOM_STATE,
            },
            model_path,
        )

        results[str(horizon)] = {
            "selected_parameters": best["parameters"],
            "train": training_metrics,
            "validation": best["validation"],
            "train_examples": len(y_train),
            "validation_examples": len(y_val),
            "model_file": model_path.name,
            "model_sha256": sha256_file(model_path),
        }

        print(
            f"\nSelected parameters: "
            f"{best['parameters']}"
        )

        print(
            f"Train MAE: "
            f"{training_metrics['mae']:.4f}"
        )

        print(
            f"Validation MAE: "
            f"{best['validation']['mae']:.4f}"
        )

    report = {
        "model": "M2_HIST_GRADIENT_BOOSTING",
        "model_version": "c3-m2-v1",
        "dataset_version": manifest["export_version"],
        "source_origin": "SIMULATED",
        "target_feature": manifest["target_feature"],
        "feature_count": len(feature_names),
        "feature_names": list(feature_names),
        "random_state": RANDOM_STATE,
        "selection_metric": "VALIDATION_MAE",
        "parameter_candidates": list(PARAMETER_CANDIDATES),
        "results": results,
        "limitations": [
            "Synthetic sensor-value forecasting only",
            "No verified landslide-event labels",
            "No real-world forecasting accuracy claims",
            "No EMERGENCY forecast-origin coverage",
            "Operating-mode contribution not isolated",
            "Overlapping forecasting examples are dependent",
            "Test split reserved for final evaluation",
        ],
    }

    report_path = args.output_dir / "metrics.json"

    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n=== M2 GRADIENT BOOSTING COMPLETED ===")
    print(f"Feature count: {len(feature_names)}")
    print(f"Saved metrics: {report_path}")


if __name__ == "__main__":
    main()