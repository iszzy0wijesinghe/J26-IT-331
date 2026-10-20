"""Process the raw C1 CSV into the final training dataset (Parquet)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import yaml

from components.c1_credibility.datasets import splits
from components.c1_credibility.datasets.schemas import DATASET_CODE, TARGET_COLUMN as LABEL_COLUMN

BUILDER_VERSION = "c1_build_1.0.0"
CLASSES = ("CLEAN", "ANOMALY", "VALID_EVENT")
SPLITS = ("train", "val", "test")

RAW_INPUT_DIR = Path("data/synthetic/c1")
DEFAULT_OUTPUT_DIR = Path("data/processed/c1")
DEFAULT_MANIFEST_DIR = Path("data/manifests")
CONFIG_CANDIDATES = (
    Path("configs/components/c1_labeling_v1.yaml"),
    Path("components/c1_credibility/configs/c1_labeling_v1.yaml"),
)

# These are C2's job (missing data). C1 should not use them. Drop them.
LEAKAGE_FEATURES = ["value_present", "obs_gap_steps", "recent_read_failures"]

# Required columns from the leader's CSV file
REQUIRED_COLUMNS = [
    "record_id", "observed_at", "device_id", "sensor_instance_id", 
    "zone_id", "value", "credibility_label", "scenario_id"
]

class BuildError(RuntimeError):
    pass

def _to_ns(d: Any) -> Any:
    """Recursively convert dict to SimpleNamespace."""
    if isinstance(d, dict):
        return SimpleNamespace(**{k: _to_ns(v) for k, v in d.items()})
    return d

def find_input(path: Path | None) -> Path:
    """Find the CSV file."""
    if path is not None and path.is_file():
        return path
    folder = path if path is not None else RAW_INPUT_DIR
    candidates = sorted(folder.glob("*.csv"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise BuildError(f"No CSV files in {folder}")
    return candidates[-1]

def load_config(path: Path | None) -> SimpleNamespace:
    """Load the YAML config file and convert to SimpleNamespace."""
    candidates = [path] if path else list(CONFIG_CANDIDATES)
    for candidate in candidates:
        if candidate and candidate.is_file():
            with candidate.open(encoding="utf-8") as handle:
                cfg = yaml.safe_load(handle)
            cfg["_path"] = str(candidate)
            return _to_ns(cfg)
    raise BuildError(f"Labeling config not found.")

def sha256(path: Path) -> str:
    """Calculate the file hash."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()

def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names and check for required columns."""
    df.columns = [c.strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise BuildError(f"Raw file is missing required columns: {missing}")
    return df.copy()

def _blank(series: pd.Series) -> pd.Series:
    """Find empty or nan values."""
    return series.isna() | series.astype(str).str.strip().isin(["", "nan", "None"])

def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate rows based on record_id."""
    n_before = len(df)
    df = df.drop_duplicates(subset=["record_id"], keep="first")
    n_after = len(df)
    if n_before != n_after:
        print(f"Dropped {n_before - n_after} duplicate record_id rows")
    return df

def drop_leakage_features(df: pd.DataFrame) -> pd.DataFrame:
    """Drop leakage features that belong to C2."""
    cols_to_drop = [c for c in LEAKAGE_FEATURES if c in df.columns]
    if cols_to_drop:
        print(f"Dropping leakage features: {cols_to_drop}")
        df = df.drop(columns=cols_to_drop)
    return df

def infer_scenario_type(df: pd.DataFrame) -> pd.DataFrame:
    """Infer scenario_type from labels if missing."""
    if "scenario_type" in df.columns and df["scenario_type"].notna().all():
        return df
    present = (
        pd.crosstab(df["scenario_id"], df[LABEL_COLUMN]).reindex(
            columns=list(CLASSES), fill_value=0
        ) > 0
    )
    kind = pd.Series("CLEAN_ONLY", index=present.index)
    kind[present["ANOMALY"] & ~present["VALID_EVENT"]] = "FAULT_ONLY"
    kind[~present["ANOMALY"] & present["VALID_EVENT"]] = "EVENT_ONLY"
    kind[present["ANOMALY"] & present["VALID_EVENT"]] = "EVENT_AND_FAULT"
    print("scenario_type missing, inferred from labels:", dict(Counter(kind)))
    return df.assign(scenario_type=df["scenario_id"].map(kind))

