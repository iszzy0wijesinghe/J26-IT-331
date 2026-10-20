# audit.py - read-only audit of a built C1 csv (GEONEX-5, Doc 05 s13 / s128 step 1)
# lives in components/c1_credibility/datasets/ and uses the repo's own schemas.py
#
#   python -m components.c1_credibility.datasets.audit data/synthetic/c1/<file>.csv [--json audit_report.json]
#
# never changes the file. checks the header against schemas.DATASET_COLUMNS,
# provenance, label / ambiguity / split consistency, units and leakage smells.
# prints PASS / WARN / FAIL. a clean audit does NOT prove the labels are right,
# that needs the generator's truth file
# exit code: 0 no FAIL, 1 at least one FAIL, 2 could not read the file

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from . import schemas
except ImportError:   # plain module import
    import schemas

try:
    from shared.enums import C1ContextStatus
    CONTEXT_VALUES = {m.value for m in C1ContextStatus}
except ImportError:
    CONTEXT_VALUES = {"COMPLETE", "PARTIAL", "INSUFFICIENT_CONTEXT"}

TARGET = schemas.TARGET_COLUMN
CLASSES = ("CLEAN", "ANOMALY", "VALID_EVENT")
SPLITS = ("train", "val", "test")
SOURCES = ("SYNTHETIC", "PHYSICAL_DEMO", "EXTERNAL")
AMBIGUITY = {"FAULT_BELOW_DETECTABILITY", "ISOLATED_RESPONSE", "PARTIAL_NEIGHBOUR_RESPONSE",
             "OVERLAPPING_EVENTS", "BORDERLINE_EXTREME"}
KEPT_REASON = "BORDERLINE_EXTREME"   # ambiguous but still train eligible (labels.TRAINING_KEPT_REASON)
REGIME_ORDER = ["DRY", "LIGHT", "MODERATE", "HEAVY", "EXTREME"]
NEEDED = ["scenario_id", "observed_at", "device_id", TARGET, "split"]

LABEL_SIDE = {TARGET, "label_source", "ambiguous", "ambiguity_reason", "borderline_extreme",
              "train_eligible", "context_status", "split", "split_temporal", "split_device"}
NOT_PROBED = {"record_id", "observation_id", "scenario_id", "observed_at"}
ID_LIKE = {"device_id", "zone_id", "sensor_instance_id", "test_run_id", "calibration_version",
           "dataset_version", "source_origin", "event_id"}


class Audit:
    def __init__(self) -> None:
        self.rows: list[dict[str, str]] = []

    def _add(self, level: str, section: str, msg: str) -> None:
        self.rows.append({"level": level, "section": section, "message": msg})
        print(f"[{level:<4}] {section}: {msg}")

    def ok(self, s: str, m: str) -> None: self._add("PASS", s, m)
    def warn(self, s: str, m: str) -> None: self._add("WARN", s, m)
    def fail(self, s: str, m: str) -> None: self._add("FAIL", s, m)
    def info(self, s: str, m: str) -> None: self._add("INFO", s, m)

    def count(self, level: str) -> int:
        return sum(1 for r in self.rows if r["level"] == level)

    def verdict(self, cond_bad: bool, section: str, bad_msg: str, good_msg: str, level: str = "fail") -> None:
        (getattr(self, level) if cond_bad else self.ok)(section, bad_msg if cond_bad else good_msg)


# ---- loading ----

def to_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.astype("boolean")
    m = {"true": True, "1": True, "false": False, "0": False}
    return s.astype("string").str.strip().str.lower().map(m).astype("boolean")


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    if "observed_at" in df.columns:
        df["observed_at"] = pd.to_datetime(df["observed_at"], utc=True, errors="coerce")
    for c in ("ambiguous", "train_eligible", "borderline_extreme"):
        if c in df.columns:
            df[c] = to_bool(df[c])
    return df


def eligible(df: pd.DataFrame) -> pd.Series:
    if "train_eligible" in df.columns:
        return df["train_eligible"].fillna(False).astype(bool)
    return pd.Series(True, index=df.index)


def insufficient(df: pd.DataFrame) -> pd.Series:
    return df["context_status"].astype("string").str.upper().str.contains("INSUFFICIENT", na=False)


# ---- checks ----

