"""As-of rainfall features and the rainfall class feature (feature builder only)."""
from __future__ import annotations
from types import SimpleNamespace

def window_sum(rain_obs: list[float | None], t: int, steps: int) -> float | None:
    if t - steps + 1 < 0: return None
    total = 0.0
    for value in rain_obs[t - steps + 1 : t + 1]:
        if value is None: return None
        total += value
    return round(total, 4)

def steps_since_rain(rain_obs: list[float | None], t: int, cap: int = 288) -> int:
    for back in range(0, min(t, cap) + 1):
        value = rain_obs[t - back]
        if value is not None and value > 0.05: return back
    return cap

def classify_rainfall(rain_1h_mm: float | None, cfg: SimpleNamespace) -> str:
    if rain_1h_mm is None: return "UNKNOWN"
    r = cfg.regimes
    if rain_1h_mm < r.dry_below: return "DRY"
    if rain_1h_mm < r.light_below: return "LIGHT"
    if rain_1h_mm < r.moderate_below: return "MODERATE"
    if rain_1h_mm < r.heavy_below: return "HEAVY"
    return "EXTREME"

def rain_available(rain_obs: list[float | None], t: int, required_steps: int) -> bool:
    return window_sum(rain_obs, t, required_steps) is not None