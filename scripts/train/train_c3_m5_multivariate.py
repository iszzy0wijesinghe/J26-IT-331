"""
GeoNex C3 - M5 Multivariate GRU Training
========================================

Development 07: Reference-Aligned Variable-Rate Training

Features:
- Fresh M5 GRU initialization
- Episode-isolated train/validation/test splitting
- Training-only normalization
- Variable-rate sampling interval audit
- Correct interval attribution to starting operating mode
- Optional high-resolution reference timeline
- Reference-aligned 15/30/60-minute targets
- Masked multi-horizon MSE loss
- Early stopping
- Gradient clipping
- Per-horizon and per-sensor evaluation
- Model checkpoint and training metadata
- Dataset provenance tracking
- Apple Silicon MPS / CUDA / CPU support

IMPORTANT:
This script supports experimental environmental forecasting.

Synthetic training data does not establish real-world
landslide forecasting accuracy.

Existing M0-M4 models and checkpoints are not modified.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

from torch import nn
from torch.utils.data import DataLoader, Dataset

from components.c3_forecasting.models.m5_multivariate_gru import (
    C3M5MultivariateGRU,
    FORECAST_HORIZONS,
    OPERATING_MODES,
    SENSOR_FEATURES,
)

from components.c3_forecasting.preprocessing.m5_dataset import (
    M5DatasetConfig,
    build_m5_training_samples,
)

from components.c3_forecasting.preprocessing.m5_scaler import (
    M5SensorScaler,
)

from components.c3_forecasting.preprocessing.m5_features import (
    parse_utc_timestamp,
)

from components.c3_forecasting.preprocessing.m5_reference_dataset import (
    build_reference_aligned_samples,
)


# ============================================================
# CONFIGURATION
# ============================================================

SEED = 42

MODEL_VERSION = "M5_MULTIVARIATE_GRU"

RESEARCH_STATUS = "EXPERIMENTAL"

EXPECTED_INTERVALS = {
    "DEEP_SLEEP": (900, 1500),
    "IDLE": (420, 720),
    "RISK": (120, 240),
    "WARNING": (30, 90),
    "EMERGENCY": (8, 25),
}


# ============================================================
# REPRODUCIBILITY
# ============================================================

def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)

    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ============================================================
# FILE UTILITIES
# ============================================================

def calculate_file_hash(path: Path) -> str:
    """
    Calculate SHA-256 for dataset provenance.
    """

    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def save_json(path: Path, data):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            data,
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )


# ============================================================
# DATA LOADING
# ============================================================

def load_observations(path: Path):
    """
    Load C3 observations or reference timeline.

    Supports:
    - Standard C3 CSV exports
    - Synthetic variable-rate observations
    - High-resolution reference timeline

    Missing sensor values become None.
    Invalid non-finite values are rejected.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}"
        )

    observations = []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        required = {
            "device_id",
            "episode_id",
            "timestamp",
            "operating_mode",
            *SENSOR_FEATURES,
        }

        missing = required - set(
            reader.fieldnames or []
        )

        if missing:
            raise ValueError(
                f"Missing CSV columns: {sorted(missing)}"
            )

        for row_number, row in enumerate(
            reader,
            start=2,
        ):

            mode = row["operating_mode"]

            if mode not in OPERATING_MODES:
                raise ValueError(
                    f"Unknown operating mode at "
                    f"row {row_number}: {mode}"
                )

            timestamp = row["timestamp"]

            parse_utc_timestamp(timestamp)

            observation = {
                "dataset_id": (
                    row.get("dataset_id")
                    or path.stem
                ),
                "device_id": row["device_id"],
                "episode_id": row["episode_id"],
                "timestamp": timestamp,
                "operating_mode": mode,
            }

            for sensor in SENSOR_FEATURES:

                value = row.get(sensor)

                if value in (None, ""):
                    observation[sensor] = None
                    continue

                numeric_value = float(value)

                if not math.isfinite(numeric_value):
                    raise ValueError(
                        f"Non-finite {sensor} at "
                        f"row {row_number}"
                    )

                observation[sensor] = numeric_value

            observations.append(observation)

    if not observations:
        raise ValueError(
            f"Dataset is empty: {path}"
        )

    return observations


# ============================================================
# EPISODE GROUPING
# ============================================================

