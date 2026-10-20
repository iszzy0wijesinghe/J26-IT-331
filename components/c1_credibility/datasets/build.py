"""Build the synthetic C1 credibility dataset from the generator."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from components.c1_credibility.datasets import splits
from components.c1_credibility.datasets.config import load_config
from components.c1_credibility.datasets.features import build_features
from components.c1_credibility.datasets.generator import Scenario, generate_scenario
from components.c1_credibility.datasets.labels import (
    LABEL_SOURCE,
    is_train_eligible,
    label_observation,
    precompute_activity,
)
from components.c1_credibility.datasets.schemas import (
    DATASET_CODE,
    DATASET_COLUMNS,
    EXCLUSION_COLUMNS,
    SCHEMA_VERSION,
    TRUTH_COLUMNS,
)
from components.c1_credibility.datasets.splits import (
    assign_device_holdout,
    assign_scenario_splits,
    assign_temporal_splits,
)
from components.c1_credibility.datasets.validate import (
    ValidationError,
    check_classes_per_split,
    check_freeze,
    validate_dataset,
)
from shared.enums import C1ContextStatus, SourceOrigin

BUILDER_VERSION = "c1_builder_0.1.0"
Row = dict[str, Any]


def _build_rows(
    scenarios: list[Scenario], cfg: Any, seed: int, dataset_version: str
) -> tuple[list[Row], list[Row], list[Row]]:
    """Return (labeled rows, excluded rows, truth rows). Splits are added later."""
    rows: list[Row] = []
    excluded: list[Row] = []
    truth: list[Row] = []
    test_run_id = f"SYN-RUN-{seed}"

    for sc in scenarios:
        activities = [precompute_activity(sc, s, cfg) for s in sc.sensors]
        for t in range(sc.steps):
            for idx, sensor in enumerate(sc.sensors):
                if not sensor.avail[t]:
                    continue  # reading never delivered: nothing to label
                features, status = build_features(sc, idx, t, cfg)
                label = label_observation(sc, idx, t, activities, cfg)
                context_ok = status != C1ContextStatus.INSUFFICIENT_CONTEXT
                record_id = f"{sc.scenario_id}:{sensor.sensor_instance_id}:{t:04d}"
                observed_at = (sc.start_time + timedelta(seconds=t * sc.dt_s)).isoformat()

                base: Row = {
                    "record_id": record_id,
                    "observation_id": f"OBS-{sc.scenario_id}-{idx}-{t:04d}",
                    "scenario_id": sc.scenario_id,
                    "zone_id": sc.zone_id,
                    "device_id": sensor.device_id,
                    "sensor_instance_id": sensor.sensor_instance_id,
                    "observed_at": observed_at,
                    "source_origin": SourceOrigin.SYNTHETIC.value,
                    "test_run_id": test_run_id,
                    "dataset_version": dataset_version,
                    "label_source": LABEL_SOURCE,
                    "event_id": label.event_id or "",
                    "calibration_version": cfg.meta.calibration_version,
                    "context_status": status.value,
                    "ambiguous": label.ambiguous,
                    "ambiguity_reason": label.ambiguity_reason,
                    "borderline_extreme": label.borderline_extreme,
                    "_step": t,
                    "_prev_faulty": t > 0 and sensor.fault_type[t - 1] is not None,
                    "fault_type_truth": label.fault_type or "",
                }
                truth.append(
                    {
                        "record_id": record_id,
                        "truth_label": label.truth_label,
                        "fault_id": label.fault_id or "",
                        "fault_type": label.fault_type or "",
                        "fault_effect": label.fault_effect,
                        "event_id": label.event_id or "",
                        "event_component": round(label.event_component, 4),
                        "true_value": sensor.true[t],
                    }
                )
                if not context_ok:
                    excluded.append(
                        {
                            **base,
                            **features,
                            "credibility_label": "",
                            "train_eligible": False,
                        }
                    )
                    continue
                rows.append(
                    {
                        **base,
                        **features,
                        "credibility_label": label.truth_label,
                        "train_eligible": is_train_eligible(
                            True, label.ambiguous, label.ambiguity_reason
                        ),
                    }
                )
    return rows, excluded, truth


def _attach_splits(
    scenarios: list[Scenario],
    rows: list[Row],
    excluded: list[Row],
    cfg: Any,
    seed: int,
) -> tuple[int, set[str]]:
    meta = [(sc.scenario_id, sc.scenario_type, sc.index) for sc in scenarios]
    temporal = assign_temporal_splits(meta, cfg)
    devices = [s.device_id for sc in scenarios for s in sc.sensors]
    holdout = assign_device_holdout(devices, cfg, seed)

    last_error: Exception | None = None
    for attempt in range(cfg.split.max_attempts):
        split_seed = seed + attempt
        main = assign_scenario_splits(meta, cfg, split_seed)
        for row in rows + excluded:
            row["split"] = main[row["scenario_id"]]
            row["split_temporal"] = temporal[row["scenario_id"]]
            if holdout:
                row["split_device"] = "test" if row["device_id"] in holdout else "train"
            else:
                row["split_device"] = "not_run"
        try:
            check_classes_per_split(rows)
            return split_seed, holdout
        except ValidationError as error:
            last_error = error
    raise ValidationError(f"No split with all classes found: {last_error}")


def _format(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    if value is None:
        return ""
    return value


def _write_csv(path: Path, columns: list[str], rows: list[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        import csv
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_format(row.get(c)) for c in columns])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_dataset(
    version: str,
    seed: int,
    n_scenarios: int,
    out_dir: Path,
    manifest_dir: Path,
    config_path: Path | None = None,
    freeze: bool = False,
    steps_override: int | None = None,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    check_freeze(cfg, freeze)
    if steps_override:
        cfg.sim.steps_per_scenario = steps_override
    if n_scenarios < 18:
        raise ValueError("Use at least 18 scenarios so every split can hold all classes")

    dataset_version = f"{DATASET_CODE}_{version}"
    scenarios = [generate_scenario(i, seed, cfg) for i in range(n_scenarios)]
    rows, excluded, truth = _build_rows(scenarios, cfg, seed, dataset_version)
    split_seed, holdout = _attach_splits(scenarios, rows, excluded, cfg, seed)
    report = validate_dataset(scenarios, rows, cfg, freeze)

    target = out_dir / dataset_version
    dataset_path = target / "dataset.csv"
    _write_csv(dataset_path, DATASET_COLUMNS, rows)
    _write_csv(target / "truth.csv", TRUTH_COLUMNS, truth)
    _write_csv(target / "exclusions.csv", EXCLUSION_COLUMNS, excluded)

    labelled = [r for r in rows if r["credibility_label"]]
    label_counts: dict[str, dict[str, int]] = {}
    for split in ("train", "val", "test"):
        counts = Counter(r["credibility_label"] for r in labelled if r["split"] == split)
        label_counts[split] = dict(sorted(counts.items()))
    ambiguous = Counter(r["ambiguity_reason"] for r in rows if r["ambiguous"])

    manifest = {
        "dataset_code": DATASET_CODE,
        "version": version,
        "dataset_version": dataset_version,
        "schema_version": SCHEMA_VERSION,
        "label_schema_version": cfg.meta.labeling_spec_version,
        "labeling_spec_version": cfg.meta.labeling_spec_version,
        "labeling_config_version": cfg.meta.config_version,
        "parameter_status": cfg.meta.parameter_status,
        "frozen": freeze,
        "source_types": [SourceOrigin.SYNTHETIC.value],
        "sensor_family": "soil_moisture",
        "builder_version": BUILDER_VERSION,
        "random_seed": seed,
        "split_strategy": "scenario_grouped",
        "split_seed_used": split_seed,
        "device_holdout_devices": sorted(holdout),
        "device_holdout_run": bool(holdout),
        "n_scenarios": n_scenarios,
        "row_count": len(rows),
        "file_hash": _sha256(dataset_path),
        "label_counts": label_counts,
        "label_source_counts": dict(Counter(r["label_source"] for r in rows)),
        "ambiguous_count": sum(ambiguous.values()),
        "ambiguous_by_reason": dict(sorted(ambiguous.items())),
        "insufficient_context_count": len(excluded),
        "calibration_versions": [cfg.meta.calibration_version],
        "validation_report": report,
        "created_at": datetime.now(UTC).isoformat(),
    }
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{dataset_version}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the synthetic C1 credibility dataset")
    parser.add_argument("--version", default="V0.1.0-draft")
    parser.add_argument("--seed", type=int, default=20261016)
    parser.add_argument("--scenarios", type=int, default=60)
    parser.add_argument("--out-dir", type=Path, default=Path("data/synthetic/c1"))
    parser.add_argument("--manifest-dir", type=Path, default=Path("data/manifests"))
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()

    manifest = build_dataset(
        version=args.version,
        seed=args.seed,
        n_scenarios=args.scenarios,
        out_dir=args.out_dir,
        manifest_dir=args.manifest_dir,
        config_path=args.config,
        freeze=args.freeze,
    )
    print(json.dumps({k: manifest[k] for k in ("dataset_version", "row_count", "label_counts")}))


if __name__ == "__main__":
    main()