# splits.py - scenario grouped train/val/test split with device + temporal holdout (GEONEX-5)
# lives in components/c1_credibility/datasets/
#
# rules:
#   - a scenario (group_by column) is never split across train/val/test
#   - holdout conditions that fail are SKIPPED with a reason, they don't crash
#   - class gaps in a split are reported the same way, validate.py decides if
#     that blocks the freeze
#   - only the labeling yaml `split` section is read, no numbers in here

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

from schemas import LABEL_COLUMN, Label, SplitName

DEVICE_COLUMN = "device_id"
TIME_COLUMN = "observed_at"
ELIGIBLE_COLUMN = "train_eligible"

# the yaml says "at least 3 distinct devices (adjust to real device count)" in a
# free text condition, so the number lives here until it gets a param record
# (split.device_holdout.min_devices overrides it if present)
DEFAULT_MIN_DEVICES = 3

# keys the manifest accepts in holdout_skips (see schemas.HoldoutKind)
MANIFEST_SKIP_KEYS = ("temporal", "device")


class SplitError(ValueError):
    """bad config or bad input, not a data condition (those become skip reasons)"""


# ---- config ----

class _SplitConfig:
    def __init__(self, cfg: Mapping[str, Any]) -> None:
        split = cfg.get("split")
        if not isinstance(split, Mapping):
            raise SplitError("labeling config has no `split` section")
        if split.get("strategy") != "scenario_grouped":
            raise SplitError(f"split.strategy must be scenario_grouped, got {split.get('strategy')!r}")

        self.group_col: str = split.get("group_by") or ""
        if not self.group_col:
            raise SplitError("split.group_by is missing")
        self.strat_col: str | None = split.get("stratify_by")

        seed = _value(split.get("random_seed"))
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            raise SplitError(f"split.random_seed must be a non-negative int, got {seed!r}")
        self.seed: int = seed

        raw = split.get("fractions", {})
        fractions: dict[SplitName, float] = {}
        for name in SplitName:
            v = _value(raw.get(name.value))
            if v is None:
                raise SplitError(f"split.fractions.{name.value} is missing or null")
            fractions[name] = float(v)
        if any(f < 0 for f in fractions.values()) or abs(sum(fractions.values()) - 1.0) > 1e-6:
            raise SplitError(f"split.fractions must be >= 0 and add up to 1, got {fractions}")
        self.fractions = fractions

        self.device_on = bool(split.get("device_holdout", {}).get("enabled", False))
        self.temporal_on = bool(split.get("temporal_holdout", {}).get("enabled", False))
        min_dev = _value(split.get("device_holdout", {}).get("min_devices", DEFAULT_MIN_DEVICES))
        self.min_devices = int(min_dev)


def _value(node: Any) -> Any:
    # param records are {value: ...}, plain values pass through
    return node["value"] if isinstance(node, Mapping) and "value" in node else node


# ---- small helpers ----

def _eligible(df: pd.DataFrame) -> pd.Series:
    # rows that count for class coverage (ambiguous-excluded and insufficient
    # context rows don't). falls back to all rows if the column isn't there yet
    if ELIGIBLE_COLUMN in df.columns:
        return df[ELIGIBLE_COLUMN].fillna(False).astype(bool)
    return pd.Series(True, index=df.index)


def _classes_present(df: pd.DataFrame, mask: pd.Series) -> set[Label]:
    return {Label(v) for v in df.loc[mask, LABEL_COLUMN].dropna().unique()}


def _missing_classes(present: set[Label]) -> list[str]:
    return [lab.value for lab in Label if lab not in present]


def _scenario_table(df: pd.DataFrame, cfg: _SplitConfig, times: pd.Series | None) -> pd.DataFrame:
    """one row per scenario: stratum, start, end. a scenario can have rows of
    different scenario_type (a faulty sensor inside an event), the most common
    one is its stratum, ties go to the first alphabetically"""
    grouped = df.groupby(cfg.group_col, sort=True)
    if cfg.strat_col:
        stratum = grouped[cfg.strat_col].agg(lambda s: s.astype(str).value_counts().sort_index().idxmax())
    else:
        stratum = pd.Series("all", index=grouped.size().index)
    table = pd.DataFrame({"stratum": stratum})
    if times is not None:
        table["start"] = times.groupby(df[cfg.group_col]).min()
        table["end"] = times.groupby(df[cfg.group_col]).max()
    return table


# ---- holdouts ----

