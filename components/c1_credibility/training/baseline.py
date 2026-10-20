"""Rule-based baseline for C1 credibility classification.

This baseline uses simple rules (no ML) to classify observations:
- If value is outside valid range [0, 100] -> ANOMALY
- If rate of change is too high -> ANOMALY
- If rainfall is high and neighbours agree -> VALID_EVENT
- Otherwise -> CLEAN
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

DATASET_PATH = Path("data/synthetic/c1/C1_CREDIBILITY_V0.2.0/dataset.csv")
CLASSES = ["CLEAN", "ANOMALY", "VALID_EVENT"]


def rule_based_predict(row: pd.Series) -> str:
    """Simple rule-based classifier."""
    # Rule 1: Out of range -> ANOMALY
    if row["value"] < 0 or row["value"] > 100:
        return "ANOMALY"
    
    # Rule 2: Extreme rate of change -> ANOMALY
    if abs(row["delta_prev_pct_per_min"]) > 5.0:
        return "ANOMALY"
    
    # Rule 3: Rainfall + neighbour agreement -> VALID_EVENT
    if (
        row["rain_1h_mm"] > 2.5  # moderate rain or higher
        and row["neighbour_rise_agree_frac"] > 0.5
        and row["target_minus_consensus"] > 2.0
    ):
        return "VALID_EVENT"
    
    # Default: CLEAN
    return "CLEAN"


def main():
    """Evaluate rule-based baseline on test set."""
    print("Loading data...")
    df = pd.read_csv(DATASET_PATH, low_memory=False)
    df = df[df["train_eligible"] == True]
    
    test = df[df["split"] == "test"].copy()
    print(f"Test: {len(test)} rows")
    
    # Apply rules
    print("\nApplying rule-based classifier...")
    test["baseline_pred"] = test.apply(rule_based_predict, axis=1)
    
    # Evaluate
    print("\n=== Rule-Based Baseline Evaluation ===")
    print("\nClassification Report:")
    print(classification_report(
        test["credibility_label"], test["baseline_pred"], target_names=CLASSES
    ))
    
    print("\nConfusion Matrix:")
    cm = confusion_matrix(test["credibility_label"], test["baseline_pred"])
    print(pd.DataFrame(cm, index=CLASSES, columns=CLASSES).to_string())
    
    # Macro-F1
    from sklearn.metrics import f1_score
    macro_f1 = f1_score(test["credibility_label"], test["baseline_pred"], average="macro")
    print(f"\nMacro-F1: {macro_f1:.3f}")


if __name__ == "__main__":
    main()