"""Read-only inventory of existing C3 candidate implementations; not a benchmark."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def inventory(root: Path = ROOT) -> dict:
    model_root = root / "components/c3_forecasting/models"
    paths = sorted(model_root.glob("*.py")) if model_root.exists() else []
    models = [{"source_file": str(p.relative_to(root)), "name": p.stem} for p in paths if p.name != "__init__.py"]
    checkpoint_root = root / "artifacts/c3"
    checkpoints = [str(p.relative_to(root)) for p in checkpoint_root.rglob("*.pt")] if checkpoint_root.exists() else []
    return {"status": "INVENTORY_ONLY_NOT_MODEL_EVALUATION", "model_sources": models, "checkpoint_paths": sorted(checkpoints), "benchmark_winner": None}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(inventory(args.root), indent=2))