def check_schema(df: pd.DataFrame, a: Audit) -> bool:
    s = "schema"
    a.info(s, f"{len(df)} rows, {df.shape[1]} columns")
    miss = [c for c in NEEDED if c not in df.columns]
    if miss:
        a.fail(s, f"cannot audit, missing columns: {miss}")
        return False

    missing = [c for c in schemas.DATASET_COLUMNS if c not in df.columns]
    extra = [c for c in df.columns if c not in schemas.DATASET_COLUMNS]
    a.verdict(bool(missing), s, f"columns in schemas.DATASET_COLUMNS but not in the csv: {missing}", "all DATASET_COLUMNS are present")
    a.verdict(bool(extra), s, f"csv columns not in schemas.DATASET_COLUMNS: {extra}", "no extra columns", "warn")
    if not missing and not extra:
        a.verdict(list(df.columns) != schemas.DATASET_COLUMNS, s, "column order differs from schemas.DATASET_COLUMNS", "column order matches schemas", "warn")
    both = sorted(set(schemas.FEATURE_COLUMNS) & set(schemas.FORBIDDEN_FEATURES))
    a.verdict(bool(both), s, f"FEATURE_COLUMNS overlaps FORBIDDEN_FEATURES: {both}", "no feature column is forbidden")

    bad = sorted(set(df[TARGET].dropna().unique()) - set(CLASSES))
    a.verdict(bool(bad), s, f"{TARGET} has values outside {CLASSES}: {bad}", "labels only hold CLEAN / ANOMALY / VALID_EVENT")
    for col in ("split", "split_temporal", "split_device"):
        if col in df.columns:
            bad = sorted(set(df[col].dropna().unique()) - set(SPLITS))
            a.verdict(bool(bad), s, f"{col} has unexpected values: {bad}", f"{col} only holds train / val / test")
    if "ambiguity_reason" in df.columns:
        bad = sorted(set(df["ambiguity_reason"].dropna().unique()) - AMBIGUITY)
        a.verdict(bool(bad), s, f"ambiguity_reason has unknown values: {bad}", "ambiguity reasons are all known")
    if "context_status" in df.columns:
        bad = sorted(set(df["context_status"].dropna().unique()) - CONTEXT_VALUES)
        a.verdict(bool(bad), s, f"context_status values not in the enum {sorted(CONTEXT_VALUES)}: {bad}", "context_status values are all known")
    return True


def check_provenance(df: pd.DataFrame, a: Audit) -> None:
    s = "provenance"
    for col in ("source_origin", "label_source", "dataset_version", "calibration_version", "test_run_id"):
        if col in df.columns:
            a.info(s, f"{col}: {df[col].value_counts(dropna=False).head(5).to_dict()}")
    if "source_origin" in df.columns:
        vals = set(df["source_origin"].dropna().astype(str).unique())
        a.verdict(bool(vals - set(SOURCES)), s, f"source_origin outside {SOURCES}: {sorted(vals - set(SOURCES))}", "source_origin uses the allowed source types", "warn")
        a.verdict(len(vals) > 1, s, f"several source types in one file: {sorted(vals)}, report them separately", "single source type", "warn")
        if df["source_origin"].isna().any():
            a.fail(s, f"{int(df['source_origin'].isna().sum())} row(s) without source_origin")


def check_basic(df: pd.DataFrame, a: Audit) -> None:
    s = "basic"
    if "record_id" in df.columns:
        d = int(df["record_id"].duplicated().sum())
        a.verdict(d > 0, s, f"{d} duplicated record_id", "record_id is unique")
        if d > 0:
            dupes = df[df["record_id"].duplicated(keep=False)].sort_values("record_id")
            a.info(s, f"Example duplicate record_ids:\n{dupes[['record_id', 'scenario_id', 'sensor_instance_id', 'observed_at', 'credibility_label']].head(10).to_string()}")
    d = int(df.duplicated(["device_id", "observed_at"]).sum())
    a.verdict(d > 0, s, f"{d} duplicated (device_id, observed_at) pair(s)", "no duplicated (device_id, observed_at)", "warn")
    nat = int(df["observed_at"].isna().sum())
    a.verdict(nat > 0, s, f"{nat} unparseable/null observed_at", f"observed_at parsed, {df['observed_at'].min()} to {df['observed_at'].max()}")
    nulls = df.isna().sum()
    nulls = nulls[nulls > 0]
    if len(nulls):
        a.info(s, "null counts: " + ", ".join(f"{k}={v}" for k, v in nulls.items()))


