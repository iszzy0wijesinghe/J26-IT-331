"""Ablation baselines for C1: how much do rainfall and neighbour context add?

Same split, same class weights and same XGBoost settings for every run. Only the
feature list changes. Own-sensor features = the C1 feature list minus rainfall and
neighbour features, so context is the only difference.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report, confusion_matrix, f1_score, recall_score

DATASET_PATH = Path("data/synthetic/c1/C1_CREDIBILITY_V0.2.0/dataset.csv")
CLASSES = ["CLEAN", "ANOMALY", "VALID_EVENT"]
CLASS_WEIGHTS = {"CLEAN": 1.0, "ANOMALY": 10.0, "VALID_EVENT": 2.0}

# copy the EXACT feature list that train.py uses, in the same order
ALL_FEATURES = [
    "value",
    "delta_prev_pct_per_min",
    "baseline_mean",
    "baseline_std",
    "value_minus_baseline",
    "stuck_run_len",
    "device_voltage",
    "rain_15m_mm",
    "rain_1h_mm",
    "rain_3h_mm",
    "steps_since_rain",
    "n_neighbours_fresh",
    "neighbour_consensus_change",
    "target_minus_consensus",
    "neighbour_change_spread",
    "neighbour_rise_agree_frac",
]


def is_rain(col: str) -> bool:
    return col.startswith("rain") or col == "steps_since_rain"


def is_neighbour(col: str) -> bool:
    return col.startswith("neighbour") or col in {"n_neighbours_fresh", "target_minus_consensus"}


OWN = [c for c in ALL_FEATURES if not is_rain(c) and not is_neighbour(c)]
RAIN = [c for c in ALL_FEATURES if is_rain(c)]
NEIGHBOUR = [c for c in ALL_FEATURES if is_neighbour(c)]
SETTINGS = {
    "own only (value-only baseline)": OWN,
    "own + rainfall": OWN + RAIN,
    "own + neighbours": OWN + NEIGHBOUR,
    "all features (C1)": ALL_FEATURES,
}

# must be identical to the parameters in train.py
XGB_PARAMS = {
    "objective": "multi:softprob",
    "num_class": 3,
    "eval_metric": "mlogloss",
    "max_depth": 6,
    "learning_rate": 0.1,
    "n_estimators": 100,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "n_jobs": -1,
}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(DATASET_PATH, low_memory=False)
    df = df[df["train_eligible"].eq(True)]
    return tuple(df[df["split"] == s].copy() for s in ("train", "val", "test"))  # type: ignore[return-value]


def encode(labels: pd.Series) -> pd.Series:
    return labels.map({name: i for i, name in enumerate(CLASSES)})


def run(name: str, features: list[str], train, val, test, verbose: bool) -> dict:
    model = xgb.XGBClassifier(**XGB_PARAMS)
    model.fit(
        train[features],
        encode(train["credibility_label"]),
        sample_weight=train["credibility_label"].map(CLASS_WEIGHTS),
        eval_set=[(val[features], encode(val["credibility_label"]))],
        verbose=False,
    )
    pred = [CLASSES[i] for i in model.predict(test[features])]
    truth = test["credibility_label"]
    recalls = recall_score(truth, pred, labels=CLASSES, average=None, zero_division=0)
    if verbose:
        print(f"\n=== {name} ({len(features)} features) ===")
        print(
            classification_report(
                truth, pred, labels=CLASSES, target_names=CLASSES, zero_division=0
            )
        )
        cm = confusion_matrix(truth, pred, labels=CLASSES)
        print(pd.DataFrame(cm, index=CLASSES, columns=CLASSES).to_string())
        ve_to_anomaly = cm[2][1] / cm[2].sum()
        print(f"VALID_EVENT -> ANOMALY: {ve_to_anomaly:.2%}")
    return {
        "setting": name,
        "n_features": len(features),
        "macro_f1": f1_score(truth, pred, labels=CLASSES, average="macro", zero_division=0),
        **{f"recall_{c}": r for c, r in zip(CLASSES, recalls, strict=True)},
    }


def main() -> None:
    train, val, test = load_data()
    print(f"Train {len(train)} | Val {len(val)} | Test {len(test)} rows")
    missing = [c for c in ALL_FEATURES if c not in train.columns]
    if missing:
        raise SystemExit(f"Columns not in the dataset: {missing}")

    rows = [
        run(name, feats, train, val, test, verbose=name.startswith("own only"))
        for name, feats in SETTINGS.items()
    ]
    table = pd.DataFrame(rows).round(3)
    print("\n=== Ablation summary (test set) ===")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()