def _device_holdout(
    df: pd.DataFrame, eligible: pd.Series, cfg: _SplitConfig, rng: np.random.Generator
) -> tuple[str | None, set[str], str | None]:
    """pick one device, returns (device, scenario ids it appears in, skip reason)"""
    if DEVICE_COLUMN not in df.columns or df[DEVICE_COLUMN].isna().any():
        return None, set(), f"{DEVICE_COLUMN} is missing or has nulls"

    devices = sorted(df[DEVICE_COLUMN].astype(str).unique())
    if len(devices) < cfg.min_devices:
        return None, set(), f"only {len(devices)} distinct device(s), need at least {cfg.min_devices}"

    # the held-out device has to carry more than one class
    candidates = [
        d for d in devices
        if len(_classes_present(df, eligible & (df[DEVICE_COLUMN].astype(str) == d))) > 1
    ]
    if not candidates:
        return None, set(), "no device has more than one class"

    chosen = str(candidates[int(rng.integers(len(candidates)))])
    ids = set(df.loc[df[DEVICE_COLUMN].astype(str) == chosen, cfg.group_col].astype(str))
    return chosen, ids, None


def _temporal_holdout(
    df: pd.DataFrame, eligible: pd.Series, scen: pd.DataFrame, times: pd.Series | None, cfg: _SplitConfig
) -> tuple[set[str], pd.Timestamp | None, str | None]:
    """last test-fraction of the time span goes to test. a scenario that reaches
    into that period goes to test as a whole, so train never contains rows later
    than the start of test. returns (scenario ids, cutoff, skip reason)"""
    if times is None:
        return set(), None, f"{TIME_COLUMN} column is missing"
    if times.isna().any():
        return set(), None, f"{TIME_COLUMN} has {int(times.isna().sum())} null/unparseable value(s)"

    t_min, t_max = times.min(), times.max()
    if t_max <= t_min:
        return set(), None, "timeline has no length, cannot hold out a later period"

    cutoff = t_min + (1.0 - cfg.fractions[SplitName.TEST]) * (t_max - t_min)
    later = {str(s) for s in scen.index[scen["end"] >= cutoff]}
    if not later:
        return set(), cutoff, "no scenario reaches into the held-out period"
    if len(later) == len(scen):
        return set(), cutoff, "every scenario reaches into the held-out period, nothing left to train on"

    in_later = df[cfg.group_col].astype(str).isin(later)
    missing = _missing_classes(_classes_present(df, eligible & in_later))
    if missing:
        return set(), cutoff, f"held-out period is missing class(es): {', '.join(missing)}"
    return later, cutoff, None


# ---- filling the rest ----

def _deal(n: int, quotas: Mapping[SplitName, int]) -> list[SplitName]:
    """spread the splits evenly over n positions, the split that is furthest
    behind its share goes next (ties: train, val, test)"""
    assigned = {s: 0 for s in quotas}
    out: list[SplitName] = []
    for i in range(n):
        open_splits = [s for s in quotas if assigned[s] < quotas[s]]
        pick = max(open_splits, key=lambda s: quotas[s] * (i + 1) / n - assigned[s])
        assigned[pick] += 1
        out.append(pick)
    return out


def _fill_remaining(
    scen: pd.DataFrame, pre: Mapping[str, SplitName], cfg: _SplitConfig, rng: np.random.Generator
) -> tuple[dict[str, SplitName], list[str]]:
    """random 70/15/15 (from the config) over the scenarios that have no split yet.
    fractions are over ALL scenarios, scenarios already in test from a holdout
    count towards the test share. sorted by stratum with a shuffle inside each
    stratum, so every scenario_type gets about its share"""
    notes: list[str] = []
    n_total = len(scen)
    remaining = [str(s) for s in scen.index if str(s) not in pre]
    if not remaining:
        return {}, notes

    sub = scen.loc[[s for s in scen.index if str(s) not in pre]]
    ordered: list[str] = []
    for stratum in sorted(sub["stratum"].unique()):
        ids = [str(s) for s in sub.index[sub["stratum"] == stratum]]
        ordered += [ids[i] for i in rng.permutation(len(ids))]

    pre_test = sum(1 for v in pre.values() if v is SplitName.TEST)
    test_target = int(cfg.fractions[SplitName.TEST] * n_total + 0.5)
    if pre_test > test_target:
        notes.append(f"holdouts put {pre_test} scenario(s) in test, above the {test_target} the test fraction asks for")

    need_val = min(int(cfg.fractions[SplitName.VAL] * n_total + 0.5), len(ordered))
    need_test = min(max(0, test_target - pre_test), len(ordered) - need_val)
    quotas = {
        SplitName.TRAIN: len(ordered) - need_val - need_test,
        SplitName.VAL: need_val,
        SplitName.TEST: need_test,
    }
    return dict(zip(ordered, _deal(len(ordered), quotas))), notes


# ---- public api ----