def check_labels(df: pd.DataFrame, a: Audit) -> None:
    s = "labels"
    counts = df[TARGET].value_counts()
    a.info(s, "class balance: " + ", ".join(f"{k}={v} ({v / len(df):.1%})" for k, v in counts.items()))
    miss = [c for c in CLASSES if c not in counts.index]
    if miss:
        a.fail(s, f"class(es) with no rows at all: {miss}")

    if {"ambiguous", "ambiguity_reason"} <= set(df.columns):
        n = int((df["ambiguity_reason"].notna() & ~df["ambiguous"].fillna(False)).sum())
        a.verdict(n > 0, s, f"{n} row(s) with an ambiguity_reason but ambiguous=False", "ambiguity_reason implies ambiguous")
        n = int((df["ambiguous"].fillna(False) & df["ambiguity_reason"].isna()).sum())
        if n:
            a.warn(s, f"{n} ambiguous row(s) without a reason")
    if {"ambiguous", "ambiguity_reason", "train_eligible"} <= set(df.columns):
        dropped = df["ambiguous"].fillna(False) & (df["ambiguity_reason"] != KEPT_REASON)
        n = int((dropped & df["train_eligible"].fillna(False)).sum())
        a.verdict(n > 0, s, f"{n} ambiguous row(s) (not {KEPT_REASON}) with train_eligible=True", f"ambiguous rows are excluded from training (except {KEPT_REASON})")
    if {"context_status", "train_eligible"} <= set(df.columns):
        n = int((insufficient(df) & df["train_eligible"].fillna(False)).sum())
        a.verdict(n > 0, s, f"{n} insufficient-context row(s) with train_eligible=True", "insufficient-context rows are not train eligible")
        a.info(s, f"train_eligible rows: {int(eligible(df).sum())} of {len(df)}")
    if "event_id" in df.columns:
        n = int(((df[TARGET] == "VALID_EVENT") & df["event_id"].isna()).sum())
        a.verdict(n > 0, s, f"{n} VALID_EVENT row(s) without event_id", "every VALID_EVENT row has an event_id", "warn")


def check_splits(df: pd.DataFrame, a: Audit) -> None:
    s = "splits"
    n_scen = df["scenario_id"].nunique()
    a.info(s, f"{n_scen} scenarios, rows per scenario median {int(df.groupby('scenario_id').size().median())}")
    elig = eligible(df)

    for col in ("split", "split_temporal"):          # device holdout may cross scenarios, these may not
        if col not in df.columns:
            continue
        cross = df.groupby("scenario_id")[col].nunique()
        cross = cross[cross > 1]
        a.verdict(len(cross) > 0, s, f"{col}: {len(cross)} scenario(s) in more than one partition, e.g. {list(cross.index[:3])}", f"{col}: no scenario is split across partitions")
        if "event_id" in df.columns:
            ev = df.dropna(subset=["event_id"]).groupby(["scenario_id", "event_id"])[col].nunique()
            a.verdict(bool((ev > 1).any()), s, f"{col}: event(s) in more than one partition", f"{col}: no event is split across partitions")

    a.info(s, f"scenario share per split: {df.drop_duplicates('scenario_id')['split'].value_counts(normalize=True).round(3).to_dict()}")
    for col in ("split", "split_temporal", "split_device"):
        if col not in df.columns:
            continue
        for sp in SPLITS:
            if col == "split_device" and not (df[col] == sp).any():
                continue   # device holdout may only use some of the partitions
            rows = df[(df[col] == sp) & elig]
            miss = [c for c in CLASSES if c not in set(rows[TARGET])]
            lvl = "warn" if col == "split_device" else "fail"   # a held-out device can legitimately be thin
            a.verdict(bool(miss), s, f"{col}={sp}: eligible rows miss class(es) {miss}", f"{col}={sp}: all 3 classes present ({len(rows)} eligible rows)", lvl)

    if "split_temporal" in df.columns:
        start = df.groupby("scenario_id").agg(t=("observed_at", "min"), sp=("split_temporal", "first"))
        bounds = {sp: (start.loc[start.sp == sp, "t"].min(), start.loc[start.sp == sp, "t"].max()) for sp in SPLITS if (start.sp == sp).any()}
        a.info(s, "scenario start range per split_temporal: " + "; ".join(f"{k}: {lo} .. {hi}" for k, (lo, hi) in bounds.items()))
        if {"train", "val", "test"} <= set(bounds):
            ordered = bounds["train"][1] <= bounds["val"][0] and bounds["val"][1] <= bounds["test"][0]
            a.verdict(not ordered, s, "split_temporal is not time ordered (train < val < test by scenario start)", "split_temporal is time ordered")
    if "split_device" in df.columns:
        per_dev = df.groupby("device_id")["split_device"].nunique()
        a.info(s, f"devices: {df['device_id'].nunique()}; devices with rows in more than one split_device value: {int((per_dev > 1).sum())}")
    
    # FIX: Handle NaN values in TARGET before sorting and joining
    mixed = df.groupby("scenario_id")[TARGET].agg(lambda x: "+".join(sorted(set(x.dropna().astype(str))))).value_counts()
    a.info(s, "label mix per scenario: " + ", ".join(f"{k}={v}" for k, v in mixed.items()))


