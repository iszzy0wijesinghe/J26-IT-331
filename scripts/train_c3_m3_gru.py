"""Train the GeoNex C3 standard GRU forecasting baseline."""

from __future__ import annotations

import argparse
import json
import random
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from components.c3_forecasting.gru_dataset import (
    C3GRUDataset,
    collate_gru_batch,
    load_gru_split,
)
from components.c3_forecasting.gru_model import C3StandardGRU
from components.c3_forecasting.gru_normalization import GRUNormalizer

SEED = 20261018

DEFAULT_DATASET_DIR = Path("data/processed/c3_v2")
DEFAULT_OUTPUT_DIR = Path("data/processed/c3_m3_results")

DEFAULT_BATCH_SIZE = 64
DEFAULT_LEARNING_RATE = 0.001
DEFAULT_MAX_EPOCHS = 30
DEFAULT_PATIENCE = 5

HIDDEN_SIZE = 64
NUM_LAYERS = 1


class NormalizedGRUDataset(Dataset):
    """Apply a fitted normalizer without changing source examples."""

    def __init__(
        self,
        source_dataset: C3GRUDataset,
        normalizer: GRUNormalizer,
    ) -> None:
        self.source_dataset = source_dataset
        self.normalizer = normalizer

    def __len__(self) -> int:
        return len(self.source_dataset)

    def __getitem__(self, index: int) -> dict:
        example = self.source_dataset[index]

        return {
            **example,
            "sequence": self.normalizer.transform(
                example["sequence"]
            ),
        }


def set_seed(seed: int) -> None:
    """Set random seeds for reproducible experiments."""

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.backends.mps.is_available():
        torch.mps.manual_seed(seed)


def choose_device(requested: str) -> torch.device:
    """Choose the requested execution device."""

    if requested == "cpu":
        return torch.device("cpu")

    if requested == "mps":
        if not torch.backends.mps.is_available():
            raise RuntimeError(
                "MPS was requested but is unavailable"
            )

        return torch.device("mps")

    if torch.backends.mps.is_available():
        return torch.device("mps")

    return torch.device("cpu")


def make_loader(
    dataset: Dataset,
    *,
    batch_size: int,
    shuffle: bool,
) -> DataLoader:
    """Create a GRU DataLoader."""

    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0,
        collate_fn=collate_gru_batch,
    )


def run_epoch(
    model: C3StandardGRU,
    loader: DataLoader,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None,
) -> dict[str, float]:
    """Run one training or validation epoch."""

    training = optimizer is not None

    model.train(training)

    total_absolute_error = 0.0
    total_squared_error = 0.0
    total_examples = 0

    criterion = nn.MSELoss()

    context = (
        torch.enable_grad()
        if training
        else torch.no_grad()
    )

    with context:
        for batch in loader:
            inputs = batch["inputs"].to(device)
            lengths = batch["lengths"]
            targets = batch["targets"].to(device)

            if training:
                optimizer.zero_grad(set_to_none=True)

            predictions = model(inputs, lengths)

            loss = criterion(predictions, targets)

            if training:
                loss.backward()

                torch.nn.utils.clip_grad_norm_(
                    model.parameters(),
                    max_norm=1.0,
                )

                optimizer.step()

            errors = predictions.detach() - targets

            total_absolute_error += (
                errors.abs().sum().item()
            )

            total_squared_error += (
                errors.square().sum().item()
            )

            total_examples += targets.shape[0]

    if total_examples == 0:
        raise ValueError("Empty GRU DataLoader")

    mae = total_absolute_error / total_examples

    rmse = (
        total_squared_error / total_examples
    ) ** 0.5

    return {
        "mae": mae,
        "rmse": rmse,
        "count": total_examples,
    }


