"""GeoNex C3 historical adaptive-monitoring research API.

Research-only historical replay:
- Uses existing Golden Database observations.
- Executes active ML forecasting models.
- Preserves adaptive-controller state within each replay.
- Estimates hypothetical monitoring energy.
- Does not control physical sensors or issue real-world warnings.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.c3_workbench.forecasting_reader import parse_timestamp
from components.c3_adaptive.mode_controller import (
    C3AdaptiveModeController,
)
from components.c3_simulation.adaptive_energy_replay import (
    estimate_adaptive_energy,
)
from components.c3_simulation.energy_model import (
    EnergyModelConfig,
    estimate_fixed_interval_energy,
)

router = APIRouter(
    prefix="/research/adaptive",
    tags=["C3 Adaptive Research"],
)

ROOT = Path(__file__).resolve().parents[2]

GOLDEN_DATABASE = (
    ROOT
    / "data"
    / "workbench"
    / "c3"
    / "golden"
    / "c3_golden.sqlite3"
)

MAX_REPLAY_OBSERVATIONS = 120


class AdaptiveReplayRequest(BaseModel):
    dataset_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    episode_id: str = Field(min_length=1)

    start_index: int = Field(default=32, ge=0)
    observation_count: int = Field(default=12, ge=1, le=120)


def load_replay_timestamps(
    request: AdaptiveReplayRequest,
) -> list[str]:
    """Load one device/episode's ordered observation timestamps."""

    if not GOLDEN_DATABASE.is_file():
        raise HTTPException(
            status_code=404,
            detail="Golden Database not found.",
        )

    try:
        connection = sqlite3.connect(
            f"{GOLDEN_DATABASE.as_uri()}?mode=ro",
            uri=True,
        )

        try:
            rows = connection.execute(
                """
                SELECT timestamp
                FROM c3_golden_observations
                WHERE dataset_id = ?
                  AND device_id = ?
                  AND episode_id = ?
                ORDER BY timestamp, observation_id
                LIMIT ? OFFSET ?
                """,
                (
                    request.dataset_id,
                    request.device_id,
                    request.episode_id,
                    request.observation_count,
                    request.start_index,
                ),
            ).fetchall()
        finally:
            connection.close()

    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to read Golden Database observations.",
        ) from exc

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No observations found for the requested replay.",
        )

    return [row[0] for row in rows]


@router.post("/replay")
def run_adaptive_replay(
    request: AdaptiveReplayRequest,
) -> dict[str, Any]:
    """Run an isolated historical adaptive-monitoring replay."""

    timestamps = load_replay_timestamps(request)

    controller = C3AdaptiveModeController()

    decisions: list[dict[str, Any]] = []

    try:
        for timestamp in timestamps:
            result = controller.evaluate(
                dataset_id=request.dataset_id,
                device_id=request.device_id,
                episode_id=request.episode_id,
                forecast_origin=timestamp,
            )

            decisions.append(result)

        # Historical Golden observations are recorded at
        # five-minute intervals. The final decision is
        # evaluated over one additional five-minute segment.
        #
        # This is an explicit research assumption.
        end_timestamp = (
            parse_timestamp(timestamps[-1])
            + timedelta(minutes=5)
        ).isoformat()

        energy_config = EnergyModelConfig(
            baseline_power_mw=5.0,
            monitoring_cycle_energy_mj=20.0,
        )

        adaptive_energy = estimate_adaptive_energy(
            decisions=decisions,
            end_timestamp=end_timestamp,
            config=energy_config,
        )

        fixed_baselines = []

        for interval_s in (5.0, 10.0, 30.0, 300.0):
            estimate = estimate_fixed_interval_energy(
                duration_s=adaptive_energy.total_duration_s,
                monitoring_interval_s=interval_s,
                config=energy_config,
            )

            fixed_baselines.append({
                "monitoring_interval_s": interval_s,
                "energy": asdict(estimate),
            })

        fixed_5_energy = fixed_baselines[0][
            "energy"
        ]["total_energy_mj"]

        energy_saving_pct = (
            (
                fixed_5_energy
                - adaptive_energy.total_energy_mj
            )
            / fixed_5_energy
            * 100.0
        )

    except (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        RuntimeError,
        FileNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Unable to complete adaptive replay: {exc}",
        ) from exc

    return {
        "dataset_id": request.dataset_id,
        "device_id": request.device_id,
        "episode_id": request.episode_id,
        "replay_type": "HISTORICAL_OPEN_LOOP_REPLAY",
        "research_status": "SYNTHETIC_RESEARCH_NOT_FIELD_VALIDATED",
        "start_timestamp": timestamps[0],
        "end_timestamp": end_timestamp,
        "observation_count": len(decisions),
        "decisions": decisions,
        "energy_evaluation": {
            "adaptive": asdict(adaptive_energy),
            "fixed_baselines": fixed_baselines,
            "saving_vs_fixed_5s_pct": energy_saving_pct,
            "assumptions": {
                "baseline_power_mw": energy_config.baseline_power_mw,
                "monitoring_cycle_energy_mj": (
                    energy_config.monitoring_cycle_energy_mj
                ),
                "monitoring_schedule": (
                    "RESTARTS_AT_EACH_DECISION_BOUNDARY"
                ),
                "hardware_energy_measured": False,
            },
        },
        "limitations": [
            "Synthetic historical replay only.",
            "Monitoring cycles are simulated, not observed.",
            "Energy parameters are hypothetical.",
            "Historical observation times are not independently verified receipt times.",
            "Individual sensor ages are not independently verified.",
            "Forecasted soil moisture is not a landslide probability.",
            "No field-validated landslide detection is performed.",
        ],
    }