def check_values(df: pd.DataFrame, a: Audit) -> None:
    s = "units"
    if "value" in df.columns:
        g = df.groupby(TARGET)["value"].agg(["min", "median", "max"]).round(3)
        a.info(s, "value (min/median/max) by class: " + "; ".join(f"{k}: {r['min']}/{r['median']}/{r['max']}" for k, r in g.iterrows()))
    if {"value", "value_present"} <= set(df.columns):
        n = int(((df["value"].isna()) == (df["value_present"] == 1)).sum())
        a.verdict(n > 0, s, f"{n} row(s) where value_present disagrees with value being null", "value_present matches null values", "warn")
    rain = [c for c in ("rain_15m_mm", "rain_1h_mm", "rain_3h_mm") if c in df.columns]
    if len(rain) == 3:
        n = int(((df[rain[0]] > df[rain[1]] + 1e-9) | (df[rain[1]] > df[rain[2]] + 1e-9)).sum())
        a.verdict(n > 0, s, f"{n} row(s) where a shorter rain window exceeds a longer one", "rain windows are monotonic (15m <= 1h <= 3h)", "warn")
        neg = int((df[rain] < 0).any(axis=1).sum())
        a.verdict(neg > 0, s, f"{neg} row(s) with negative rain", "no negative rain")
    if {"rainfall_regime", "rain_1h_mm"} <= set(df.columns):
        med = df.groupby("rainfall_regime")["rain_1h_mm"].median()
        known = [r for r in REGIME_ORDER if r in med.index]
        a.info(s, "median rain_1h_mm per regime: " + ", ".join(f"{k}={v:.2f}" for k, v in med.items()))
        if len(known) == len(med) and len(known) > 1 and not med[known].is_monotonic_increasing:
            a.warn(s, "regime order DRY..EXTREME does not follow median rain_1h_mm")
    for col, lo, hi in (("neighbour_rise_agree_frac", 0, 1), ("n_neighbours_fresh", 0, None), ("stuck_run_len", 0, None),
                        ("dt_s", 0, None), ("history_obs", 0, None), ("recent_read_failures", 0, None), ("steps_since_rain", 0, None)):
        if col in df.columns:
            v = df[col].dropna()
            bad = int(((v < lo) | ((v > hi) if hi is not None else False)).sum()) if len(v) else 0
            a.verdict(bad > 0, s, f"{col}: {bad} value(s) outside [{lo}, {hi if hi is not None else 'inf'}]", f"{col} in range")
    if "device_voltage" in df.columns:
        a.info(s, f"device_voltage min/median/max: {df['device_voltage'].min():.2f}/{df['device_voltage'].median():.2f}/{df['device_voltage'].max():.2f}")


