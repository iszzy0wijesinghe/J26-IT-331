"""Training readiness endpoints for GeoNex C3."""

from fastapi import APIRouter, HTTPException

from apps.c3_workbench.training_approval import get_training_approval
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
        result = assess_training_readiness(dataset_id)
        approval = get_training_approval(dataset_id)
        authorized = (approval.get("approval_status") == "APPROVED" and approval.get("research_profile") == "SYNTHETIC_RESEARCH")
        # Retain distinction: experimental authorization is not field approval.
        result["training_approved"] = authorized
        result["training_approval_reason"] = ("Synthetic experiment authorized (self-declared; NOT field approved)." if authorized else "Temporal readiness does not establish sensor provenance or research approval.")
        result["research_profile"] = "SYNTHETIC_RESEARCH" if authorized else None
        result["field_approved"] = False
        return result

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error