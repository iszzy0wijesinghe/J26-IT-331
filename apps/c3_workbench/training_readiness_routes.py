"""
GeoNex C3 Training Readiness API.

Phase 1.4.10 — Training Database Isolation.

This endpoint combines:

1. Temporal readiness assessment.
2. Synthetic research training authorization.

It does NOT:
- Execute training.
- Export datasets.
- Activate models.
- Authorize field deployment.
- Guarantee training artifact integrity.

Database responsibilities:
- Temporal observations: Golden Database.
- Training approval metadata: Training Database.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.c3_workbench.golden_training_readiness import (
    assess_training_readiness,
)

from apps.c3_workbench.training_approval import (
    get_training_approval,
)


router = APIRouter(
    prefix="/training/readiness",
    tags=["C3 Training Readiness"],
)


@router.get("/{dataset_id}")
def get_training_readiness(dataset_id: str):
    """
    Return temporal readiness and research authorization.

    Research authorization is not equivalent to
    operational field approval.
    """

    try:
        result = assess_training_readiness(
            dataset_id
        )

        approval = get_training_approval(
            dataset_id
        )

        authorized = (
            approval.get("approval_status") == "APPROVED"
            and approval.get("research_profile") == "SYNTHETIC_RESEARCH"
        )

        result["training_approved"] = authorized

        result["training_approval_reason"] = (
            "Synthetic experiment authorized "
            "(self-declared; NOT field approved)."
            if authorized
            else (
                "Temporal readiness does not establish "
                "sensor provenance or research approval."
            )
        )

        result["research_profile"] = (
            "SYNTHETIC_RESEARCH"
            if authorized
            else None
        )

        # Research approval never grants field deployment
        # authorization.
        result["field_approved"] = False

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error