def check_state_columns(df: pd.DataFrame, a: Audit) -> None:
    s = "leakage"
    if "value_present" in df.columns:
        absent = df[df["value_present"] == 0]
        if len(absent):
            share = absent[TARGET].value_counts(normalize=True).round(3).to_dict()
            a.info(s, f"rows with no reading: {len(absent)}, label share {share}")
            a.verdict(absent[TARGET].nunique() == 1, s,
                      "every row without a reading has the same label, value_present / obs_gap_steps / recent_read_failures act as label proxies (missing readings belong to C2)",
                      "rows without a reading are spread over several labels", "warn")
    if {"recent_read_failures", "value_present"} <= set(df.columns):
        present = df[df["value_present"] == 1]
        if len(present) and (present["recent_read_failures"].fillna(0) == 0).all():
            a.warn(s, "recent_read_failures is 0 on every row that has a reading, it only counts the current dropout run, not recent failures")
    if "mode" in df.columns:
        a.verdict(df["mode"].nunique() > 1, s, f"mode has {df['mode'].nunique()} values, label share per mode:\n" + pd.crosstab(df['mode'], df[TARGET], normalize='index').round(2).to_string(),
                  "mode is constant, it carries no information (safe, but useless as a feature)", "warn")
    if "dt_s" in df.columns:
        per = df.groupby(TARGET)["dt_s"].nunique().to_dict()
        a.info(s, f"distinct dt_s per class: {per}")
        if df["dt_s"].nunique() > 1:
            a.warn(s, "dt_s varies, check that sampling interval is not tied to scenario type or label")


def probe_single_columns(df: pd.DataFrame, a: Audit, top: int = 12) -> None:
    s = "leakage"
    try:
        from sklearn.metrics import balanced_accuracy_score
        from sklearn.tree import DecisionTreeClassifier
    except ImportError:
        a.info(s, "scikit-learn not installed, skipping single-column probes")
        return
    elig = eligible(df)
    tr, va = df[(df["split"] == "train") & elig], df[(df["split"] == "val") & elig]
    if tr[TARGET].nunique() < 2 or va.empty:
        a.info(s, "train/val too thin for single-column probes")
        return

    def encode(col: str) -> tuple[np.ndarray, np.ndarray]:
        if pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col]):
            lo = df[col].min() - 1 if df[col].notna().any() else -1
            return tr[col].fillna(lo).to_numpy(float), va[col].fillna(lo).to_numpy(float)
        cats = {v: i for i, v in enumerate(tr[col].astype("string").dropna().unique())}
        f = lambda x: x.astype("string").map(cats).fillna(-1).to_numpy(float)
        return f(tr[col]), f(va[col])

    scores: list[tuple[str, float]] = []
    for col in df.columns:
        if col in LABEL_SIDE or col in NOT_PROBED:
            continue
        xt, xv = encode(col)
        clf = DecisionTreeClassifier(max_depth=3, random_state=0).fit(xt.reshape(-1, 1), tr[TARGET])
        scores.append((col, balanced_accuracy_score(va[TARGET], clf.predict(xv.reshape(-1, 1)))))
    scores.sort(key=lambda t: -t[1])
    chance = 1 / va[TARGET].nunique()
    a.info(s, f"single-column probe (balanced accuracy on val, chance ~{chance:.2f}): " + ", ".join(f"{c}={v:.2f}" for c, v in scores[:top]))
    hot = [c for c, v in scores if c in ID_LIKE and c != "event_id" and v > chance + 0.10]
    a.verdict(bool(hot), s, f"identifier-like column(s) predict the label better than chance: {hot}", "no identifier-like column predicts the label on its own", "warn")


# ---- main ----

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="read-only audit of a built C1 csv")
    p.add_argument("csv", type=Path)
    p.add_argument("--json", type=Path, help="also write the findings as json")
    args = p.parse_args(argv)
    try:
        df = load(args.csv)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"cannot read input: {exc}", file=sys.stderr)
        return 2

    a = Audit()
    if check_schema(df, a):
        check_provenance(df, a)
        check_basic(df, a)
        check_labels(df, a)
        check_splits(df, a)
        check_values(df, a)
        check_state_columns(df, a)
        probe_single_columns(df, a)

    print(f"\nPASS={a.count('PASS')} WARN={a.count('WARN')} FAIL={a.count('FAIL')}")
    print("a clean audit still does not prove the labels are correct, compare with the generator truth file")
    if args.json:
        args.json.write_text(json.dumps(a.rows, indent=2), encoding="utf-8")
    return 1 if a.count("FAIL") else 0


if __name__ == "__main__":
    sys.exit(main())