def attach_splits(df: pd.DataFrame, cfg: SimpleNamespace, seed: int) -> pd.DataFrame:
    """Split into train/val/test using the splits module."""
    meta = df[["scenario_id", "scenario_type"]].drop_duplicates().values.tolist()
    meta = [(row[0], row[1], i) for i, row in enumerate(meta)]
    result = splits.assign_scenario_splits(meta, cfg, seed)
    df["split"] = df["scenario_id"].map(result)
    
    if "split" not in df.columns:
        raise BuildError("Could not generate 'split' column")
    return df

def validate(df: pd.DataFrame, cfg: SimpleNamespace, freeze: bool) -> None:
    """Final validation of the dataset."""
    if freeze and cfg.meta.status != "APPROVED":
        raise BuildError("Cannot freeze: config status is PROVISIONAL")

    bad_split = sorted(set(df["split"]) - set(SPLITS))
    if bad_split:
        raise BuildError(f"Unexpected split values: {bad_split}")

    crossing = df.groupby("scenario_id")["split"].nunique()
    crossing = crossing[crossing > 1]
    if len(crossing):
        raise BuildError(f"Scenarios appear in more than one split: {list(crossing.index[:5])}")

    eligible = df[df["train_eligible"] == True] if "train_eligible" in df.columns else df
    for split in SPLITS:
        present = set(eligible.loc[eligible["split"] == split, LABEL_COLUMN])
        missing = sorted(set(CLASSES) - present)
        if missing:
            print(f"WARNING: Split '{split}' has no rows for: {missing}")

def write_outputs(
    df: pd.DataFrame, cfg: SimpleNamespace, args: argparse.Namespace, input_path: Path, seed: int,
) -> dict[str, Any]:
    """Save the Parquet file and the Manifest."""
    dataset_version = f"{DATASET_CODE}_{args.version}"
    df = df.assign(dataset_version=dataset_version)
    
    if "source_origin" not in df.columns:
        df["source_origin"] = "SYNTHETIC"

    df["observed_at"] = pd.to_datetime(df["observed_at"], utc=True, errors="coerce")
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.manifest_dir.mkdir(parents=True, exist_ok=True)
    
    dataset_path = args.output_dir / f"{dataset_version}.parquet"
    df.to_parquet(dataset_path, engine="pyarrow", index=False)

    label_counts = {
        s: {
            k: int(v)
            for k, v in df[df["split"] == s][LABEL_COLUMN].value_counts().sort_index().items()
        }
        for s in SPLITS
    }
    
    manifest = {
        "dataset_code": DATASET_CODE,
        "version": args.version,
        "dataset_version": dataset_version,
        "row_count": int(len(df)),
        "file_hash": sha256(dataset_path),
        "label_counts": label_counts,
        "created_at": datetime.now(UTC).isoformat(),
    }
    
    (args.manifest_dir / f"{dataset_version}.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest["_dataset_path"] = str(dataset_path)
    return manifest

def run(args: argparse.Namespace) -> int:
    """Main run function."""
    cfg = load_config(args.config)
    seed = args.seed if args.seed is not None else 42

    input_path = find_input(args.input)
    print(f"Reading {input_path}")
    raw = pd.read_csv(input_path, low_memory=False)
    n_input = len(raw)

    # 1. Standardize column names
    df = map_columns(raw)
    
    # 2. Remove duplicate rows
    df = drop_duplicates(df)
    
    # 3. Remove rows without labels
    df = df[~_blank(df[LABEL_COLUMN])]
    
    # 4. Drop leakage features
    df = drop_leakage_features(df)
    
    # 5. Infer scenario_type
    df = infer_scenario_type(df)
    
    # 6. Assign splits
    df = attach_splits(df, cfg, seed)
    
    # 7. Validate
    validate(df, cfg, args.freeze)

    # 8. Save outputs
    manifest = write_outputs(df, cfg, args, input_path, seed)
    
    print("\n=== C1 dataset summary ===")
    print(f"input rows: {n_input}")
    print(f"final rows: {manifest['row_count']}")
    print("\nrows per split and class:")
    table = pd.crosstab(df["split"], df[LABEL_COLUMN]).reindex(
        index=list(SPLITS), columns=list(CLASSES), fill_value=0
    )
    print(table.to_string())
    print(f"\nwritten: {manifest['_dataset_path']}")
    return 0

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=None)
    p.add_argument("--config", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    p.add_argument("--version", default="V0.1.0-draft")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--freeze", action="store_true")
    return p.parse_args(argv)

def main(argv: list[str] | None = None) -> None:
    """Program entry point."""
    try:
        sys.exit(run(parse_args(argv)))
    except BuildError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()