def group_observations(observations):

    groups = defaultdict(list)

    for observation in observations:

        key = (
            observation["dataset_id"],
            observation["device_id"],
            observation["episode_id"],
        )

        groups[key].append(observation)

    for key, group in groups.items():

        group.sort(
            key=lambda row: parse_utc_timestamp(
                row["timestamp"]
            )
        )

        previous_timestamp = None

        for row in group:

            timestamp = parse_utc_timestamp(
                row["timestamp"]
            )

            if (
                previous_timestamp is not None
                and timestamp <= previous_timestamp
            ):
                raise ValueError(
                    f"Duplicate or non-increasing "
                    f"timestamp in episode {key}"
                )

            previous_timestamp = timestamp

    return groups


# ============================================================
# VARIABLE-RATE SAMPLING AUDIT
# ============================================================

def audit_sampling_intervals(groups):
    """
    Audit sampling intervals by operating mode.

    IMPORTANT CORRECTION:

    The interval from observation A to observation B
    is scheduled using the mode recorded at A.

    Therefore, attribute the interval to A's mode,
    not B's mode.

    This matches the current synthetic simulator's
    sampling scheduler.
    """

    intervals = defaultdict(list)

    for group in groups.values():

        for previous, current in zip(
            group[:-1],
            group[1:],
        ):

            previous_time = parse_utc_timestamp(
                previous["timestamp"]
            )

            current_time = parse_utc_timestamp(
                current["timestamp"]
            )

            delta_seconds = (
                current_time - previous_time
            ).total_seconds()

            if delta_seconds <= 0:
                raise ValueError(
                    "Non-positive sampling interval"
                )

            # Correct attribution:
            # The previous mode schedules this interval.
            mode = previous["operating_mode"]

            intervals[mode].append(delta_seconds)

    result = {}

    for mode in OPERATING_MODES:

        values = intervals.get(mode, [])

        if not values:

            result[mode] = {
                "count": 0,
                "median_seconds": None,
                "minimum_seconds": None,
                "maximum_seconds": None,
                "within_expected_range_pct": None,
            }

            continue

        values_array = np.asarray(
            values,
            dtype=np.float64,
        )

        lower, upper = EXPECTED_INTERVALS[mode]

        within_range = (
            (values_array >= lower)
            & (values_array <= upper)
        )

        result[mode] = {
            "count": len(values),
            "median_seconds": float(
                np.median(values_array)
            ),
            "minimum_seconds": float(
                np.min(values_array)
            ),
            "maximum_seconds": float(
                np.max(values_array)
            ),
            "within_expected_range_pct": float(
                np.mean(within_range) * 100.0
            ),
        }

    return result


# ============================================================
# OPERATING MODE DISTRIBUTION
# ============================================================

def calculate_mode_distribution(observations):

    counts = {
        mode: 0
        for mode in OPERATING_MODES
    }

    for observation in observations:
        counts[observation["operating_mode"]] += 1

    return counts


# ============================================================
# EPISODE-ISOLATED SPLITTING
# ============================================================

def split_episode_groups(
    groups,
    seed=SEED,
):
    """
    Split complete episodes before generating windows.

    Prevents rolling-window leakage across
    train/validation/test partitions.

    Does not guarantee independence when the source
    generator produces near-duplicate episodes.
    """

    keys = sorted(groups.keys())

    if len(keys) < 5:
        raise ValueError(
            "At least five episode groups are "
            "required for this split."
        )

    rng = random.Random(seed)

    rng.shuffle(keys)

    total = len(keys)

    train_count = int(total * 0.70)
    validation_count = int(total * 0.15)

    train_keys = keys[:train_count]

    validation_keys = keys[
        train_count:
        train_count + validation_count
    ]

    test_keys = keys[
        train_count + validation_count:
    ]

    if not all(
        (
            train_keys,
            validation_keys,
            test_keys,
        )
    ):
        raise ValueError(
            "Empty training, validation, "
            "or test partition."
        )

    def flatten(selected_keys):

        return [
            observation
            for key in selected_keys
            for observation in groups[key]
        ]

    manifest = {
        "train_groups": [
            list(key)
            for key in train_keys
        ],
        "validation_groups": [
            list(key)
            for key in validation_keys
        ],
        "test_groups": [
            list(key)
            for key in test_keys
        ],
    }

    return (
        flatten(train_keys),
        flatten(validation_keys),
        flatten(test_keys),
        manifest,
    )


# ============================================================
# TORCH DATASET
# ============================================================

