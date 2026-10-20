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

from components.c3_forecasting.models.standard_gru import C3StandardGRU
from components.c3_forecasting.preprocessing.gru_dataset import (
    C3GRUDataset,
    collate_gru_batch,
    load_gru_split,
)
from components.c3_forecasting.preprocessing.gru_normalization import GRUNormalizer
from components.c3_forecasting.preprocessing.gru_target_normalization import (
    GRUTargetNormalizer,
)

# ============================================================
# Experiment Configuration
# ============================================================

SEED = 20261018

DEFAULT_DATASET_DIR = Path("data/processed/c3_v2")
DEFAULT_OUTPUT_DIR = Path("data/processed/c3_m3_results")

DEFAULT_BATCH_SIZE = 64
DEFAULT_LEARNING_RATE = 0.001
DEFAULT_MAX_EPOCHS = 30
DEFAULT_PATIENCE = 5

HIDDEN_SIZE = 64
NUM_LAYERS = 1

VALID_HORIZONS = frozenset({15, 30, 60})


# ============================================================
# Normalized Dataset Wrapper
# ============================================================

class NormalizedGRUDataset(Dataset):
    """Apply training-fitted sensor normalization to GRU examples."""

    def __init__(
        self,
        source_dataset: C3GRUDataset,
        normalizer: GRUNormalizer,
    ) -> None:
        self.source_dataset = source_dataset
        self.normalizer = normalizer

    def __len__(self) -> int:
        """Return the number of examples."""

        return len(self.source_dataset)

    def __getitem__(
        self,
        index: int,
    ) -> dict:
        """Return a sensor-normalized example."""

        example = self.source_dataset[index]

        return {
            **example,
            "sequence": self.normalizer.transform(
                example["sequence"]
            ),
        }


# ============================================================
# Reproducibility
# ============================================================

def set_seed(seed: int) -> None:
    """Initialize Python, NumPy, and PyTorch random seeds."""

    random.seed(seed)

    np.random.seed(seed)

    torch.manual_seed(seed)

    if torch.backends.mps.is_available():
        torch.mps.manual_seed(seed)


# ============================================================
# Device Selection
# ============================================================

def choose_device(requested: str) -> torch.device:
    """Select CPU or Apple Silicon MPS execution."""

    if requested == "cpu":
        return torch.device("cpu")

    if requested == "mps":
        if not torch.backends.mps.is_available():
            raise RuntimeError(
                "MPS was requested but is unavailable"
            )

        return torch.device("mps")

    if requested == "auto":
        if torch.backends.mps.is_available():
            return torch.device("mps")

        return torch.device("cpu")

    raise ValueError(
        f"Unsupported device: {requested}"
    )


# ============================================================
# DataLoader Construction
# ============================================================

def make_loader(
    dataset: Dataset,
    *,
    batch_size: int,
    shuffle: bool,
) -> DataLoader:
    """Create a variable-length GRU DataLoader."""

    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0,
        collate_fn=collate_gru_batch,
    )


# ============================================================
# Training and Validation Epoch
# ============================================================

def run_epoch(
    model: C3StandardGRU,
    loader: DataLoader,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None,
    target_normalizer: GRUTargetNormalizer,
) -> dict[str, float]:
    """
    Execute one training or validation epoch.

    Training:
        - Normalize target values using training-derived statistics.
        - Calculate MSE loss in standardized target space.
        - Apply gradient clipping.
        - Update model parameters.

    Evaluation:
        - Convert predictions to original soil-moisture units.
        - Calculate MAE and RMSE in percentage points.
        - Do not update model parameters.
    """

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

            # Packed GRU sequence lengths remain on CPU.
            lengths = batch["lengths"]

            targets = batch["targets"].to(device)

            # --------------------------------------------
            # Normalize targets.
            # --------------------------------------------

            normalized_targets = (
                target_normalizer.normalize(targets)
            )

            if training:
                optimizer.zero_grad(
                    set_to_none=True
                )

            # --------------------------------------------
            # Forward pass.
            # --------------------------------------------

            normalized_predictions = model(
                inputs,
                lengths,
            )

            loss = criterion(
                normalized_predictions,
                normalized_targets,
            )

            if not torch.isfinite(loss).item():
                raise RuntimeError(
                    "Non-finite GRU loss encountered"
                )

            # --------------------------------------------
            # Backpropagation.
            # --------------------------------------------

            if training:
                loss.backward()

                torch.nn.utils.clip_grad_norm_(
                    model.parameters(),
                    max_norm=1.0,
                )

                optimizer.step()

            # --------------------------------------------
            # Restore predictions to original units.
            # --------------------------------------------

            predictions = (
                target_normalizer.denormalize(
                    normalized_predictions.detach()
                )
            )

            # Targets are already in original units.
            errors = predictions - targets

            total_absolute_error += (
                errors.abs().sum().item()
            )

            total_squared_error += (
                errors.square().sum().item()
            )

            total_examples += targets.shape[0]

    if total_examples == 0:
        raise ValueError(
            "Cannot calculate metrics for an empty DataLoader"
        )

    mae = (
        total_absolute_error
        / total_examples
    )

    rmse = (
        total_squared_error
        / total_examples
    ) ** 0.5

    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "count": total_examples,
    }


