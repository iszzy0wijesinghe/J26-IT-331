"""Rule-based and majority baselines for C1 credibility classification."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, f1_score

DATASET_PATH = Path("data/synthetic/c1/C1_CREDIBILITY_V0.2.0/dataset.csv")
CLASSES = ["CLEAN", "ANOMALY", "VALID_EVENT"]

MAX_RATE_PCT_PER_MIN = 1.0
RAIN_MM = 2.5
EVENT_RISE_PCT = 1.5
NEIGHBOUR_AGREE = 0.5


def rule_based_predict(row: pd.Series) -> str:
    value = row["value"]
    if pd.isna(value) or value < 0 or value > 100:
        return "ANOMALY"
    rate = row["delta_prev_pct_per_min"]
    if pd.notna(rate) and abs(rate) > MAX_RATE_PCT_PER_MIN:
        return "ANOMALY"
    # NaN-safe max using pd.Series
    rain = pd.Series([row["rain_1h_mm"], row["rain_3h_mm"]]).max()
    if (
        pd.notna(rain)
        and rain >= RAIN_MM
        and row["value_minus_baseline"] >= EVENT_RISE_PCT
        and row["neighbour_rise_agree_frac"] >= NEIGHBOUR_AGREE
    ):
        return "VALID_EVENT"
    return "CLEAN"


def report(name: str, y_true: pd.Series, y_pred: pd.Series) -> None:
    print(f"\n=== {name} ===")
    print(classification_report(y_true, y_pred, labels=CLASSES, target_names=CLASSES, zero_division=0))
    cm = confusion_matrix(y_true, y_pred, labels=CLASSES)
    print(pd.DataFrame(cm, index=CLASSES, columns=CLASSES).to_string())
    print(f"Macro-F1: {f1_score(y_true, y_pred, labels=CLASSES, average='macro', zero_division=0):.3f}")


def main() -> None:
    df = pd.read_csv(DATASET_PATH, low_memory=False)
    df = df[df["train_eligible"].astype(bool)]
    test = df[df["split"] == "test"].copy()
    print(f"Test: {len(test)} rows")

    report("Always-CLEAN baseline", test["credibility_label"], pd.Series("CLEAN", index=test.index))
    test["baseline_pred"] = test.apply(rule_based_predict, axis=1)
    report("Rule-based baseline", test["credibility_label"], test["baseline_pred"])


if __name__ == "__main__":
    main()