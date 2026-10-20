"""As-of neighbour context (spec section 7.3 and 14.3)."""
from __future__ import annotations
import statistics
from types import SimpleNamespace
from components.c1_credibility.datasets.generator import Scenario, SensorSeries

def own_baseline(series: list[float | None], t: int, window: int) -> float | None:
    past = [v for v in series[max(0, t - window) : t] if v is not None]
    if len(past) < 3: return None
    return statistics.fmean(past)

def own_change(series: list[float | None], t: int, window: int) -> float | None:
    value = series[t]
    baseline = own_baseline(series, t, window)
    if value is None or baseline is None: return None
    return value - baseline

def fresh_neighbours(sc: Scenario, target_idx: int, t: int, cfg: SimpleNamespace) -> list[SensorSeries]:
    max_age_s = cfg.neighbour.max_age_multiplier * sc.dt_s
    fresh: list[SensorSeries] = []
    for j, sensor in enumerate(sc.sensors):
        if j == target_idx: continue
        if not sensor.avail[t]: continue
        if sensor.lag_steps[t] * sc.dt_s > max_age_s: continue
        if sensor.obs[t] is None: continue
        fresh.append(sensor)
    return fresh

def neighbour_features(sc: Scenario, target_idx: int, t: int, cfg: SimpleNamespace) -> dict[str, float | int | None]:
    window = cfg.features.window_steps
    fresh = fresh_neighbours(sc, target_idx, t, cfg)
    changes = [c for s in fresh if (c := own_change(s.obs, t, window)) is not None]
    consensus = statistics.median(changes) if changes else None
    spread = statistics.pstdev(changes) if len(changes) >= 2 else None
    agree = sum(1 for c in changes if c >= cfg.features.rise_detect_pct) / len(changes) if changes else None
    target_change = own_change(sc.sensors[target_idx].obs, t, window)
    diff = target_change - consensus if (target_change is not None and consensus is not None) else None
    return {
        "n_neighbours_fresh": len(fresh),
        "neighbour_consensus_change": None if consensus is None else round(consensus, 4),
        "target_minus_consensus": None if diff is None else round(diff, 4),
        "neighbour_change_spread": None if spread is None else round(spread, 4),
        "neighbour_rise_agree_frac": None if agree is None else round(agree, 4),
    }