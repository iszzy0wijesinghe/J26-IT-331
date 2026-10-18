"""Export reproducible C3 V2 synthetic forecasting datasets.

Produces split-specific compressed JSONL files and a manifest containing
dataset provenance, counts, checksums, and experimental limitations.

No ML models are trained by this script.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from components.c3_forecasting.v2_target_builder import (
    build_v2_fixed_horizon_examples,
)

EXPORT_VERSION = "c3-fixed-horizon-v2"
SPLITS = ("train", "validation", "test")
HORIZONS = (15, 30, 60)


def sha256_file(path: Path) -> str:
    """Calculate the SHA-256 checksum of a file."""

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def write_jsonl_gz(path: Path, records: list[dict]) -> None:
    """Write JSONL using deterministic gzip compression."""

    with path.open("wb") as raw:
        with gzip.GzipFile(
            fileobj=raw,
            mode="wb",
            filename="",
            mtime=0,
        ) as compressed:
            for record in records:
                line = json.dumps(
                    record,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )

                compressed.write((line + "\n").encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("data/synthetic/c3_v2"),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/c3_v2"),
    )

    args = parser.parse_args()

    source_dir = args.dataset_dir
    output_dir = args.output_dir

    source_manifest_path = source_dir / "manifest.json"
    source_telemetry_path = source_dir / "telemetry.jsonl.gz"

    if not source_manifest_path.is_file():
        raise FileNotFoundError(source_manifest_path)

    if not source_telemetry_path.is_file():
        raise FileNotFoundError(source_telemetry_path)

    source_manifest = json.loads(
        source_manifest_path.read_text(encoding="utf-8")
    )

    actual_source_sha256 = sha256_file(source_telemetry_path)

    if actual_source_sha256 != source_manifest["packet_sha256"]:
        raise ValueError(
            "Source telemetry checksum does not match source manifest"
        )

    if (
        source_manifest.get("source_origin") != "SIMULATED"
        or source_manifest.get("not_field_data") is not True
        or source_manifest.get("not_landslide_ground_truth") is not True
    ):
        raise ValueError(
            "Source dataset provenance is not the expected synthetic V2"
        )

    print("Building C3 V2 fixed-horizon examples...")

    examples = build_v2_fixed_horizon_examples(
        str(source_dir),
        horizons_minutes=HORIZONS,
        tolerance_minutes=2.0,
        target_feature="soil_moisture_pct",
        min_history_steps=3,
        max_history_steps=32,
    )

    records_by_split = defaultdict(list)

    episode_splits = defaultdict(set)
    counts_by_horizon = Counter()
    counts_by_split_horizon = Counter()
    origin_modes = Counter()

    example_ids = set()

    for example in examples:
        if example.split not in SPLITS:
            raise ValueError(
                f"Unexpected dataset split: {example.split}"
            )

        episode_splits[example.episode_id].add(example.split)

        identity = (
            example.episode_id,
            example.device_id,
            example.forecast_origin.isoformat(),
            example.target_feature,
            example.requested_horizon_minutes,
        )

        if identity in example_ids:
            raise ValueError(
                f"Duplicate supervised example identity: {identity}"
            )

        example_ids.add(identity)

        record = example.to_record()

        records_by_split[example.split].append(record)

        counts_by_horizon[
            str(example.requested_horizon_minutes)
        ] += 1

        counts_by_split_horizon[
            (example.split, str(example.requested_horizon_minutes))
        ] += 1

        origin_modes[
            (
                example.split,
                example.input_sequence.steps[-1].operating_mode.value,
            )
        ] += 1

    conflicting_episodes = {
        episode: splits
        for episode, splits in episode_splits.items()
        if len(splits) != 1
    }

    if conflicting_episodes:
        raise ValueError(
            "Episode leakage across dataset splits: "
            f"{conflicting_episodes}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    exported_files = {}

    for split in SPLITS:
        path = output_dir / f"{split}.jsonl.gz"

        # Stable ordering ensures repeatable exported bytes.
        records = sorted(
            records_by_split[split],
            key=lambda item: (
                item["episode_id"],
                item["device_id"],
                item["forecast_origin"],
                item["target"]["requested_horizon_minutes"],
            ),
        )

        write_jsonl_gz(path, records)

        exported_files[split] = {
            "filename": path.name,
            "examples": len(records),
            "sha256": sha256_file(path),
        }

        print(
            f"Exported {split}: {len(records):,} examples"
        )

    manifest = {
        "export_version": EXPORT_VERSION,
        "source_dataset_version": source_manifest["dataset_version"],
        "source_origin": "SIMULATED",
        "not_field_data": True,
        "not_landslide_ground_truth": True,
        "training_objective": (
            "FUTURE_SENSOR_VALUE_REGRESSION"
        ),
        "target_feature": "soil_moisture_pct",
        "forecast_horizons_minutes": list(HORIZONS),
        "target_tolerance_minutes": 2.0,
        "minimum_history_steps": 3,
        "maximum_history_steps": 32,
        "split_policy": "EPISODE_DISJOINT",
        "source_telemetry_sha256": actual_source_sha256,
        "source_manifest_sha256": sha256_file(
            source_manifest_path
        ),
        "total_examples": len(examples),
        "counts_by_horizon": {
            str(horizon): counts_by_horizon[str(horizon)]
            for horizon in HORIZONS
        },
        "counts_by_split_horizon": {
            split: {
                str(horizon): counts_by_split_horizon[
                    (split, str(horizon))
                ]
                for horizon in HORIZONS
            }
            for split in SPLITS
        },
        "forecast_origin_mode_counts": {
            split: {
                mode: origin_modes[(split, mode)]
                for mode in (
                    "DEEP_SLEEP",
                    "IDLE",
                    "RISK",
                    "WARNING",
                    "EMERGENCY",
                )
            }
            for split in SPLITS
        },
        "files": exported_files,
        "limitations": [
            "Synthetic telemetry, not field measurements",
            "No verified landslide-event ground truth",
            "Targets are observed future sensor values",
            "Requested horizons use a plus/minus two-minute tolerance",
            "Overlapping histories create dependent examples",
            "EMERGENCY mode has no valid forecast-origin examples",
            "WARNING mode is absent from original test telemetry",
            "Episode-disjoint splitting does not prove field generalization",
            "Feature-age causality requires additional verification",
        ],
    }

    manifest_path = output_dir / "manifest.json"

    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("\n=== C3 V2 EXPORT SUMMARY ===")
    print(f"Total examples: {len(examples):,}")

    for horizon in HORIZONS:
        print(
            f"{horizon}-minute examples: "
            f"{counts_by_horizon[str(horizon)]:,}"
        )

    print(f"\nOutput directory: {output_dir}")
    print("Export completed successfully.")


if __name__ == "__main__":
    main()