class M5TorchDataset(Dataset):

    def __init__(
        self,
        samples,
        scaler,
    ):
        self.samples = samples
        self.scaler = scaler

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):

        sample = self.samples[index]

        features = self.scaler.transform_features(
            sample.features
        )

        targets = self.scaler.transform_targets(
            sample.targets,
            sample.target_mask,
        )

        return {
            "features": np.asarray(
                features,
                dtype=np.float32,
            ),
            "targets": np.asarray(
                targets,
                dtype=np.float32,
            ),
            "target_mask": np.asarray(
                sample.target_mask,
                dtype=np.float32,
            ),
            "length": sample.sequence_length,
        }


# ============================================================
# VARIABLE-LENGTH BATCH COLLATION
# ============================================================

def collate_batch(batch):

    max_length = max(
        item["length"]
        for item in batch
    )

    feature_count = batch[0]["features"].shape[1]

    features = np.zeros(
        (
            len(batch),
            max_length,
            feature_count,
        ),
        dtype=np.float32,
    )

    targets = []
    masks = []
    lengths = []

    for index, item in enumerate(batch):

        length = item["length"]

        features[index, :length] = (
            item["features"]
        )

        targets.append(item["targets"])
        masks.append(item["target_mask"])
        lengths.append(length)

    return {
        "features": torch.from_numpy(features),
        "targets": torch.from_numpy(
            np.stack(targets)
        ),
        "masks": torch.from_numpy(
            np.stack(masks)
        ),
        "lengths": torch.tensor(
            lengths,
            dtype=torch.long,
        ),
    }


# ============================================================
# MASKED LOSS
# ============================================================

def masked_mse(
    predictions,
    targets,
    masks,
):

    squared_error = (
        predictions - targets
    ) ** 2

    masked_error = squared_error * masks

    denominator = masks.sum().clamp(
        min=1.0
    )

    return masked_error.sum() / denominator


# ============================================================
# MODEL FORWARD
# ============================================================

def forward_model(
    model,
    batch,
    device,
):

    features = batch["features"].to(device)

    lengths = batch["lengths"].to(device)

    return model(
        features,
        lengths,
    )


# ============================================================
# TRAINING / VALIDATION EPOCH
# ============================================================

def run_epoch(
    model,
    loader,
    optimizer,
    device,
):

    training = optimizer is not None

    model.train(training)

    total_squared_error = 0.0
    total_valid_values = 0.0

    for batch in loader:

        targets = batch["targets"].to(device)
        masks = batch["masks"].to(device)

        valid_count = float(
            masks.sum().item()
        )

        if valid_count == 0:
            continue

        with torch.set_grad_enabled(training):

            predictions = forward_model(
                model,
                batch,
                device,
            )

            loss = masked_mse(
                predictions,
                targets,
                masks,
            )

            if training:

                optimizer.zero_grad()

                loss.backward()

                nn.utils.clip_grad_norm_(
                    model.parameters(),
                    max_norm=1.0,
                )

                optimizer.step()

        total_squared_error += (
            float(loss.item()) * valid_count
        )

        total_valid_values += valid_count

    if total_valid_values == 0:
        raise RuntimeError(
            "No valid target values in epoch."
        )

    return (
        total_squared_error / total_valid_values
    )


# ============================================================
# MODEL EVALUATION
# ============================================================

@torch.no_grad()
def evaluate_model(
    model,
    loader,
    scaler,
    device,
):

    model.eval()

    predictions_all = []
    targets_all = []
    masks_all = []

    for batch in loader:

        predictions = forward_model(
            model,
            batch,
            device,
        )

        predictions_all.append(
            predictions.cpu().numpy()
        )

        targets_all.append(
            batch["targets"].numpy()
        )

        masks_all.append(
            batch["masks"].numpy()
        )

    if not predictions_all:
        raise RuntimeError(
            "Evaluation dataset is empty."
        )

    predictions = np.concatenate(
        predictions_all,
        axis=0,
    )

    targets = np.concatenate(
        targets_all,
        axis=0,
    )

    masks = np.concatenate(
        masks_all,
        axis=0,
    )

    predictions = scaler.inverse_transform_targets(
        predictions
    )

    targets = scaler.inverse_transform_targets(
        targets
    )

    metrics = {}

    for horizon_index, horizon in enumerate(
        FORECAST_HORIZONS
    ):

        horizon_metrics = {}

        for sensor_index, sensor in enumerate(
            SENSOR_FEATURES
        ):

            valid = (
                masks[
                    :,
                    horizon_index,
                    sensor_index,
                ] > 0
            )

            count = int(valid.sum())

            if count == 0:

                horizon_metrics[sensor] = {
                    "count": 0,
                    "mae": None,
                    "rmse": None,
                }

                continue

            actual = targets[
                valid,
                horizon_index,
                sensor_index,
            ]

            predicted = predictions[
                valid,
                horizon_index,
                sensor_index,
            ]

            errors = predicted - actual

            horizon_metrics[sensor] = {
                "count": count,
                "mae": float(
                    np.mean(np.abs(errors))
                ),
                "rmse": float(
                    np.sqrt(
                        np.mean(errors ** 2)
                    )
                ),
            }

        metrics[str(horizon)] = horizon_metrics

    return metrics


