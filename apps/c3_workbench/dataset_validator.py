"""Validation of GeoNex C3 forecast-ready synthetic datasets.

This validator accepts the C3 fixed-horizon V2 dataset format.

Only the following dataset files are accessed:

    manifest.json
    train.jsonl.gz
    validation.jsonl.gz

The held-out test split is deliberately excluded.

Validation includes:
    - Dataset provenance and manifest compatibility
    - SHA-256 file integrity
    - Forecast target validation
    - M4 temporal feature compatibility
    - Bounded gzip decompression
    - Bounded JSONL record reading
    - Forecast horizon counts
    - Episode-disjoint train/validation splitting

IMPORTANT:
    Passing validation establishes dataset structural compatibility,
    not real-world forecasting performance or landslide-warning validity.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from components.c3_forecasting.preprocessing.m4_features import (
    M4_INPUT_FEATURE_COUNT,
    extract_m4_sequence,
)


# ============================================================
# Supported dataset configuration
# ============================================================

SUPPORTED_HORIZONS = {15, 30, 60}

REQUIRED_SPLITS = (
    "train",
    "validation",
)

VALID_MODES = {
    "DEEP_SLEEP",
    "IDLE",
    "RISK",
    "WARNING",
}

EXPECTED_EXPORT_VERSION = "c3-fixed-horizon-v2"
EXPECTED_SOURCE_VERSION = "c3-synthetic-v2"
EXPECTED_SOURCE_ORIGIN = "SIMULATED"
EXPECTED_TARGET_FEATURE = "soil_moisture_pct"
EXPECTED_TRAINING_OBJECTIVE = "FUTURE_SENSOR_VALUE_REGRESSION"
EXPECTED_SPLIT_POLICY = "EPISODE_DISJOINT"


# ============================================================
# Resource limits
# ============================================================

# Maximum manifest size: 1 MiB
MAX_MANIFEST_BYTES = 1 * 1024**2

# Maximum JSONL record size: 2 MiB
MAX_JSONL_LINE_BYTES = 2 * 1024**2

# Maximum decompressed size per split: 1 GiB
#
# Existing C3 V2 dataset measurements:
#
# Training:
#   Compressed:   ~19.08 MiB
#   Decompressed: ~764.51 MiB
#
# Validation:
#   Compressed:   ~3.50 MiB
#   Decompressed: ~141.41 MiB
#
# A 1 GiB per-split limit accommodates the existing dataset.
MAX_DECOMPRESSED_SPLIT_BYTES = 1024**3

# Maximum number of examples per split.
MAX_RECORDS_PER_SPLIT = 100_000

# Bounded hashing buffer.
HASH_CHUNK_BYTES = 1024 * 1024


# ============================================================
# Exceptions
# ============================================================

class C3DatasetValidationError(ValueError):
    """Raised when a C3 forecasting dataset is invalid."""


# ============================================================
# File integrity
# ============================================================

def calculate_sha256(path: Path) -> str:
    """Calculate the SHA-256 digest of a file using bounded reads."""

    digest = hashlib.sha256()

    try:
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(HASH_CHUNK_BYTES)

                if not chunk:
                    break

                digest.update(chunk)

    except OSError as exc:
        raise C3DatasetValidationError(
            f"Cannot calculate SHA-256 for {path.name}: {exc}"
        ) from exc

    return digest.hexdigest()


# ============================================================
# Manifest validation
# ============================================================

def load_manifest(dataset_dir: Path) -> dict[str, Any]:
    """Read and validate a C3 fixed-horizon V2 manifest."""

    dataset_dir = Path(dataset_dir)

    manifest_path = dataset_dir / "manifest.json"

    if not manifest_path.is_file():
        raise C3DatasetValidationError(
            "Dataset manifest.json is missing"
        )

    try:
        manifest_size = manifest_path.stat().st_size

    except OSError as exc:
        raise C3DatasetValidationError(
            "Cannot inspect dataset manifest"
        ) from exc

    if manifest_size > MAX_MANIFEST_BYTES:
        raise C3DatasetValidationError(
            "Dataset manifest exceeds the 1 MiB limit"
        )

    try:
        with manifest_path.open("rb") as stream:
            raw_manifest = stream.read(MAX_MANIFEST_BYTES + 1)

        if len(raw_manifest) > MAX_MANIFEST_BYTES:
            raise C3DatasetValidationError(
                "Dataset manifest exceeds the 1 MiB limit"
            )

        manifest = json.loads(raw_manifest.decode("utf-8"))

    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise C3DatasetValidationError(
            f"Cannot read dataset manifest: {exc}"
        ) from exc

    if not isinstance(manifest, dict):
        raise C3DatasetValidationError(
            "Manifest must be a JSON object"
        )

    # --------------------------------------------------------
    # Dataset identity and provenance
    # --------------------------------------------------------

    if manifest.get("export_version") != EXPECTED_EXPORT_VERSION:
        raise C3DatasetValidationError(
            "Unsupported dataset export version"
        )

    if manifest.get("source_dataset_version") != EXPECTED_SOURCE_VERSION:
        raise C3DatasetValidationError(
            "Unsupported source dataset version"
        )

    if manifest.get("source_origin") != EXPECTED_SOURCE_ORIGIN:
        raise C3DatasetValidationError(
            "Only simulated C3 datasets are supported"
        )

    if manifest.get("target_feature") != EXPECTED_TARGET_FEATURE:
        raise C3DatasetValidationError(
            "Unsupported forecast target"
        )

    if (
        manifest.get("training_objective")
        != EXPECTED_TRAINING_OBJECTIVE
    ):
        raise C3DatasetValidationError(
            "Unsupported training objective"
        )

    if manifest.get("split_policy") != EXPECTED_SPLIT_POLICY:
        raise C3DatasetValidationError(
            "Expected episode-disjoint dataset splitting"
        )

    # --------------------------------------------------------
    # Research limitations
    # --------------------------------------------------------

    if manifest.get("not_field_data") is not True:
        raise C3DatasetValidationError(
            "Synthetic-data provenance disclaimer is required"
        )

    if manifest.get("not_landslide_ground_truth") is not True:
        raise C3DatasetValidationError(
            "Landslide ground-truth disclaimer is required"
        )

    # --------------------------------------------------------
    # Forecast horizons
    # --------------------------------------------------------

    horizons = manifest.get("forecast_horizons_minutes")

    if horizons != [15, 30, 60]:
        raise C3DatasetValidationError(
            "Unsupported forecast horizon configuration"
        )

    # --------------------------------------------------------
    # Temporal history configuration
    # --------------------------------------------------------

    if manifest.get("minimum_history_steps") != 3:
        raise C3DatasetValidationError(
            "Expected minimum history length of 3 steps"
        )

    if manifest.get("maximum_history_steps") != 32:
        raise C3DatasetValidationError(
            "Expected maximum history length of 32 steps"
        )

    # --------------------------------------------------------
    # Required file metadata
    # --------------------------------------------------------

    files = manifest.get("files")

    if not isinstance(files, dict):
        raise C3DatasetValidationError(
            "Manifest files section is invalid"
        )

    for split in REQUIRED_SPLITS:
        file_info = files.get(split)

        if not isinstance(file_info, dict):
            raise C3DatasetValidationError(
                f"Manifest missing file metadata for {split}"
            )

        expected_filename = f"{split}.jsonl.gz"

        if file_info.get("filename") != expected_filename:
            raise C3DatasetValidationError(
                f"Unexpected filename for {split}"
            )

        expected_hash = file_info.get("sha256")

        if (
            not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or any(
                character not in "0123456789abcdef"
                for character in expected_hash
            )
        ):
            raise C3DatasetValidationError(
                f"Invalid SHA-256 digest for {split}"
            )

        expected_count = file_info.get("examples")

        if (
            isinstance(expected_count, bool)
            or not isinstance(expected_count, int)
            or expected_count < 1
            or expected_count > MAX_RECORDS_PER_SPLIT
        ):
            raise C3DatasetValidationError(
                f"Invalid example count for {split}"
            )

    # --------------------------------------------------------
    # Horizon count metadata
    # --------------------------------------------------------

    counts_by_split = manifest.get("counts_by_split_horizon")

    if not isinstance(counts_by_split, dict):
        raise C3DatasetValidationError(
            "Manifest horizon count metadata is missing"
        )

    for split in REQUIRED_SPLITS:
        split_counts = counts_by_split.get(split)

        if not isinstance(split_counts, dict):
            raise C3DatasetValidationError(
                f"Missing horizon counts for {split}"
            )

        for horizon in SUPPORTED_HORIZONS:
            value = split_counts.get(str(horizon))

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise C3DatasetValidationError(
                    f"Invalid {horizon}-minute count for {split}"
                )

        expected_total = sum(
            split_counts[str(horizon)]
            for horizon in SUPPORTED_HORIZONS
        )

        if expected_total != files[split]["examples"]:
            raise C3DatasetValidationError(
                f"Manifest horizon totals do not match {split} examples"
            )

    return manifest


# ============================================================
# Forecast record validation
# ============================================================

def validate_record(
    record: dict[str, Any],
    split: str,
    line_number: int,
) -> tuple[int, str, str, int, int]:
    """Validate one C3 fixed-horizon forecasting example.

    Returns:
        (
            requested_horizon_minutes,
            episode_id,
            device_id,
            sequence_length,
            missing_readings,
        )
    """

    location = f"{split}:{line_number}"

    # --------------------------------------------------------
    # Split identity
    # --------------------------------------------------------

    if record.get("split") != split:
        raise C3DatasetValidationError(
            f"{location}: Record split mismatch"
        )

    # --------------------------------------------------------
    # Episode and device identity
    # --------------------------------------------------------

    episode_id = record.get("episode_id")
    device_id = record.get("device_id")

    if not isinstance(episode_id, str) or not episode_id:
        raise C3DatasetValidationError(
            f"{location}: Invalid episode ID"
        )

    if not isinstance(device_id, str) or not device_id:
        raise C3DatasetValidationError(
            f"{location}: Invalid device ID"
        )

    # --------------------------------------------------------
    # Forecast target
    # --------------------------------------------------------

    target = record.get("target")

    if not isinstance(target, dict):
        raise C3DatasetValidationError(
            f"{location}: Missing or invalid target"
        )

    if target.get("feature") != EXPECTED_TARGET_FEATURE:
        raise C3DatasetValidationError(
            f"{location}: Unsupported target feature"
        )

    horizon = target.get("requested_horizon_minutes")

    if (
        isinstance(horizon, bool)
        or not isinstance(horizon, int)
        or horizon not in SUPPORTED_HORIZONS
    ):
        raise C3DatasetValidationError(
            f"{location}: Invalid forecast horizon"
        )

    target_value = target.get("value")

    if (
        isinstance(target_value, bool)
        or not isinstance(target_value, (int, float))
    ):
        raise C3DatasetValidationError(
            f"{location}: Invalid forecast target value"
        )

    try:
        numeric_target = float(target_value)

    except (ValueError, OverflowError, TypeError) as exc:
        raise C3DatasetValidationError(
            f"{location}: Target cannot be converted to a number"
        ) from exc

    if not math.isfinite(numeric_target):
        raise C3DatasetValidationError(
            f"{location}: Non-finite forecast target"
        )

    # Model training uses float32 tensors.
    if abs(numeric_target) > np.finfo(np.float32).max:
        raise C3DatasetValidationError(
            f"{location}: Target exceeds float32 range"
        )

    # --------------------------------------------------------
    # Temporal input sequence
    # --------------------------------------------------------

    sequence = record.get("input_sequence")

    if not isinstance(sequence, dict):
        raise C3DatasetValidationError(
            f"{location}: Invalid temporal sequence"
        )

    steps = sequence.get("steps")

    if not isinstance(steps, list):
        raise C3DatasetValidationError(
            f"{location}: Temporal steps must be a list"
        )

    if not (3 <= len(steps) <= 32):
        raise C3DatasetValidationError(
            f"{location}: Expected 3–32 temporal steps"
        )

    # --------------------------------------------------------
    # Operating mode validation
    # --------------------------------------------------------

    for step_index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise C3DatasetValidationError(
                f"{location}: Invalid step at index {step_index}"
            )

        operating_mode = step.get("operating_mode")

        if operating_mode not in VALID_MODES:
            raise C3DatasetValidationError(
                f"{location}: Unsupported operating mode "
                f"at step {step_index}"
            )

    # --------------------------------------------------------
    # M4 feature extraction
    # --------------------------------------------------------

    try:
        features = extract_m4_sequence(
            sequence,
            include_time=True,
            include_mode=True,
        )

    except (
        TypeError,
        ValueError,
        KeyError,
        IndexError,
        OverflowError,
        AttributeError,
    ) as exc:
        raise C3DatasetValidationError(
            f"{location}: M4 feature extraction failed: {exc}"
        ) from exc

    expected_shape = (
        len(steps),
        M4_INPUT_FEATURE_COUNT,
    )

    if features.shape != expected_shape:
        raise C3DatasetValidationError(
            f"{location}: Invalid M4 feature dimensions. "
            f"Expected {expected_shape}, got {features.shape}"
        )

    if not np.isfinite(features).all():
        raise C3DatasetValidationError(
            f"{location}: M4 features contain non-finite values"
        )

    # --------------------------------------------------------
    # Missing sensor reading statistics
    # --------------------------------------------------------

    missing_readings = 0

    for step in steps:
        masks = step.get("masks", {})

        if isinstance(masks, dict):
            missing_readings += sum(
                value is not True
                for value in masks.values()
            )

    return (
        horizon,
        episode_id,
        device_id,
        len(steps),
        missing_readings,
    )


# ============================================================
# Bounded JSONL reader
# ============================================================

def _iter_bounded_jsonl(
    path: Path,
    split: str,
):
    """Yield JSONL records with bounded gzip decompression.

    Enforces:
        - Maximum 1 GiB decompressed data per split
        - Maximum 2 MiB per JSONL record
        - Maximum 100,000 lines per split

    Each line is read with a strict upper bound rather than
    allowing an unlimited allocation.
    """

    decompressed_bytes = 0

    try:
        with gzip.open(path, "rb") as stream:
            for line_number in range(1, MAX_RECORDS_PER_SPLIT + 2):

                remaining_bytes = (
                    MAX_DECOMPRESSED_SPLIT_BYTES
                    - decompressed_bytes
                )

                if remaining_bytes < 0:
                    raise C3DatasetValidationError(
                        f"{split}: Decompressed data exceeds 1 GiB"
                    )

                read_limit = min(
                    MAX_JSONL_LINE_BYTES,
                    remaining_bytes,
                ) + 1

                raw_line = stream.readline(read_limit)

                if not raw_line:
                    return

                decompressed_bytes += len(raw_line)

                if (
                    decompressed_bytes
                    > MAX_DECOMPRESSED_SPLIT_BYTES
                ):
                    raise C3DatasetValidationError(
                        f"{split}: Decompressed data exceeds 1 GiB"
                    )

                if len(raw_line) > MAX_JSONL_LINE_BYTES:
                    raise C3DatasetValidationError(
                        f"{split}:{line_number}: "
                        "JSONL record exceeds 2 MiB"
                    )

                # A line that does not end in '\n' is valid only
                # if it is the final record at EOF.
                #
                # peek(1) checks whether additional bytes remain.
                if not raw_line.endswith(b"\n"):
                    if stream.peek(1):
                        raise C3DatasetValidationError(
                            f"{split}:{line_number}: "
                            "JSONL record exceeds the configured limit"
                        )

                if line_number > MAX_RECORDS_PER_SPLIT:
                    raise C3DatasetValidationError(
                        f"{split}: Record count exceeds 100,000"
                    )

                try:
                    line = raw_line.decode("utf-8")

                except UnicodeDecodeError as exc:
                    raise C3DatasetValidationError(
                        f"{split}:{line_number}: Invalid UTF-8"
                    ) from exc

                if not line.strip():
                    continue

                try:
                    record = json.loads(line)

                except json.JSONDecodeError as exc:
                    raise C3DatasetValidationError(
                        f"{split}:{line_number}: Invalid JSON: {exc}"
                    ) from exc

                if not isinstance(record, dict):
                    raise C3DatasetValidationError(
                        f"{split}:{line_number}: Expected JSON object"
                    )

                yield line_number, record

    except (
        OSError,
        EOFError,
    ) as exc:
        raise C3DatasetValidationError(
            f"Cannot read {path.name}: {exc}"
        ) from exc


# ============================================================
# Dataset directory validation
# ============================================================

def validate_dataset_directory(
    dataset_dir: str | Path,
) -> dict[str, Any]:
    """Validate C3 training/validation data.

    The held-out test split is never opened.
    """

    dataset_dir = Path(dataset_dir)

    manifest = load_manifest(dataset_dir)

    split_statistics: dict[str, Any] = {}
    episode_sets: dict[str, set[str]] = {}

    # --------------------------------------------------------
    # Validate only training and validation splits
    # --------------------------------------------------------

    for split in REQUIRED_SPLITS:

        file_info = manifest["files"][split]

        expected_filename = f"{split}.jsonl.gz"

        path = dataset_dir / expected_filename

        if not path.is_file():
            raise C3DatasetValidationError(
                f"Missing dataset split: {expected_filename}"
            )

        # ----------------------------------------------------
        # SHA-256 verification
        # ----------------------------------------------------

        expected_hash = file_info["sha256"]
        actual_hash = calculate_sha256(path)

        if actual_hash != expected_hash:
            raise C3DatasetValidationError(
                f"SHA-256 mismatch for {expected_filename}"
            )

        # ----------------------------------------------------
        # Statistics
        # ----------------------------------------------------

        count = 0

        horizon_counts: Counter[int] = Counter()
        mode_counts: Counter[str] = Counter()
        sequence_lengths: Counter[int] = Counter()

        episodes: set[str] = set()
        devices: set[str] = set()

        missing_readings = 0

        # ----------------------------------------------------
        # Validate forecasting records
        # ----------------------------------------------------

        for line_number, record in _iter_bounded_jsonl(
            path,
            split,
        ):

            (
                horizon,
                episode_id,
                device_id,
                sequence_length,
                missing_count,
            ) = validate_record(
                record,
                split,
                line_number,
            )

            count += 1

            horizon_counts[horizon] += 1
            sequence_lengths[sequence_length] += 1

            episodes.add(episode_id)
            devices.add(device_id)

            missing_readings += missing_count

            for step in record["input_sequence"]["steps"]:
                mode_counts[step["operating_mode"]] += 1

        # ----------------------------------------------------
        # Verify split example counts
        # ----------------------------------------------------

        expected_count = file_info["examples"]

        if count != expected_count:
            raise C3DatasetValidationError(
                f"Record count mismatch for {split}. "
                f"Expected {expected_count}, found {count}"
            )

        # ----------------------------------------------------
        # Verify horizon distributions
        # ----------------------------------------------------

        expected_horizons = manifest[
            "counts_by_split_horizon"
        ][split]

        for horizon in SUPPORTED_HORIZONS:

            expected = expected_horizons[str(horizon)]
            actual = horizon_counts[horizon]

            if expected != actual:
                raise C3DatasetValidationError(
                    f"Horizon count mismatch for "
                    f"{split}/{horizon} minutes. "
                    f"Expected {expected}, found {actual}"
                )

        # ----------------------------------------------------
        # Save split statistics
        # ----------------------------------------------------

        split_statistics[split] = {
            "examples": count,
            "episodes": len(episodes),
            "devices": len(devices),
            "horizon_counts": dict(horizon_counts),
            "mode_step_counts": dict(mode_counts),
            "sequence_length_distribution": dict(
                sequence_lengths
            ),
            "missing_readings": missing_readings,
        }

        episode_sets[split] = episodes

    # ========================================================
    # Episode leakage protection
    # ========================================================

    overlapping_episodes = (
        episode_sets["train"]
        & episode_sets["validation"]
    )

    if overlapping_episodes:
        raise C3DatasetValidationError(
            "Training/validation episode leakage detected: "
            f"{len(overlapping_episodes)} overlapping episodes"
        )

    # ========================================================
    # Validation result
    # ========================================================

    return {
        "status": "VALIDATED",
        "dataset_version": manifest["source_dataset_version"],
        "export_version": manifest["export_version"],
        "source_origin": manifest["source_origin"],
        "target_feature": manifest["target_feature"],
        "forecast_horizons_minutes": manifest[
            "forecast_horizons_minutes"
        ],
        "splits": split_statistics,
        "episode_disjoint": True,
        "held_out_test_accessed": False,
        "warning": (
            "Synthetic telemetry only. "
            "Forecast targets are future sensor values, "
            "not landslide probabilities or validated "
            "safety warnings."
        ),
    }