"""Dataset validation (spec sections 7.5, 14.5, 15 and 16.1)."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from components.c1_credibility.datasets import generator as generator_module
from components.c1_credibility.datasets.config import is_approved
from components.c1_credibility.datasets.generator import Scenario
from components.c1_credibility.datasets.labels import precompute_activity
from components.c1_credibility.datasets.schemas import FEATURE_COLUMNS, FORBIDDEN_FEATURES
Row = dict[str, Any]
CLASSES = ("CLEAN", "ANOMALY", "VALID_EVENT")

class ValidationError(RuntimeError): pass

def check_feature_columns() -> None:
    bad = sorted(set(FEATURE_COLUMNS) & FORBIDDEN_FEATURES)
    if bad: raise ValidationError(f"Forbidden fields used as features: {bad}")

def check_generator_is_regime_free() -> None:
    source = Path(generator_module.__file__).read_text(encoding="utf-8").lower()
    if "regime" in source: raise ValidationError("generator.py must not reference rainfall regimes")

def check_split_integrity(rows: list[Row]) -> None:
    for column in ("split", "split_temporal"):
        seen: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            seen[row["scenario_id"]].add(row[column])
            if row["event_id"]: seen[f"event:{row['scenario_id']}:{row['event_id']}"].add(row[column])
        crossing = [k for k, v in seen.items() if len(v) > 1]
        if crossing: raise ValidationError(f"Groups cross {column}: {crossing[:3]}")

def check_classes_per_split(rows: list[Row]) -> None:
    present: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row["train_eligible"] and row["credibility_label"]: present[row["split"]].add(row["credibility_label"])
    for split in ("train", "val", "test"):
        missing = set(CLASSES) - present[split]
        if missing: raise ValidationError(f"Split '{split}' is missing classes: {sorted(missing)}")

def check_clean_evidence(rows: list[Row], cfg: SimpleNamespace) -> dict[str, int]:
    out_of_range = 0
    too_fast = 0
    for row in rows:
        if row["credibility_label"] != "CLEAN" or row["value"] is None: continue
        if not cfg.valid_range.min <= row["value"] <= cfg.valid_range.max: out_of_range += 1
        delta = row["delta_prev_pct_per_min"]
        if row["_prev_faulty"]: continue
        if delta is not None and abs(delta) > cfg.clean.max_normal_rate_pct_per_min: too_fast += 1
    if out_of_range or too_fast: raise ValidationError(f"CLEAN rows violate observable evidence: range={out_of_range}, rate={too_fast}")
    return {"clean_out_of_range": out_of_range, "clean_too_fast": too_fast}

def check_event_coherence(scenarios: list[Scenario], rows: list[Row], cfg: SimpleNamespace) -> dict[str, int]:
    lag_max = round(cfg.rain.lag_max_min * 60 / cfg.sim.sample_interval_s)
    violations = 0
    checked = 0
    for sc in scenarios:
        onset = {e.event_id: e.onset for e in sc.events}
        for sensor in sc.sensors:
            active = precompute_activity(sc, sensor, cfg).active_event
            for t in range(sc.steps):
                event_id = active[t]
                if event_id is None or (t > 0 and active[t - 1] == event_id): continue
                checked += 1
                support = sum(sc.rain_true[max(0, t - lag_max) : t + 1])
                if t < onset[event_id] or support < cfg.rain.support_min_mm: violations += 1
    orphan = sum(1 for r in rows if r["credibility_label"] == "VALID_EVENT" and not r["event_id"])
    if violations or orphan: raise ValidationError(f"Event coherence failed: {violations} runs without rain support, {orphan} VALID_EVENT rows without event_id")
    return {"event_runs_checked": checked, "event_coherence_violations": violations}

def detectability_report(rows: list[Row]) -> dict[str, float | int]:
    fault_rows = [r for r in rows if r["fault_type_truth"]]
    undetectable = [r for r in fault_rows if r["ambiguity_reason"] == "FAULT_BELOW_DETECTABILITY"]
    return {"fault_rows": len(fault_rows), "fault_rows_below_detectability": len(undetectable), "fraction_undetectable": round(len(undetectable) / len(fault_rows), 4) if fault_rows else 0.0}

def check_freeze(cfg: SimpleNamespace, freeze: bool) -> None:
    if freeze and not is_approved(cfg): raise ValidationError("Cannot freeze: parameter_status is PROVISIONAL. Justify every parameter and set parameter_status = 'APPROVED' in c1_labeling_v1.toml.")

def validate_dataset(scenarios: list[Scenario], rows: list[Row], cfg: SimpleNamespace, freeze: bool) -> dict[str, Any]:
    check_freeze(cfg, freeze)
    check_feature_columns()
    check_generator_is_regime_free()
    check_split_integrity(rows)
    check_classes_per_split(rows)
    report: dict[str, Any] = {}
    report.update(check_clean_evidence(rows, cfg))
    report.update(check_event_coherence(scenarios, rows, cfg))
    report.update(detectability_report(rows))
    return report