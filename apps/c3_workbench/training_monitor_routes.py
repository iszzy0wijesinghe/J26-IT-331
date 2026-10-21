"""
GeoNex C3 Training Monitoring API.

Phase 1.4.8 — Dedicated Training Database Integration.

Provides read-only training telemetry derived from
persisted training events.

Responsibilities:
    - Retrieve training job status.
    - Read persisted training events.
    - Calculate completed training commands.
    - Extract real epoch information.
    - Extract recorded training metrics.
    - Preserve frontend API response structure.

No synthetic progress values are generated.

Database:
    Dedicated C3 Training Database, accessed through
    the migrated training_queue service.
"""

from __future__ import annotations

import re

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from apps.c3_workbench.training_queue import (
    get_training_job,
)


router = APIRouter(
    prefix="/training",
    tags=["C3 Training Telemetry"],
)


HORIZONS = (15, 30, 60)

STAGES = (
    ["TRAINING_M1", "TRAINING_M2"]
    + [
        f"TRAINING_M3_{horizon}MIN"
        for horizon in HORIZONS
    ]
    + [
        f"TRAINING_M4_{variant}_{horizon}MIN"
        for variant in "ABC"
        for horizon in HORIZONS
    ]
)


EPOCH_RE = re.compile(
    r"(?i)\bepoch\s*[:=]?\s*(\d+)"
    r"(?:\s*(?:/|of)\s*(\d+))?"
)


METRIC_RE = re.compile(
    r"(?i)\b("
    r"train(?:ing)?[_ -]?(?:loss|mae|rmse)"
    r"|"
    r"val(?:idation)?[_ -]?(?:loss|mae|rmse)"
    r")\s*[:=]\s*"
    r"(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)"
)


def extract_metrics(
    message: str,
) -> dict[str, float]:
    """
    Extract actual metric values from recorded
    training output.
    """

    return {
        name.lower()
        .replace(" ", "_")
        .replace("-", "_"): float(value)
        for name, value in METRIC_RE.findall(message)
    }


def extract_epoch(
    message: str,
) -> tuple[int | None, int | None]:
    """
    Extract the current and total epoch counts
    from a recorded training message.
    """

    match = EPOCH_RE.search(message)

    if match is None:
        return None, None

    current = int(
        match.group(1)
    )

    maximum = (
        int(match.group(2))
        if match.group(2)
        else None
    )

    return current, maximum


def derive_training_telemetry(
    job: dict,
    *,
    limit: int = 250,
) -> dict:
    """
    Derive monitoring information from persisted
    training events.

    Does not generate estimated progress.
    """

    events = job.get("events") or []

    completed = set()
    started = set()

    metric_points = []

    current_epoch = None
    max_epochs = None

    active_stage = str(
        job.get("current_stage") or ""
    )

    status = str(
        job.get("status") or ""
    )

    # -------------------------------------------------
    # Step 1 — Process recorded training events.
    # -------------------------------------------------

    for event in events:

        stage = str(
            event.get("stage") or ""
        )

        message = str(
            event.get("message") or ""
        )

        if stage not in STAGES:
            continue

        message_lower = message.lower()

        if "starting task" in message_lower:
            started.add(stage)

        if (
            "completed" in message_lower
            or "finished" in message_lower
        ):
            completed.add(stage)

        epoch, maximum = extract_epoch(
            message
        )

        metrics = extract_metrics(
            message
        )

        if epoch is not None or metrics:

            metric_points.append(
                {
                    "stage": stage,
                    "timestamp": event.get(
                        "timestamp"
                    ),
                    "epoch": epoch,
                    "metrics": metrics,
                }
            )

        # Only the currently active training stage
        # contributes to the displayed epoch counter.
        if stage == active_stage:

            if epoch is not None:
                current_epoch = epoch

            if maximum is not None:
                max_epochs = maximum

    # -------------------------------------------------
    # Step 2 — Handle terminal training stages.
    # -------------------------------------------------

    # EVALUATING means the training worker has moved
    # past the training-command execution phase.
    #
    # COMPLETED means model candidates have also been
    # registered and the job finalized.
    #
    # These states are meaningful lifecycle evidence,
    # but they do not replace individual event records.

    if status in (
        "EVALUATING",
        "COMPLETED",
    ):
        completed.update(STAGES)

    # -------------------------------------------------
    # Step 3 — Calculate command completion.
    # -------------------------------------------------

    completed_tasks = len(
        completed
    )

    total_tasks = len(
        STAGES
    )

    progress_percent = round(
        completed_tasks / total_tasks * 100,
        1,
    )

    # -------------------------------------------------
    # Step 4 — Prevent stale epoch display.
    # -------------------------------------------------

    if active_stage not in STAGES:
        current_epoch = None
        max_epochs = None

    # -------------------------------------------------
    # Step 5 — Preserve existing frontend response.
    # -------------------------------------------------

    return {
        "job_id": job.get("job_id"),
        "status": status,
        "current_stage": active_stage,
        "completed_tasks": completed_tasks,
        "total_tasks": total_tasks,
        "progress_percent": progress_percent,
        "progress_basis": (
            "completed training commands; "
            "epoch work is excluded"
        ),
        "current_epoch": current_epoch,
        "max_epochs": max_epochs,
        "events": events[-limit:],
        "metric_points": metric_points[-limit:],
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "error_message": job.get("error_message"),
    }


@router.get(
    "/jobs/{job_id}/telemetry"
)
def training_telemetry(
    job_id: str,
    limit: int = Query(
        default=250,
        ge=10,
        le=2000,
    ),
):
    """
    Retrieve persisted training telemetry.

    No database writes.
    No training execution.
    """

    job = get_training_job(
        job_id
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Training job not found.",
        )

    return derive_training_telemetry(
        job,
        limit=limit,
    )