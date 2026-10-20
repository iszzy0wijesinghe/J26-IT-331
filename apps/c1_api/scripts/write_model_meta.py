"""Writes models/c1/c1_xgboost_v1_meta.json, the file the API reads for class order and dashboard metrics.

Run it once after training, with the numbers from YOUR evaluation (test split):

    python scripts/write_model_meta.py --classes CLEAN ANOMALY VALID_EVENT \
        --macro-f1 0.91 --anomaly-recall 0.83 --valid-event-recall 0.88 \
        --evaluated-on "test split, scenario grouped"

--classes must be in the order the labels were encoded when the model was trained (0, 1, 2).
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--classes", nargs=3, required=True, metavar=("C0", "C1", "C2"), help="class names in training encoding order")
    p.add_argument("--version", default="c1_xgboost_v1")
    p.add_argument("--macro-f1", type=float)
    p.add_argument("--anomaly-recall", type=float)
    p.add_argument("--valid-event-recall", type=float)
    p.add_argument("--evaluated-on", default=None)
    p.add_argument("--out", type=Path, default=REPO_ROOT / "models" / "c1" / "c1_xgboost_v1_meta.json")
    a = p.parse_args()

    expected = {"CLEAN", "ANOMALY", "VALID_EVENT"}
    if set(a.classes) != expected:
        p.error(f"--classes must be a permutation of {sorted(expected)}")
    for name in ("macro_f1", "anomaly_recall", "valid_event_recall"):
        v = getattr(a, name)
        if v is not None and not 0 <= v <= 1:
            p.error(f"--{name.replace('_', '-')} must be between 0 and 1 (e.g. 0.91, not 91)")

    metrics = {k: v for k, v in {
        "macro_f1": a.macro_f1, "anomaly_recall": a.anomaly_recall,
        "valid_event_recall": a.valid_event_recall, "evaluated_on": a.evaluated_on,
    }.items() if v is not None}

    meta = {"version": a.version, "trained_at": str(date.today()), "classes": a.classes, "metrics": metrics}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"wrote {a.out}\n{json.dumps(meta, indent=2)}")


if __name__ == "__main__":
    main()
