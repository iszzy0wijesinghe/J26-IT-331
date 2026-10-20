"""Group-aware, frozen splits (spec section 15). Never random row splits."""
from __future__ import annotations
import random
from collections import defaultdict
from types import SimpleNamespace

SplitMap = dict[str, str]

def _get_cfg_val(cfg, dotted_key, default=None):
    """Get a value from dict or SimpleNamespace using a dotted key."""
    node = cfg
    for key in dotted_key.split("."):
        if isinstance(node, dict):
            node = node.get(key)
        elif isinstance(node, SimpleNamespace):
            node = getattr(node, key, None)
        else:
            return default
    return node if node is not None else default

def assign_scenario_splits(scenarios: list[tuple[str, str, int]], cfg, seed: int) -> SplitMap:
    """Scenario-grouped split, stratified by scenario type at the group level."""
    rng = random.Random(f"{seed}-scenario-split")
    by_type: dict[str, list[str]] = defaultdict(list)
    for sid, stype, _ in sorted(scenarios, key=lambda s: s[2]):
        by_type[stype].append(sid)

    val_ratio = _get_cfg_val(cfg, "split.val", 0.15)
    test_ratio = _get_cfg_val(cfg, "split.test", 0.15)
    if isinstance(val_ratio, dict): val_ratio = val_ratio.get("value", 0.15)
    if isinstance(test_ratio, dict): test_ratio = test_ratio.get("value", 0.15)

    assignment: SplitMap = {}
    for _stype, ids in sorted(by_type.items()):
        shuffled = ids[:]
        rng.shuffle(shuffled)
        n = len(shuffled)
        n_val = max(1, round(n * val_ratio))
        n_test = max(1, round(n * test_ratio))
        n_train = max(1, n - n_val - n_test)
        for k, sid in enumerate(shuffled):
            if k < n_train: assignment[sid] = "train"
            elif k < n_train + n_val: assignment[sid] = "val"
            else: assignment[sid] = "test"
    return assignment

def assign_temporal_splits(scenarios: list[tuple[str, str, int]], cfg) -> SplitMap:
    """Earlier scenarios train, later scenarios test."""
    ordered = sorted(scenarios, key=lambda s: s[2])
    n = len(ordered)
    train_ratio = _get_cfg_val(cfg, "split.train", 0.70)
    val_ratio = _get_cfg_val(cfg, "split.val", 0.15)
    if isinstance(train_ratio, dict): train_ratio = train_ratio.get("value", 0.70)
    if isinstance(val_ratio, dict): val_ratio = val_ratio.get("value", 0.15)
    n_train = round(n * train_ratio)
    n_val = round(n * val_ratio)
    out: SplitMap = {}
    for k, (sid, _, _) in enumerate(ordered):
        out[sid] = "train" if k < n_train else ("val" if k < n_train + n_val else "test")
    return out

def assign_device_holdout(device_ids: list[str], cfg, seed: int) -> set[str]:
    """Devices held out entirely for the device-holdout robustness run."""
    unique = sorted(set(device_ids))
    holdout_count = _get_cfg_val(cfg, "split.device_holdout_count", 1)
    if isinstance(holdout_count, dict): holdout_count = holdout_count.get("value", 1)
    if len(unique) <= holdout_count + 2: return set()
    rng = random.Random(f"{seed}-device-holdout")
    return set(rng.sample(unique, holdout_count))