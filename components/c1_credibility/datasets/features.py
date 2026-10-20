"""As-of feature builder for C1 (spec section 14.3)."""
from __future__ import annotations
import statistics
from types import SimpleNamespace
from components.c1_credibility.datasets.generator import Scenario
from components.c1_credibility.datasets.neighbours import neighbour_features
from components.c1_credibility.datasets.rainfall import (
    classify_rainfall, rain_available, steps_since_rain, window_sum,
)
from shared.enums import C1ContextStatus

def context_status(sc: Scenario, target_idx: int, t: int, n_fresh: int, cfg: SimpleNamespace) -> C1ContextStatus:
    if t < cfg.context.min_history_obs: return C1ContextStatus.INSUFFICIENT_CONTEXT
    if not rain_available(sc.rain_obs, t, cfg.context.rain_window_steps_required): return C1ContextStatus.INSUFFICIENT_CONTEXT
    total_neighbours = len(sc.sensors) - 1
    if n_fresh >= total_neighbours: return C1ContextStatus.COMPLETE
    if n_fresh >= cfg.neighbour.min_count: return C1ContextStatus.PARTIAL
    return C1ContextStatus.INSUFFICIENT_CONTEXT

def build_features(sc: Scenario, target_idx: int, t: int, cfg: SimpleNamespace) -> tuple[dict[str, object], C1ContextStatus]:
    sensor = sc.sensors[target_idx]
    series = sensor.obs
    window = cfg.features.window_steps
    dt_min = sc.dt_s / 60.0
    value = series[t]
    prev_t = next((p for p in range(t - 1, -1, -1) if series[p] is not None), None)
    gap = None if prev_t is None else t - prev_t
    delta = None
    if value is not None and prev_t is not None and gap:
        delta = round((value - series[prev_t]) / (gap * dt_min), 4)
    past = [v for v in series[max(0, t - window) : t] if v is not None]
    base_mean = statistics.fmean(past) if len(past) >= 3 else None
    base_std = statistics.pstdev(past) if len(past) >= 3 else None
    minus_base = None if (value is None or base_mean is None) else round(value - base_mean, 4)
    stuck = 0
    if value is not None:
        for back in range(t, -1, -1):
            if series[back] is not None and series[back] == value: stuck += 1
            else: break
    failures = 0
    for back in range(t, -1, -1):
        if series[back] is None: failures += 1
        else: break
    rain_1h = window_sum(sc.rain_obs, t, 12)
    nb = neighbour_features(sc, target_idx, t, cfg)
    features: dict[str, object] = {
        "mode": cfg.sim.mode, "dt_s": sc.dt_s, "value": value, "value_present": int(value is not None),
        "delta_prev_pct_per_min": delta, "obs_gap_steps": gap,
        "baseline_mean": None if base_mean is None else round(base_mean, 4),
        "baseline_std": None if base_std is None else round(base_std, 4),
        "value_minus_baseline": minus_base, "stuck_run_len": stuck,
        "rain_15m_mm": window_sum(sc.rain_obs, t, 3), "rain_1h_mm": rain_1h,
        "rain_3h_mm": window_sum(sc.rain_obs, t, 36), "steps_since_rain": steps_since_rain(sc.rain_obs, t),
        "rainfall_regime": classify_rainfall(rain_1h, cfg), **nb,
        "device_voltage": sensor.voltage[t], "recent_read_failures": failures, "history_obs": min(t, window),
    }
    status = context_status(sc, target_idx, t, int(nb["n_neighbours_fresh"]), cfg)
    return features, status