def assign_splits(df: pd.DataFrame, labeling_cfg: Mapping[str, Any]) -> tuple[pd.DataFrame, dict[str, str]]:
    """add `split` (train/val/test), `split_device` and `split_temporal` to a copy of df.

    order: device holdout -> temporal holdout -> random fill for the rest.
    returns (new df, skip reasons). skip reasons use the keys "device" and
    "temporal" for holdouts that were skipped, and "classes:<split>" for a split
    that is missing a class. use manifest_holdout_skips() for the manifest.

    split_device / split_temporal are only set to "test" on the rows of the
    held-out device / the rows of scenarios in the held-out period (else <NA>).
    other devices can still sit in test if they share a scenario with the held-out
    device, scenario integrity wins over device purity.

    extra info (chosen device, cutoff, notes, scenario counts) is in df.attrs["split_info"].
    raises SplitError for a bad config / bad input only.
    """
    cfg = _SplitConfig(labeling_cfg)

    needed = [cfg.group_col, LABEL_COLUMN] + ([cfg.strat_col] if cfg.strat_col else [])
    absent = [c for c in needed if c not in df.columns]
    if absent:
        raise SplitError(f"dataframe is missing column(s): {absent}")
    if df.empty:
        raise SplitError("dataframe is empty")
    if df[cfg.group_col].isna().any():
        raise SplitError(f"{cfg.group_col} has nulls, every row needs a scenario")

    work = df.copy()
    work[cfg.group_col] = work[cfg.group_col].astype(str)
    eligible = _eligible(work)
    times = pd.to_datetime(work[TIME_COLUMN], utc=True, errors="coerce") if TIME_COLUMN in work.columns else None
    scen = _scenario_table(work, cfg, times)

    skips: dict[str, str] = {}
    info: dict[str, Any] = {"held_out_device": None, "temporal_cutoff": None, "notes": []}
    pre: dict[str, SplitName] = {}

    # separate streams so turning a holdout on/off doesn't change the other draws
    rng_device = np.random.default_rng([cfg.seed, 1])
    rng_fill = np.random.default_rng([cfg.seed, 2])

    device, device_ids, temporal_ids = None, set(), set()
    if cfg.device_on:
        device, device_ids, why = _device_holdout(work, eligible, cfg, rng_device)
        if why:
            skips["device"] = why
        else:
            info["held_out_device"] = device
            pre.update({sid: SplitName.TEST for sid in device_ids})
            pulled = work[cfg.group_col].isin(device_ids) & (work[DEVICE_COLUMN].astype(str) != device)
            if pulled.any():
                info["notes"].append(
                    f"{int(pulled.sum())} row(s) of other devices are in test because they share a scenario with the held-out device"
                )

    if cfg.temporal_on:
        temporal_ids, cutoff, why = _temporal_holdout(work, eligible, scen, times, cfg)
        if why:
            skips["temporal"] = why
        else:
            info["temporal_cutoff"] = cutoff.isoformat()
            pre.update({sid: SplitName.TEST for sid in temporal_ids})

    filled, notes = _fill_remaining(scen, pre, cfg, rng_fill)
    info["notes"] += notes
    assignment = {**filled, **pre}

    out = df.copy()
    out["split"] = work[cfg.group_col].map(lambda s: assignment[s].value).astype("string")
    out["split_device"] = pd.Series(pd.NA, index=out.index, dtype="string")
    out["split_temporal"] = pd.Series(pd.NA, index=out.index, dtype="string")
    if info["held_out_device"] is not None:
        out.loc[work[DEVICE_COLUMN].astype(str) == device, "split_device"] = SplitName.TEST.value
    if temporal_ids:
        out.loc[work[cfg.group_col].isin(temporal_ids), "split_temporal"] = SplitName.TEST.value

    _assert_scenarios_intact(out, work[cfg.group_col])
    skips.update(_class_gaps(out, eligible))
    info["scenarios"] = {n.value: sum(1 for v in assignment.values() if v is n) for n in SplitName}
    out.attrs["split_info"] = info
    return out, skips


def _assert_scenarios_intact(out: pd.DataFrame, groups: pd.Series) -> None:
    # internal safety net, should never trigger
    per = out.groupby(groups)["split"].nunique()
    broken = per[per > 1]
    if not broken.empty:
        raise SplitError(f"scenario(s) split across partitions: {list(broken.index[:5])}")


def _class_gaps(out: pd.DataFrame, eligible: pd.Series) -> dict[str, str]:
    """every split should hold all three classes (rows that count). a gap is
    recorded, not raised"""
    gaps: dict[str, str] = {}
    for name in SplitName:
        rows = out["split"] == name.value
        if not rows.any():
            gaps[f"classes:{name.value}"] = "split has no rows"
            continue
        missing = _missing_classes(_classes_present(out, rows & eligible))
        if missing:
            gaps[f"classes:{name.value}"] = f"missing class(es): {', '.join(missing)}"
    return gaps


def manifest_holdout_skips(skips: Mapping[str, str]) -> dict[str, str]:
    """only the holdout skips, in the shape DatasetManifest.holdout_skips wants"""
    return {k: v for k, v in skips.items() if k in MANIFEST_SKIP_KEYS}


def class_counts(df: pd.DataFrame) -> dict[SplitName, dict[Label, int]]:
    """rows per split and class (zeros included), for DatasetManifest.class_counts"""
    counts = {name: {lab: 0 for lab in Label} for name in SplitName}
    for (split, label), n in df.groupby(["split", LABEL_COLUMN]).size().items():
        counts[SplitName(split)][Label(label)] = int(n)
    return counts