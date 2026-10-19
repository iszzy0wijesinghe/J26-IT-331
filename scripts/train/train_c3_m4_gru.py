"""Train GeoNex C3 M4 mode-conditioned variable-rate GRU experiments."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from components.c3_forecasting.models.standard_gru import C3StandardGRU
from components.c3_forecasting.preprocessing.gru_target_normalization import (
    GRUTargetNormalizer,
)
from components.c3_forecasting.preprocessing.m4_dataset import (
    C3M4Dataset,
    collate_m4_batch,
    load_m4_split,
)
from components.c3_forecasting.preprocessing.m4_features import M4_INPUT_FEATURE_COUNT
from components.c3_forecasting.preprocessing.m4_normalization import M4Normalizer
from scripts.train.train_c3_m3_gru import (
    choose_device,
    run_epoch,
    set_seed,
)

SEED = 20261018

DEFAULT_DATASET_DIR = Path("data/processed/c3_v2")
DEFAULT_OUTPUT_DIR = Path("data/processed/c3_m4_results")

DEFAULT_BATCH_SIZE = 64
DEFAULT_LEARNING_RATE = 0.001
DEFAULT_MAX_EPOCHS = 50
DEFAULT_PATIENCE = 8

HIDDEN_SIZE = 64
NUM_LAYERS = 1

VALID_HORIZONS = frozenset({15, 30, 60})

ABLATIONS = {
    "A": {
        "include_time": True,
        "include_mode": False,
    },
    "B": {
        "include_time": False,
        "include_mode": True,
    },
    "C": {
        "include_time": True,
        "include_mode": True,
    },
}


class NormalizedM4Dataset(Dataset):
    """Apply M4 normalization and experiment-specific feature masking."""

    def __init__(
        self,
        source_dataset: C3M4Dataset,
        normalizer: M4Normalizer,
        *,
        include_time: bool,
        include_mode: bool,
    ) -> None:
        self.source_dataset = source_dataset
        self.normalizer = normalizer
        self.include_time = include_time
        self.include_mode = include_mode

    def __len__(self) -> int:
        return len(self.source_dataset)

    def __getitem__(self, index: int) -> dict:
        example = self.source_dataset[index]

        sequence = self.normalizer.transform(
            example["sequence"],
            include_time=self.include_time,
            include_mode=self.include_mode,
        )

        return {
            **example,
            "sequence": sequence,
        }


def train(
    *,
    dataset_dir: Path,
    output_dir: Path,
    horizon: int,
    ablation: str,
    batch_size: int,
    learning_rate: float,
    max_epochs: int,
    patience: int,
    device_name: str,
) -> dict:
    """Train one M4 ablation for one forecasting horizon."""

    if horizon not in VALID_HORIZONS:
        raise ValueError("Horizon must be 15, 30, or 60 minutes")

    if ablation not in ABLATIONS:
        raise ValueError("Ablation must be A, B, or C")

    if batch_size <= 0:
        raise ValueError("Batch size must be positive")

    if not np.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("Learning rate must be finite and positive")

    if max_epochs <= 0:
        raise ValueError("Maximum epochs must be positive")

    if patience <= 0:
        raise ValueError("Early stopping patience must be positive")

    set_seed(SEED)

    device = choose_device(device_name)

    configuration = ABLATIONS[ablation]

    include_time = configuration["include_time"]
    include_mode = configuration["include_mode"]

    print("\n=== GEONEX C3 M4 GRU ===", flush=True)
    print(f"Ablation: M4-{ablation}", flush=True)
    print(f"Horizon: {horizon} minutes", flush=True)
    print(f"Elapsed-time features: {include_time}", flush=True)
    print(f"Operating-mode features: {include_mode}", flush=True)
    print(f"Device: {device}", flush=True)
    print(f"Seed: {SEED}", flush=True)

    # --------------------------------------------------------
    # Load training and validation only.
    # --------------------------------------------------------

    print("\nLoading training examples...", flush=True)

    train_examples = load_m4_split(dataset_dir, "train")

    print("Loading validation examples...", flush=True)

    validation_examples = load_m4_split(dataset_dir, "validation")

    train_dataset = C3M4Dataset(
        dataset_dir,
        split="train",
        horizon_minutes=horizon,
        preloaded_examples=train_examples,
    )

    validation_dataset = C3M4Dataset(
        dataset_dir,
        split="validation",
        horizon_minutes=horizon,
        preloaded_examples=validation_examples,
    )

    print(f"Training examples: {len(train_dataset)}")
    print(f"Validation examples: {len(validation_dataset)}")

    # --------------------------------------------------------
    # Training-only normalization.
    # --------------------------------------------------------

    print("\nFitting M4 normalizer...", flush=True)

    sensor_normalizer = M4Normalizer.fit(train_dataset.examples)

    target_normalizer = GRUTargetNormalizer.fit(train_dataset.examples)

    print(f"Target mean: {target_normalizer.mean:.4f}")
    print(f"Target std: {target_normalizer.std:.4f}")

    # --------------------------------------------------------
    # Prepare normalized datasets.
    # --------------------------------------------------------

    normalized_train = NormalizedM4Dataset(
        train_dataset,
        sensor_normalizer,
        include_time=include_time,
        include_mode=include_mode,
    )

    normalized_validation = NormalizedM4Dataset(
        validation_dataset,
        sensor_normalizer,
        include_time=include_time,
        include_mode=include_mode,
    )

    train_loader = DataLoader(
        normalized_train,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
        collate_fn=collate_m4_batch,
    )

    validation_loader = DataLoader(
        normalized_validation,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        collate_fn=collate_m4_batch,
    )

    # --------------------------------------------------------
    # Initialize model.
    # --------------------------------------------------------

    model = C3StandardGRU(
        input_size=M4_INPUT_FEATURE_COUNT,
        hidden_size=HIDDEN_SIZE,
        num_layers=NUM_LAYERS,
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=learning_rate,
    )

    parameter_count = sum(parameter.numel() for parameter in model.parameters())

    print(f"\nTrainable parameters: {parameter_count}")

    # --------------------------------------------------------
    # Training state.
    # --------------------------------------------------------

    history: list[dict] = []

    best_validation_mae = float("inf")
    best_validation_metrics: dict | None = None

    best_epoch = 0
    epochs_without_improvement = 0

    output_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = output_dir / f"m4_{ablation.lower()}_{horizon}min.pt"

    # --------------------------------------------------------
    # Training loop.
    # --------------------------------------------------------

    for epoch in range(1, max_epochs + 1):
        training_metrics = run_epoch(
            model=model,
            loader=train_loader,
            device=device,
            optimizer=optimizer,
            target_normalizer=target_normalizer,
        )

        validation_metrics = run_epoch(
            model=model,
            loader=validation_loader,
            device=device,
            optimizer=None,
            target_normalizer=target_normalizer,
        )

        record = {
            "epoch": epoch,
            "training_mae": training_metrics["mae"],
            "training_rmse": training_metrics["rmse"],
            "validation_mae": validation_metrics["mae"],
            "validation_rmse": validation_metrics["rmse"],
        }

        history.append(record)

        print(
            f"Epoch {epoch:02d} | "
            f"Train MAE: {training_metrics['mae']:.4f} | "
            f"Train RMSE: {training_metrics['rmse']:.4f} | "
            f"Val MAE: {validation_metrics['mae']:.4f} | "
            f"Val RMSE: {validation_metrics['rmse']:.4f}",
            flush=True,
        )

        # ----------------------------------------------------
        # Save the best validation checkpoint.
        # ----------------------------------------------------

        if validation_metrics["mae"] < best_validation_mae:
            best_validation_mae = validation_metrics["mae"]
            best_validation_metrics = validation_metrics.copy()

            best_epoch = epoch
            epochs_without_improvement = 0

            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "model": "m4_gru",
                    "ablation": ablation,
                    "include_time": include_time,
                    "include_mode": include_mode,
                    "horizon_minutes": horizon,
                    "target_feature": "soil_moisture_pct",
                    "dataset_version": "c3-fixed-horizon-v2",
                    "input_size": M4_INPUT_FEATURE_COUNT,
                    "hidden_size": HIDDEN_SIZE,
                    "num_layers": NUM_LAYERS,
                    "normalizer": sensor_normalizer.to_dict(),
                    "target_normalizer": target_normalizer.to_dict(),
                    "seed": SEED,
                    "best_epoch": best_epoch,
                    "validation_metrics": best_validation_metrics,
                },
                checkpoint_path,
            )

            print("  -> Best checkpoint updated.", flush=True)

        else:
            epochs_without_improvement += 1

        if epochs_without_improvement >= patience:
            print(
                f"\nEarly stopping at epoch {epoch}.",
                flush=True,
            )
            break

    # --------------------------------------------------------
    # Save experiment metadata.
    # --------------------------------------------------------

    result = {
        "model": "m4_gru",
        "ablation": ablation,
        "include_time": include_time,
        "include_mode": include_mode,
        "dataset_version": "c3-fixed-horizon-v2",
        "target_feature": "soil_moisture_pct",
        "horizon_minutes": horizon,
        "device": str(device),
        "seed": SEED,
        "train_examples": len(train_dataset),
        "validation_examples": len(validation_dataset),
        "parameter_count": parameter_count,
        "configuration": {
            "input_size": M4_INPUT_FEATURE_COUNT,
            "hidden_size": HIDDEN_SIZE,
            "num_layers": NUM_LAYERS,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "max_epochs": max_epochs,
            "patience": patience,
            "optimizer": "Adam",
            "loss": "MSE",
            "loss_units": "standardized_target",
            "reported_metric_units": "soil_moisture_percentage_points",
            "selection_metric": "validation_mae",
        },
        "normalizer": sensor_normalizer.to_dict(),
        "target_normalizer": target_normalizer.to_dict(),
        "best_epoch": best_epoch,
        "best_validation_mae": best_validation_mae,
        "best_validation_metrics": best_validation_metrics,
        "epochs_completed": len(history),
        "history": history,
        "checkpoint": checkpoint_path.name,
        "created_at": datetime.now(UTC).isoformat(),
    }

    metrics_path = output_dir / f"m4_{ablation.lower()}_{horizon}min_metrics.json"

    metrics_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print("\n=== M4 TRAINING COMPLETE ===")
    print(f"Best epoch: {best_epoch}")
    print(f"Best validation MAE: {best_validation_mae:.4f}")

    if best_validation_metrics is not None:
        print("Best validation RMSE: " f"{best_validation_metrics['rmse']:.4f}")

    print(f"Checkpoint: {checkpoint_path}")
    print(f"Metrics: {metrics_path}")

    return result


def main() -> None:
    """Parse CLI arguments and launch M4 training."""

    parser = argparse.ArgumentParser(description="Train GeoNex C3 M4 GRU ablation experiments")

    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_DATASET_DIR,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )

    parser.add_argument(
        "--horizon",
        type=int,
        choices=(15, 30, 60),
        default=15,
    )

    parser.add_argument(
        "--ablation",
        choices=("A", "B", "C"),
        default="A",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=DEFAULT_LEARNING_RATE,
    )

    parser.add_argument(
        "--max-epochs",
        type=int,
        default=DEFAULT_MAX_EPOCHS,
    )

    parser.add_argument(
        "--patience",
        type=int,
        default=DEFAULT_PATIENCE,
    )

    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "mps"),
        default="auto",
    )

    args = parser.parse_args()

    train(
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        horizon=args.horizon,
        ablation=args.ablation,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        max_epochs=args.max_epochs,
        patience=args.patience,
        device_name=args.device,
    )


if __name__ == "__main__":
    main()