# ============================================================
# REFERENCE DATA FILTERING
# ============================================================

def filter_reference_by_groups(
    reference_observations,
    selected_observations,
):
    """
    Restrict reference targets to the selected
    train/validation/test episode keys.

    Reference values are labels only.
    They never enter the model input features.
    """

    selected_keys = {
        (
            row["dataset_id"],
            row["device_id"],
            row["episode_id"],
        )
        for row in selected_observations
    }

    return [
        row
        for row in reference_observations
        if (
            row["dataset_id"],
            row["device_id"],
            row["episode_id"],
        ) in selected_keys
    ]


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "GeoNex C3 M5 Multivariate GRU Training"
        )
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Variable-rate observation CSV",
    )

    parser.add_argument(
        "--reference",
        default=None,
        help=(
            "Optional high-resolution reference CSV "
            "for future-target alignment"
        ),
    )

    parser.add_argument(
        "--output-dir",
        default=(
            "artifacts/c3/experiments/"
            "m5_fresh_training"
        ),
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=30,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.001,
    )

    parser.add_argument(
        "--patience",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=SEED,
    )

    args = parser.parse_args()

    if args.epochs < 1:
        parser.error("--epochs must be >= 1")

    if args.batch_size < 1:
        parser.error("--batch-size must be >= 1")

    if args.patience < 1:
        parser.error("--patience must be >= 1")

    if args.learning_rate <= 0:
        parser.error("--learning-rate must be > 0")

    set_seed(args.seed)

    input_path = Path(args.input)

    reference_path = (
        Path(args.reference)
        if args.reference
        else None
    )

    output_dir = Path(args.output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    checkpoint_path = (
        output_dir / "m5_multivariate_gru.pt"
    )

    report_path = (
        output_dir / "training_report.json"
    )

    # --------------------------------------------------------
    # 1. LOAD OBSERVATIONS
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("GEONEX C3 - M5 MULTIVARIATE TRAINING")
    print("=" * 60)

    print("\n[1/10] Loading observations...")

    observations = load_observations(
        input_path
    )

    groups = group_observations(
        observations
    )

    print(
        f"Observations: {len(observations):,}"
    )

    print(
        f"Episode groups: {len(groups)}"
    )

    # --------------------------------------------------------
    # 2. LOAD OPTIONAL REFERENCE TIMELINE
    # --------------------------------------------------------

    print("\n[2/10] Loading reference timeline...")

    reference_observations = None

    if reference_path is not None:

        reference_observations = load_observations(
            reference_path
        )

        print(
            "Reference observations:",
            f"{len(reference_observations):,}",
        )

        target_source = "REFERENCE_TIMELINE"

    else:

        print(
            "No reference supplied. "
            "Using observation-aligned targets."
        )

        target_source = "SAMPLED_OBSERVATIONS"

    # --------------------------------------------------------
    # 3. AUDIT SAMPLING INTERVALS
    # --------------------------------------------------------

    print("\n[3/10] Auditing sampling intervals...")

    sampling_audit = audit_sampling_intervals(
        groups
    )

    mode_distribution = calculate_mode_distribution(
        observations
    )

    print("\nOperating mode distribution:")

    print(
        json.dumps(
            mode_distribution,
            indent=2,
        )
    )

    print("\nSampling interval audit:")

    print(
        json.dumps(
            sampling_audit,
            indent=2,
        )
    )

    missing_modes = [
        mode
        for mode, count in mode_distribution.items()
        if count == 0
    ]

    if missing_modes:

        print(
            "\nWARNING: Missing operating modes:",
            missing_modes,
        )

    # --------------------------------------------------------
    # 4. SPLIT EPISODES
    # --------------------------------------------------------

    print("\n[4/10] Splitting independent episodes...")

    (
        train_observations,
        validation_observations,
        test_observations,
        split_manifest,
    ) = split_episode_groups(
        groups,
        seed=args.seed,
    )

    print(
        "Train observations:",
        len(train_observations),
    )

    print(
        "Validation observations:",
        len(validation_observations),
    )

    print(
        "Test observations:",
        len(test_observations),
    )

    # --------------------------------------------------------
    # 5. BUILD TRAINING SAMPLES
    # --------------------------------------------------------

    print("\n[5/10] Building training samples...")

    dataset_config = M5DatasetConfig(
        sequence_length=32,
        minimum_sequence_length=3,
        target_tolerance_minutes=3.0,
        minimum_valid_targets=1,
        require_all_horizons=False,
    )

    if reference_observations is not None:

        print(
            "Target source: high-resolution "
            "reference timeline"
        )

        train_reference = filter_reference_by_groups(
            reference_observations,
            train_observations,
        )

        validation_reference = filter_reference_by_groups(
            reference_observations,
            validation_observations,
        )

        test_reference = filter_reference_by_groups(
            reference_observations,
            test_observations,
        )

        print(
            "Train reference rows:",
            len(train_reference),
        )

        print(
            "Validation reference rows:",
            len(validation_reference),
        )

        print(
            "Test reference rows:",
            len(test_reference),
        )

        train_samples = build_reference_aligned_samples(
            train_observations,
            train_reference,
            dataset_config,
        )

        validation_samples = build_reference_aligned_samples(
            validation_observations,
            validation_reference,
            dataset_config,
        )

        test_samples = build_reference_aligned_samples(
            test_observations,
            test_reference,
            dataset_config,
        )

    else:

        print(
            "Target source: sampled observations"
        )

        train_samples = build_m5_training_samples(
            train_observations,
            dataset_config,
        )

        validation_samples = build_m5_training_samples(
            validation_observations,
            dataset_config,
        )

        test_samples = build_m5_training_samples(
            test_observations,
            dataset_config,
        )

    print(
        f"Train samples: {len(train_samples):,}"
    )

    print(
        f"Validation samples: "
        f"{len(validation_samples):,}"
    )

    print(
        f"Test samples: {len(test_samples):,}"
    )

    if not all(
        (
            train_samples,
            validation_samples,
            test_samples,
        )
    ):
        raise RuntimeError(
            "Training, validation, or test "
            "samples are empty."
        )

    # --------------------------------------------------------
    # 6. FIT TRAINING-ONLY SCALER
    # --------------------------------------------------------

    print("\n[6/10] Fitting training-only scaler...")

    scaler = M5SensorScaler().fit(
        [
            sample.features
            for sample in train_samples
        ]
    )

    train_dataset = M5TorchDataset(
        train_samples,
        scaler,
    )

    validation_dataset = M5TorchDataset(
        validation_samples,
        scaler,
    )

    test_dataset = M5TorchDataset(
        test_samples,
        scaler,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collate_batch,
    )

    validation_loader = DataLoader(
        validation_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=collate_batch,
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=collate_batch,
    )

    # --------------------------------------------------------
    # 7. INITIALIZE FRESH MODEL
    # --------------------------------------------------------

    print("\n[7/10] Initializing fresh M5 model...")

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "mps"
        if torch.backends.mps.is_available()
        else "cpu"
    )

    print(f"Training device: {device}")

    # Fresh initialization.
    # No previous checkpoint is loaded.
    model = C3M5MultivariateGRU()

    model = model.to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=1e-4,
    )

    # --------------------------------------------------------
    # 8. TRAIN MODEL
    # --------------------------------------------------------

    print("\n[8/10] Starting training...\n")

    best_validation_loss = float("inf")

    patience_counter = 0

    training_history = []

    for epoch in range(
        1,
        args.epochs + 1,
    ):

        train_loss = run_epoch(
            model,
            train_loader,
            optimizer,
            device,
        )

        validation_loss = run_epoch(
            model,
            validation_loader,
            None,
            device,
        )

        if not math.isfinite(validation_loss):
            raise RuntimeError(
                "Non-finite validation loss. "
                "Training stopped."
            )

        print(
            f"Epoch {epoch:03d} | "
            f"Train MSE: {train_loss:.6f} | "
            f"Validation MSE: "
            f"{validation_loss:.6f}"
        )

        training_history.append({
            "epoch": epoch,
            "train_mse": train_loss,
            "validation_mse": validation_loss,
        })

        if validation_loss < best_validation_loss:

            best_validation_loss = validation_loss

            patience_counter = 0

            checkpoint = {
                "model_state_dict": (
                    model.state_dict()
                ),
                "scaler": scaler.to_dict(),
                "model_version": MODEL_VERSION,
                "sensor_features": list(
                    SENSOR_FEATURES
                ),
                "forecast_horizons": list(
                    FORECAST_HORIZONS
                ),
                "operating_modes": list(
                    OPERATING_MODES
                ),
                "seed": args.seed,
                "training_epoch": epoch,
                "validation_mse": validation_loss,
                "research_status": RESEARCH_STATUS,
                "target_source": target_source,
                "input_dataset": str(input_path),
                "reference_dataset": (
                    str(reference_path)
                    if reference_path
                    else None
                ),
                "dataset_approved_for_research": False,
            }

            torch.save(
                checkpoint,
                checkpoint_path,
            )

            print(
                "  Saved improved checkpoint."
            )

        else:

            patience_counter += 1

            if patience_counter >= args.patience:

                print(
                    "\nEarly stopping activated."
                )

                break

    # --------------------------------------------------------
    # 9. EVALUATE BEST CHECKPOINT
    # --------------------------------------------------------

    print("\n[9/10] Evaluating best checkpoint...")

    checkpoint = torch.load(
        checkpoint_path,
        map_location=device,
        weights_only=True,
    )

    model.load_state_dict(
        checkpoint["model_state_dict"]
    )

    test_metrics = evaluate_model(
        model,
        test_loader,
        scaler,
        device,
    )

    print("\nTest evaluation completed.")

    # --------------------------------------------------------
    # 10. SAVE TRAINING REPORT
    # --------------------------------------------------------

    print("\n[10/10] Saving training report...")

    input_hash = calculate_file_hash(
        input_path
    )

    reference_hash = (
        calculate_file_hash(reference_path)
        if reference_path
        else None
    )

    report = {
        "model": MODEL_VERSION,
        "status": RESEARCH_STATUS,
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "dataset_approved_for_research": False,
        "target_source": target_source,
        "input_dataset": str(input_path),
        "input_sha256": input_hash,
        "reference_dataset": (
            str(reference_path)
            if reference_path
            else None
        ),
        "reference_sha256": reference_hash,
        "total_observations": len(observations),
        "total_episode_groups": len(groups),
        "train_samples": len(train_samples),
        "validation_samples": len(
            validation_samples
        ),
        "test_samples": len(test_samples),
        "best_epoch": checkpoint["training_epoch"],
        "best_validation_mse": (
            best_validation_loss
        ),
        "mode_distribution": mode_distribution,
        "missing_modes": missing_modes,
        "sampling_interval_audit": sampling_audit,
        "split_manifest": split_manifest,
        "training_history": training_history,
        "test_metrics": test_metrics,
        "training_configuration": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "patience": args.patience,
            "seed": args.seed,
            "sequence_length": (
                dataset_config.sequence_length
            ),
            "forecast_horizons": list(
                FORECAST_HORIZONS
            ),
            "sensor_features": list(
                SENSOR_FEATURES
            ),
        },
        "limitations": [
            "Synthetic engineering data is not "
            "independently validated landslide data.",
            "Episode-isolated splitting does not "
            "guarantee independent environmental "
            "patterns across simulated episodes.",
            "The model predicts sensor values, "
            "not verified landslide events.",
            "Forecasting beyond validated horizons "
            "is unsupported.",
        ],
    }

    save_json(
        report_path,
        report,
    )

    print("\n" + "=" * 60)
    print("M5 TRAINING COMPLETED")
    print("=" * 60)

    print(
        f"Best epoch: "
        f"{checkpoint['training_epoch']}"
    )

    print(
        f"Best validation MSE: "
        f"{best_validation_loss:.6f}"
    )

    print(
        f"Checkpoint: {checkpoint_path}"
    )

    print(
        f"Training report: {report_path}"
    )

    print(
        "\nResearch status: EXPERIMENTAL"
    )

    print(
        "Production deployment: NOT APPROVED"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()