"""Deterministic synthetic scenario generator for the C1 soil-moisture dataset."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

SCENARIO_TYPES = [
    "DRY_BASELINE",
    "DRY_FAULT",
    "EVENT",
    "EVENT_FAULT",
    "LIGHT_RAIN",
    "OUTAGE",
]

FAULT_FAMILIES = [
    "SENSOR_SPIKE",
    "STUCK_AT",
    "SENSOR_DRIFT",
    "BIAS",
    "DROPOUT",
    "EXCESSIVE_NOISE",
    "OUT_OF_RANGE",
    "QUANTIZATION",
]

ZONES = ["ZONE-A", "ZONE-B", "ZONE-C"]
BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass
class Event:
    event_id: str
    onset: int
    duration: int
    depth_mm: float


@dataclass
class FaultRecord:
    fault_id: str
    fault_type: str
    sensor_idx: int
    start: int
    end: int


@dataclass
class SensorSeries:
    sensor_instance_id: str
    device_id: str
    zone_id: str
    sigma: float
    true: list[float]
    obs_clean: list[float]
    obs: list[float | None]
    avail: list[bool]
    lag_steps: list[int]
    voltage: list[float]
    fault_id: list[str | None]
    fault_type: list[str | None]
    fault_effect: list[float | None]
    event_comp: dict[str, list[float]] = field(default_factory=dict)


@dataclass
class Scenario:
    scenario_id: str
    scenario_type: str
    index: int
    zone_id: str
    start_time: datetime
    dt_s: int
    steps: int
    rain_true: list[float]
    rain_obs: list[float | None]
    events: list[Event]
    faults: list[FaultRecord]
    sensors: list[SensorSeries]


@dataclass
class _SoilParams:
    base: float
    sat: float
    gain: float
    lag: int
    drain: float


def _simulate_soil(rain: list[float], p: _SoilParams, steps: int) -> list[float]:
    theta = p.base
    out: list[float] = []
    for t in range(steps):
        out.append(theta)
        r = rain[t - p.lag] if t - p.lag >= 0 else 0.0
        theta += p.gain * r * (1.0 - theta / p.sat) - p.drain * (theta - p.base)
        theta = min(max(theta, 0.0), p.sat)
    return out


def _profile(duration: int, depth: float, onset: int, steps: int) -> list[float]:
    """Triangular rainfall profile that sums to the event depth."""
    weights = [1.0 - abs(2.0 * k / max(duration - 1, 1) - 1.0) + 0.1 for k in range(duration)]
    total = sum(weights)
    series = [0.0] * steps
    for k, w in enumerate(weights):
        if onset + k < steps:
            series[onset + k] = depth * w / total
    return series


def fault_family_for(index: int, seed: int) -> str:
    """Pick the fault family for fault-scenario `index`, mixing families across types."""
    fault_n = (index // 6) * 2 + (0 if index % 6 == 1 else 1)
    cycle = fault_n // len(FAULT_FAMILIES)
    order = FAULT_FAMILIES[:]
    random.Random(f"{seed}-family-order-{cycle}").shuffle(order)
    return order[fault_n % len(FAULT_FAMILIES)]


def _plan_rain(
    scenario_type: str, rng: random.Random, steps: int, sid: str
) -> tuple[list[float], list[Event], list[list[float]]]:
    background = [0.0] * steps
    if scenario_type in {"LIGHT_RAIN", "EVENT", "EVENT_FAULT", "OUTAGE"}:
        n_drizzle = rng.randint(2, 5) if scenario_type == "LIGHT_RAIN" else rng.randint(0, 2)
        for _ in range(n_drizzle):
            onset = rng.randint(10, steps - 20)
            profile = _profile(rng.randint(2, 6), rng.uniform(0.3, 2.0), onset, steps)
            background = [a + b for a, b in zip(background, profile, strict=True)]

    events: list[Event] = []
    profiles: list[list[float]] = []
    if scenario_type in {"EVENT", "EVENT_FAULT", "OUTAGE"} or (
        scenario_type == "LIGHT_RAIN" and rng.random() < 0.5
    ):
        n_events = 1 if scenario_type == "LIGHT_RAIN" else (2 if rng.random() < 0.3 else 1)
        for n in range(n_events):
            if n == 1 and rng.random() < 0.15:
                onset = events[0].onset + rng.randint(2, 10)  # deliberate overlap
            else:
                onset = rng.randint(40, max(41, steps - 140))
            depth = (
                rng.uniform(1.0, 6.0) if scenario_type == "LIGHT_RAIN" else rng.uniform(1.0, 45.0)
            )
            duration = rng.randint(6, 36)
            event = Event(f"{sid}-EV{n + 1}", onset, duration, depth)
            events.append(event)
            profiles.append(_profile(duration, depth, onset, steps))
    return background, events, profiles


def _apply_fault(
    sensor: SensorSeries,
    fault: FaultRecord,
    cfg: SimpleNamespace,
    rng: random.Random,
) -> None:
    sigma = sensor.sigma
    start, end = fault.start, fault.end
    window = range(start, end + 1)
    new: dict[int, float | None] = {}
    ftype = fault.fault_type

    if ftype == "SENSOR_SPIKE":
        sign = rng.choice([-1.0, 1.0])
        offset = sign * rng.uniform(10.0, 50.0) * sigma
        for t in window:
            new[t] = sensor.obs_clean[t] + offset
    elif ftype == "STUCK_AT":
        frozen = sensor.obs_clean[start]
        for t in window:
            new[t] = frozen
    elif ftype == "SENSOR_DRIFT":
        sign = rng.choice([-1.0, 1.0])
        final = rng.uniform(8.0, 30.0) * sigma
        span = max(end - start, 1)
        for t in window:
            new[t] = sensor.obs_clean[t] + sign * final * (t - start) / span
    elif ftype == "BIAS":
        sign = rng.choice([-1.0, 1.0])
        offset = sign * rng.uniform(4.0, 15.0) * sigma
        for t in window:
            new[t] = sensor.obs_clean[t] + offset
    elif ftype == "DROPOUT":
        for t in window:
            new[t] = None
    elif ftype == "EXCESSIVE_NOISE":
        factor = rng.uniform(cfg.fault.noise_factor_min + 1.0, cfg.fault.noise_factor_min + 6.0)
        for t in window:
            new[t] = sensor.true[t] + rng.gauss(0.0, sigma * factor)
    elif ftype == "OUT_OF_RANGE":
        for t in window:
            new[t] = rng.uniform(105.0, 140.0) if rng.random() < 0.5 else rng.uniform(-20.0, -2.0)
    elif ftype == "QUANTIZATION":
        step = cfg.fault.quant_step_pct
        for t in window:
            new[t] = round(sensor.obs_clean[t] / step) * step
    else:  # pragma: no cover - guarded by FAULT_FAMILIES
        raise ValueError(f"Unknown fault family {ftype}")

    for t, value in new.items():
        sensor.obs[t] = None if value is None else round(value, 3)
        sensor.fault_id[t] = fault.fault_id
        sensor.fault_type[t] = ftype
        sensor.fault_effect[t] = (
            None if value is None else round(sensor.obs[t] - sensor.obs_clean[t], 4)
        )

    if (
        ftype in {"DROPOUT", "EXCESSIVE_NOISE", "QUANTIZATION", "OUT_OF_RANGE"}
        and rng.random() < 0.7
    ):
        for t in window:
            sensor.voltage[t] = round(rng.uniform(2.9, 3.2), 3)


def _plan_fault(
    scenario_type: str,
    family: str,
    sensor: SensorSeries,
    events: list[Event],
    steps: int,
    cfg: SimpleNamespace,
    rng: random.Random,
    sid: str,
    sensor_idx: int,
    fault_no: int = 1,
) -> FaultRecord:
    lengths = {
        "SENSOR_SPIKE": (1, 3),
        "STUCK_AT": (8, 30),
        "SENSOR_DRIFT": (24, 80),
        "BIAS": (24, 120),
        "DROPOUT": (1, 6),
        "EXCESSIVE_NOISE": (12, 60),
        "OUT_OF_RANGE": (1, 3),
        "QUANTIZATION": (24, 100),
    }

    def pick_window(fam: str) -> tuple[int, int]:
        lo, hi = lengths[fam]
        length = rng.randint(lo, hi)
        if scenario_type == "EVENT_FAULT" and events:
            start = events[0].onset + rng.randint(0, 30)
        else:
            start = rng.randint(20, steps - length - 2)
        start = min(start, steps - length - 1)
        return start, start + length - 1

    start, end = pick_window(family)
    if family == "STUCK_AT":
        needed = cfg.fault.stuck_min_variation_sigma * sensor.sigma
        for _ in range(30):
            seg = sensor.obs_clean[start : end + 1]
            if max(seg) - min(seg) >= needed:
                break
            start, end = pick_window(family)
        else:
            family = "SENSOR_SPIKE"  # a stuck sensor in a flat signal is undetectable
            start, end = pick_window(family)
    return FaultRecord(f"{sid}-F{fault_no}", family, sensor_idx, start, end)


def generate_scenario(index: int, seed: int, cfg: SimpleNamespace) -> Scenario:
    """Generate one deterministic scenario for scenario `index`."""
    scenario_type = SCENARIO_TYPES[index % len(SCENARIO_TYPES)]
    sid = f"SC{index:04d}"
    rng = random.Random(f"{seed}-scenario-{index}")
    steps = cfg.sim.steps_per_scenario
    dt_s = cfg.sim.sample_interval_s
    zone = ZONES[index % len(ZONES)]
    n_sensors = cfg.sim.n_neighbours + 1
    sigma = cfg.sim.noise_sigma_pct

    background, events, profiles = _plan_rain(scenario_type, rng, steps, sid)
    rain_true = background[:]
    for profile in profiles:
        rain_true = [a + b for a, b in zip(rain_true, profile, strict=True)]
    rain_true = [round(v, 4) for v in rain_true]

    sensors: list[SensorSeries] = []
    for j in range(n_sensors):
        params = _SoilParams(
            base=rng.uniform(38.0, 55.0),
            sat=rng.uniform(85.0, 95.0),
            gain=rng.uniform(0.6, 1.0),
            lag=rng.randint(1, 8),
            drain=rng.uniform(0.015, 0.03),
        )
        full = _simulate_soil(rain_true, params, steps)
        comps: dict[str, list[float]] = {}
        for event, profile in zip(events, profiles, strict=True):
            without = [a - b for a, b in zip(rain_true, profile, strict=True)]
            alt = _simulate_soil(without, params, steps)
            comps[event.event_id] = [round(a - b, 4) for a, b in zip(full, alt, strict=True)]
        obs_clean = [round(v + rng.gauss(0.0, sigma), 3) for v in full]
        sensors.append(
            SensorSeries(
                sensor_instance_id=f"{zone}-SM{j + 1}",
                device_id=f"{zone}-D{j + 1}",
                zone_id=zone,
                sigma=sigma,
                true=[round(v, 3) for v in full],
                obs_clean=obs_clean,
                obs=list(obs_clean),
                avail=[True] * steps,
                lag_steps=[0] * steps,
                voltage=[round(3.9 - 0.0002 * t + rng.gauss(0.0, 0.01), 3) for t in range(steps)],
                fault_id=[None] * steps,
                fault_type=[None] * steps,
                fault_effect=[None] * steps,
                event_comp=comps,
            )
        )

    faults: list[FaultRecord] = []
    if scenario_type in {"DRY_FAULT", "EVENT_FAULT"}:
        first_family = fault_family_for(index, seed)
        offset = FAULT_FAMILIES.index(first_family)
        chosen = rng.sample(range(n_sensors), 2)
        for k, sensor_idx in enumerate(chosen):
            family = FAULT_FAMILIES[(offset + 3 * k) % len(FAULT_FAMILIES)]
            fault = _plan_fault(
                scenario_type,
                family,
                sensors[sensor_idx],
                events,
                steps,
                cfg,
                rng,
                sid,
                sensor_idx,
                fault_no=k + 1,
            )
            _apply_fault(sensors[sensor_idx], fault, cfg, rng)
            faults.append(fault)

    rain_obs: list[float | None] = list(rain_true)
    if scenario_type == "OUTAGE":
        start = rng.randint(30, steps - 80)
        for t in range(start, start + rng.randint(30, 60)):
            rain_obs[t] = None
        out_idx, delay_idx = rng.sample(range(n_sensors), 2)
        o_start = rng.randint(30, steps - 70)
        for t in range(o_start, o_start + rng.randint(20, 50)):
            sensors[out_idx].avail[t] = False
        d_start = rng.randint(30, steps - 70)
        for t in range(d_start, d_start + rng.randint(20, 50)):
            sensors[delay_idx].lag_steps[t] = 5

    return Scenario(
        scenario_id=sid,
        scenario_type=scenario_type,
        index=index,
        zone_id=zone,
        start_time=BASE_TIME + timedelta(days=2 * index),
        dt_s=dt_s,
        steps=steps,
        rain_true=rain_true,
        rain_obs=rain_obs,
        events=events,
        faults=faults,
        sensors=sensors,
    )