def train(
    *,
    dataset_dir: Path,
    output_dir: Path,
    horizon: int,
    batch_size: int,
    learning_rate: float,
    max_epochs: int,
    patience: int,
    device_name: str,
) -> dict:
    """Train one forecast-horizon GRU model."""

    if horizon not in {15, 30, 60}:
        raise ValueError("Horizon must be 15, 30, or 60")

    if batch_size <= 0:
        raise ValueError("Batch size must be positive")

    if learning_rate <= 0:
        raise ValueError("Learning rate must be positive")

    if max_epochs <= 0 or patience <= 0:
        raise ValueError(
            "Epochs and patience must be positive"
        )

    set_seed(SEED)

    device = choose_device(device_name)

    print("\n=== GEONEX C3 M3 STANDARD GRU ===")
    print("Horizon:", horizon, "minutes")
    print("Device:", device)

    # --------------------------------------------------------
    # Load only train and validation splits.
    # --------------------------------------------------------

    print("\nLoading training examples...")

    train_examples = load_gru_split(
        dataset_dir,
        "train",
    )

    print("Loading validation examples...")

    validation_examples = load_gru_split(
        dataset_dir,
        "validation",
    )

    train_dataset = C3GRUDataset(
        dataset_dir,
        split="train",
        horizon_minutes=horizon,
        preloaded_examples=train_examples,
    )

    validation_dataset = C3GRUDataset(
        dataset_dir,
        split="validation",
        horizon_minutes=horizon,
        preloaded_examples=validation_examples,
    )

    print("Training examples:", len(train_dataset))
    print("Validation examples:", len(validation_dataset))

    # --------------------------------------------------------
    # Fit normalization on training examples only.
    # --------------------------------------------------------

    print("\nFitting training-only normalizer...")

    normalizer = GRUNormalizer.fit(
        train_dataset.examples
    )

    normalized_train = NormalizedGRUDataset(
        train_dataset,
        normalizer,
    )

    normalized_validation = NormalizedGRUDataset(
        validation_dataset,
        normalizer,
    )

    train_loader = make_loader(
        normalized_train,
        batch_size=batch_size,
        shuffle=True,
    )

    validation_loader = make_loader(
        normalized_validation,
        batch_size=batch_size,
        shuffle=False,
    )

    # --------------------------------------------------------
    # Initialize model and optimizer.
    # --------------------------------------------------------

    model = C3StandardGRU(
        hidden_size=HIDDEN_SIZE,
        num_layers=NUM_LAYERS,
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=learning_rate,
    )

    parameter_count = sum(
        parameter.numel()
        for parameter in model.parameters()
    )

    print("Trainable parameters:", parameter_count)

    # --------------------------------------------------------
    # Training loop.
    # --------------------------------------------------------

    history = []

    best_validation_mae = float("inf")
    best_epoch = 0
    epochs_without_improvement = 0

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    checkpoint_path = (
        output_dir / f"gru_{horizon}min.pt"
    )

    for epoch in range(1, max_epochs + 1):
        training_metrics = run_epoch(
            model,
            train_loader,
            device,
            optimizer,
        )

        validation_metrics = run_epoch(
            model,
            validation_loader,
            device,
            optimizer=None,
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
            f"Val MAE: {validation_metrics['mae']:.4f} | "
            f"Val RMSE: {validation_metrics['rmse']:.4f}",
            flush=True,
        )

        if validation_metrics["mae"] < best_validation_mae:
            best_validation_mae = (
                validation_metrics["mae"]
            )

            best_epoch = epoch

            epochs_without_improvement = 0

            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "horizon_minutes": horizon,
                    "input_size": model.input_size,
                    "hidden_size": HIDDEN_SIZE,
                    "num_layers": NUM_LAYERS,
                    "normalizer": normalizer.to_dict(),
                    "seed": SEED,
                    "best_epoch": best_epoch,
                    "validation_metrics": validation_metrics,
                },
                checkpoint_path,
            )

        else:
            epochs_without_improvement += 1

        if epochs_without_improvement >= patience:
            print(
                f"\nEarly stopping at epoch {epoch}."
            )
            break

    # --------------------------------------------------------
    # Save experiment metadata.
    # --------------------------------------------------------

    result = {
        "model": "standard_gru",
        "dataset_version": "c3-fixed-horizon-v2",
        "target_feature": "soil_moisture_pct",
        "horizon_minutes": horizon,
        "device": str(device),
        "seed": SEED,
        "train_examples": len(train_dataset),
        "validation_examples": len(validation_dataset),
        "parameter_count": parameter_count,
        "configuration": {
            "input_size": model.input_size,
            "hidden_size": HIDDEN_SIZE,
            "num_layers": NUM_LAYERS,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "max_epochs": max_epochs,
            "patience": patience,
            "optimizer": "Adam",
            "loss": "MSE",
            "selection_metric": "validation_mae",
        },
        "best_epoch": best_epoch,
        "best_validation_mae": best_validation_mae,
        "history": history,
        "checkpoint": checkpoint_path.name,
        "created_at": datetime.now(
            UTC
        ).isoformat(),
    }

    metrics_path = (
        output_dir / f"gru_{horizon}min_metrics.json"
    )

    metrics_path.write_text(
        json.dumps(
            result,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n=== TRAINING COMPLETE ===")
    print("Best epoch:", best_epoch)
    print(
        "Best validation MAE:",
        round(best_validation_mae, 4),
    )
    print("Checkpoint:", checkpoint_path)
    print("Metrics:", metrics_path)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train GeoNex C3 standard GRU"
    )

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
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        max_epochs=args.max_epochs,
        patience=args.patience,
        device_name=args.device,
    )


if __name__ == "__main__":
    main()