# ============================================================
# Main Training Procedure
# ============================================================

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
    """Train one GeoNex C3 forecasting horizon."""

    # --------------------------------------------------------
    # Validate configuration.
    # --------------------------------------------------------

    if horizon not in VALID_HORIZONS:
        raise ValueError(
            "Horizon must be 15, 30, or 60 minutes"
        )

    if batch_size <= 0:
        raise ValueError(
            "Batch size must be positive"
        )

    if not np.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError(
            "Learning rate must be finite and positive"
        )

    if max_epochs <= 0:
        raise ValueError(
            "Maximum epochs must be positive"
        )

    if patience <= 0:
        raise ValueError(
            "Early stopping patience must be positive"
        )

    # --------------------------------------------------------
    # Initialize experiment.
    # --------------------------------------------------------

    set_seed(SEED)

    device = choose_device(device_name)

    print(
        "\n=== GEONEX C3 M3 STANDARD GRU ==="
    )

    print(
        "Horizon:",
        horizon,
        "minutes",
    )

    print(
        "Device:",
        device,
    )

    print(
        "Random seed:",
        SEED,
    )

    # --------------------------------------------------------
    # Load only training and validation data.
    # --------------------------------------------------------

    print(
        "\nLoading training examples...",
        flush=True,
    )

    train_examples = load_gru_split(
        dataset_dir,
        "train",
    )

    print(
        "Loading validation examples...",
        flush=True,
    )

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

    print(
        "Training examples:",
        len(train_dataset),
    )

    print(
        "Validation examples:",
        len(validation_dataset),
    )

    # --------------------------------------------------------
    # Fit sensor normalization on training data only.
    # --------------------------------------------------------

    print(
        "\nFitting training-only sensor normalizer...",
        flush=True,
    )

    sensor_normalizer = GRUNormalizer.fit(
        train_dataset.examples
    )

    # --------------------------------------------------------
    # Fit target normalization on training data only.
    # --------------------------------------------------------

    print(
        "Fitting training-only target normalizer...",
        flush=True,
    )

    target_normalizer = GRUTargetNormalizer.fit(
        train_dataset.examples
    )

    print(
        "Target mean:",
        round(target_normalizer.mean, 4),
    )

    print(
        "Target std:",
        round(target_normalizer.std, 4),
    )

    # --------------------------------------------------------
    # Prepare normalized datasets.
    # --------------------------------------------------------

    normalized_train = NormalizedGRUDataset(
        train_dataset,
        sensor_normalizer,
    )

    normalized_validation = NormalizedGRUDataset(
        validation_dataset,
        sensor_normalizer,
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
    # Initialize model.
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

    print(
        "\nTrainable parameters:",
        parameter_count,
    )

    # --------------------------------------------------------
    # Training state.
    # --------------------------------------------------------

    history: list[dict] = []

    best_validation_mae = float("inf")
    best_validation_metrics: dict | None = None

    best_epoch = 0
    epochs_without_improvement = 0

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    checkpoint_path = (
        output_dir
        / f"gru_{horizon}min.pt"
    )

    # --------------------------------------------------------
    # Training loop.
    # --------------------------------------------------------

    for epoch in range(
        1,
        max_epochs + 1,
    ):
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
        # Validation-based model selection.
        # ----------------------------------------------------

        if (
            validation_metrics["mae"]
            < best_validation_mae
        ):
            best_validation_mae = (
                validation_metrics["mae"]
            )

            best_validation_metrics = (
                validation_metrics.copy()
            )

            best_epoch = epoch

            epochs_without_improvement = 0

            # Save the best model, not merely the last epoch.
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "horizon_minutes": horizon,
                    "target_feature": "soil_moisture_pct",
                    "dataset_version": "c3-fixed-horizon-v2",
                    "input_size": model.input_size,
                    "hidden_size": HIDDEN_SIZE,
                    "num_layers": NUM_LAYERS,
                    "normalizer": sensor_normalizer.to_dict(),
                    "target_normalizer": (
                        target_normalizer.to_dict()
                    ),
                    "seed": SEED,
                    "best_epoch": best_epoch,
                    "validation_metrics": (
                        best_validation_metrics
                    ),
                },
                checkpoint_path,
            )

            print(
                "  -> Best checkpoint updated.",
                flush=True,
            )

        else:
            epochs_without_improvement += 1

        # ----------------------------------------------------
        # Early stopping.
        # ----------------------------------------------------

        if epochs_without_improvement >= patience:
            print(
                "\nEarly stopping at "
                f"epoch {epoch}.",
                flush=True,
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
            "loss_units": "standardized_target",
            "reported_metric_units": (
                "soil_moisture_percentage_points"
            ),
            "selection_metric": "validation_mae",
        },
        "sensor_normalizer": (
            sensor_normalizer.to_dict()
        ),
        "target_normalizer": (
            target_normalizer.to_dict()
        ),
        "best_epoch": best_epoch,
        "best_validation_mae": best_validation_mae,
        "best_validation_metrics": (
            best_validation_metrics
        ),
        "epochs_completed": len(history),
        "history": history,
        "checkpoint": checkpoint_path.name,
        "created_at": datetime.now(
            UTC
        ).isoformat(),
    }

    metrics_path = (
        output_dir
        / f"gru_{horizon}min_metrics.json"
    )

    metrics_path.write_text(
        json.dumps(
            result,
            indent=2,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # Final summary.
    # --------------------------------------------------------

    print(
        "\n=== TRAINING COMPLETE ==="
    )

    print(
        "Best epoch:",
        best_epoch,
    )

    print(
        "Best validation MAE:",
        round(best_validation_mae, 4),
    )

    if best_validation_metrics is not None:
        print(
            "Best validation RMSE:",
            round(
                best_validation_metrics["rmse"],
                4,
            ),
        )

    print(
        "Checkpoint:",
        checkpoint_path,
    )

    print(
        "Metrics:",
        metrics_path,
    )

    return result


# ============================================================
# Command-Line Interface
# ============================================================

def main() -> None:
    """Parse arguments and launch training."""

    parser = argparse.ArgumentParser(
        description=(
            "Train GeoNex C3 standard GRU forecasting baseline"
        )
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