"""Train GeoNex C3 M1 Ridge Regression forecasting baselines."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from components.c3_forecasting.tabular_features import (
    extract_tabular_features,
)

HORIZONS = (15, 30, 60)
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)

# Use only training and validation during model selection.
SPLITS = ("train", "validation")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_examples(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                yield json.loads(line)


def prepare_data(dataset_dir: Path):
    """Extract numerical features without fitting preprocessing."""

    prepared = {}

    feature_names = None

    for split in SPLITS:
        grouped = {
            horizon: {"X": [], "y": []}
            for horizon in HORIZONS
        }

        for example in load_examples(
            dataset_dir / f"{split}.jsonl.gz"
        ):
            target = example["target"]
            horizon = int(target["requested_horizon_minutes"])

            if horizon not in HORIZONS:
                continue

            features = extract_tabular_features(
                example["input_sequence"]
            )

            current_names = tuple(sorted(features))

            if feature_names is None:
                feature_names = current_names
            elif current_names != feature_names:
                raise ValueError("Inconsistent feature schema")

            vector = [
                features[name]
                for name in feature_names
            ]

            grouped[horizon]["X"].append(vector)
            grouped[horizon]["y"].append(float(target["value"]))

        for horizon in HORIZONS:
            X = np.asarray(
                grouped[horizon]["X"],
                dtype=np.float64,
            )

            y = np.asarray(
                grouped[horizon]["y"],
                dtype=np.float64,
            )

            if X.size == 0:
                raise ValueError(
                    f"No examples for {split}/{horizon}"
                )

            if not np.isfinite(X).all():
                raise ValueError("Non-finite input features")

            if not np.isfinite(y).all():
                raise ValueError("Non-finite targets")

            prepared[(split, horizon)] = (X, y)

    return prepared, feature_names


def evaluate(model, X, y):
    predictions = model.predict(X)

    return {
        "mae": float(mean_absolute_error(y, predictions)),
        "rmse": float(
            np.sqrt(mean_squared_error(y, predictions))
        ),
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
        default=Path("data/processed/c3_m1_results"),
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

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    results = {}

    for horizon in HORIZONS:
        X_train, y_train = prepared[("train", horizon)]
        X_val, y_val = prepared[("validation", horizon)]

        print(f"\n=== {horizon}-MINUTE RIDGE MODEL ===")

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

            print(
                f"Alpha={alpha:<7} "
                f"Validation MAE={validation['mae']:.4f} "
                f"RMSE={validation['rmse']:.4f}"
            )

        # Choose using validation MAE only.
        best = min(
            candidates,
            key=lambda item: (
                item["validation"]["mae"],
                item["alpha"],
            ),
        )

        best_model = best["model"]

        training_metrics = evaluate(
            best_model,
            X_train,
            y_train,
        )

        model_path = (
            args.output_dir / f"ridge_{horizon}min.joblib"
        )

        joblib.dump(
            {
                "model": best_model,
                "feature_names": feature_names,
                "horizon_minutes": horizon,
                "target_feature": manifest["target_feature"],
                "dataset_sha256": sha256_file(manifest_path),
            },
            model_path,
        )

        results[str(horizon)] = {
            "selected_alpha": best["alpha"],
            "train": training_metrics,
            "validation": best["validation"],
            "train_examples": len(y_train),
            "validation_examples": len(y_val),
            "model_file": model_path.name,
            "model_sha256": sha256_file(model_path),
        }

        print(
            f"Selected alpha: {best['alpha']}"
        )

        print(
            f"Train MAE: {training_metrics['mae']:.4f}"
        )

        print(
            f"Validation MAE: "
            f"{best['validation']['mae']:.4f}"
        )

    report = {
        "model": "M1_RIDGE_REGRESSION",
        "model_version": "c3-m1-ridge-v1",
        "dataset_version": manifest["export_version"],
        "source_origin": "SIMULATED",
        "feature_count": len(feature_names),
        "feature_names": list(feature_names),
        "regularization_candidates": list(ALPHAS),
        "selection_metric": "VALIDATION_MAE",
        "preprocessing": "TRAIN_ONLY_STANDARD_SCALER",
        "results": results,
        "limitations": [
            "Synthetic sensor-value forecasting only",
            "No landslide-event ground truth",
            "No EMERGENCY forecast-origin examples",
            "Test split intentionally not evaluated during tuning",
            "Overlapping examples are not statistically independent",
        ],
    }

    report_path = args.output_dir / "metrics.json"

    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n=== M1 RIDGE TRAINING COMPLETED ===")
    print(f"Feature count: {len(feature_names)}")
    print(f"Saved results: {report_path}")


if __name__ == "__main__":
    main()