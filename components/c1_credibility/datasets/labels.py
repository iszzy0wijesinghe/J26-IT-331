"""Label assignment from generator truth (spec sections 6, 8, 9 and 10)."""
from __future__ import annotations
import math
from dataclasses import dataclass
from types import SimpleNamespace
from components.c1_credibility.datasets.generator import Scenario, SensorSeries

LABEL_SOURCE = "SYNTHETIC_GENERATOR_TRUTH"
_ALWAYS_DETECTABLE = {"DROPOUT", "OUT_OF_RANGE", "EXCESSIVE_NOISE"}
TRAINING_KEPT_REASON = "BORDERLINE_EXTREME"

@dataclass
class Activity:
    active_event: list[str | None]
    max_component: list[float]
    max_event_id: list[str | None]
    overlap: list[bool]

@dataclass
class LabelResult:
    truth_label: str
    event_id: str | None
    event_component: float
    ambiguous: bool
    ambiguity_reason: str
    borderline_extreme: bool
    fault_id: str | None
    fault_type: str | None
    fault_effect: float | None

def precompute_activity(sc: Scenario, sensor: SensorSeries, cfg: SimpleNamespace) -> Activity:
    steps = sc.steps
    floor = cfg.event.min_effect_sigma * sensor.sigma
    eps = cfg.event.response_epsilon_sigma * sensor.sigma
    min_run = max(cfg.event.min_duration_obs, math.ceil(cfg.event.min_duration_min * 60 / sc.dt_s))
    active: list[str | None] = [None] * steps
    best_comp = [0.0] * steps
    best_id: list[str | None] = [None] * steps
    responding = [0] * steps
    for event_id, comp in sensor.event_comp.items():
        for t in range(steps):
            if comp[t] >= eps: responding[t] += 1
            if comp[t] > best_comp[t]:
                best_comp[t] = comp[t]
                best_id[t] = event_id
        t = 0
        while t < steps:
            if comp[t] >= floor:
                start = t
                while t < steps and comp[t] >= floor: t += 1
                if t - start >= min_run:
                    for k in range(start, t):
                        if active[k] is None or comp[k] > sensor.event_comp[active[k]][k]: active[k] = event_id
            else: t += 1
    return Activity(active, best_comp, best_id, [n >= 2 for n in responding])

def _fault_threshold(fault_type: str, cfg: SimpleNamespace) -> float | None:
    if fault_type in _ALWAYS_DETECTABLE: return None
    return {
        "SENSOR_SPIKE": cfg.fault.spike_min_sigma,
        "SENSOR_DRIFT": cfg.fault.drift_floor_sigma,
        "BIAS": cfg.fault.bias_min_sigma,
    }.get(fault_type, cfg.fault.floor_sigma)

def label_observation(sc: Scenario, target_idx: int, t: int, activities: list[Activity], cfg: SimpleNamespace) -> LabelResult:
    sensor = sc.sensors[target_idx]
    act = activities[target_idx]
    floor = cfg.event.min_effect_sigma * sensor.sigma
    fault_type = sensor.fault_type[t]
    if fault_type is not None:
        threshold = _fault_threshold(fault_type, cfg)
        effect = sensor.fault_effect[t]
        detectable = threshold is None or effect is None or abs(effect) >= threshold * sensor.sigma
        return LabelResult(
            truth_label="ANOMALY", event_id=None, event_component=act.max_component[t],
            ambiguous=not detectable, ambiguity_reason="" if detectable else "FAULT_BELOW_DETECTABILITY",
            borderline_extreme=False, fault_id=sensor.fault_id[t], fault_type=fault_type, fault_effect=effect,
        )
    event_id = act.active_event[t]
    label = "VALID_EVENT" if event_id else "CLEAN"
    reason = ""
    borderline = False
    if act.overlap[t]: reason = "OVERLAPPING_EVENTS"
    elif event_id:
        eligible = [j for j, other in enumerate(sc.sensors) if j != target_idx and other.fault_type[t] is None]
        if eligible:
            responding = sum(1 for j in eligible if activities[j].active_event[t] == event_id)
            frac = responding / len(eligible)
            if responding == 0: reason = "ISOLATED_RESPONSE"
            elif frac < cfg.neighbour.agreement_fraction_min: reason = "PARTIAL_NEIGHBOUR_RESPONSE"
        if not reason and act.max_component[t] < cfg.event.borderline_factor * floor:
            reason = TRAINING_KEPT_REASON
            borderline = True
    return LabelResult(
        truth_label=label, event_id=event_id, event_component=act.max_component[t],
        ambiguous=bool(reason), ambiguity_reason=reason, borderline_extreme=borderline,
        fault_id=None, fault_type=None, fault_effect=None,
    )

def is_train_eligible(context_ok: bool, ambiguous: bool, reason: str) -> bool:
    return context_ok and (not ambiguous or reason == TRAINING_KEPT_REASON)