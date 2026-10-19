"""Training readiness endpoints for GeoNex C3."""

from fastapi import APIRouter, HTTPException

from apps.c3_workbench.golden_training_readiness import (
    assess_training_readiness,
)


router = APIRouter(
    prefix="/training/readiness",
    tags=["C3 Training Readiness"],
)


@router.get("/{dataset_id}")
def get_training_readiness(dataset_id: str):
    try:
        return assess_training_readiness(dataset_id)

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error