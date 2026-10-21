"""
GeoNex C3 Training Experiment Admission API.

Phase 1.4.6 — Training Database Integration.

Responsibilities:
    - Assess Golden temporal training readiness.
    - Prepare training dataset exports.
    - Authorize synthetic research experiments.
    - Retrieve training authorization status.
    - Revoke training authorization.

Database ownership:
    Golden temporal readiness -> Golden Database
    Training approval         -> Training Database

IMPORTANT:
    Synthetic research authorization does not
    authorize operational or field deployment.
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
)

from pydantic import (
    BaseModel,
    Field,
)

from apps.c3_workbench.golden_training_adapter import (
    export_golden_training_dataset,
)

from apps.c3_workbench.golden_training_readiness import (
    assess_training_readiness,
)

from apps.c3_workbench.training_approval import (
    approve_synthetic_dataset,
    get_training_approval,
    revoke_training_approval,
)


router = APIRouter(
    prefix="/training/experiments",
    tags=["C3 Experiment Admission"],
)


RESEARCH_PROFILE = "SYNTHETIC_RESEARCH"


class Authorization(BaseModel):
    """
    Explicit researcher authorization for synthetic
    research experiments.

    These fields preserve the existing API contract.
    """

    researcher: str = Field(
        min_length=1,
    )

    reason: str = Field(
        min_length=1,
    )

    confirm_synthetic: bool

    acknowledge_not_field_approved: bool


@router.get("/{dataset_id}/admission")
def admission(
    dataset_id: str,
):
    """
    Return temporal readiness and synthetic
    research authorization status.

    This endpoint does not modify database records.
    """

    try:
        readiness = assess_training_readiness(
            dataset_id
        )

        approval = get_training_approval(
            dataset_id
        )

        authorized = (
            approval is not None
            and approval.get("approval_status") == "APPROVED"
            and approval.get("research_profile") == RESEARCH_PROFILE
        )

        return {
            "dataset_id": dataset_id,
            "temporal_ready": readiness["temporal_ready"],
            "synthetic_experiment_authorized": authorized,
            "field_approved": False,
            "mode": RESEARCH_PROFILE,
            "approval": approval,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


@router.post("/{dataset_id}/prepare")
def prepare(
    dataset_id: str,
):
    """
    Export an eligible Golden dataset for
    synthetic research training.

    Dataset export does not authorize training.
    """

    try:
        return export_golden_training_dataset(
            dataset_id
        )

    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


@router.post("/{dataset_id}/authorize")
def authorize(
    dataset_id: str,
    payload: Authorization,
):
    """
    Explicitly authorize synthetic research training.

    Both declarations are mandatory.
    """

    if not payload.confirm_synthetic:
        raise HTTPException(
            status_code=422,
            detail=(
                "Explicit synthetic-only "
                "declaration is required."
            ),
        )

    if not payload.acknowledge_not_field_approved:
        raise HTTPException(
            status_code=422,
            detail=(
                "Field-use disclaimer "
                "acknowledgement is required."
            ),
        )

    researcher = payload.researcher.strip()
    reason = payload.reason.strip()

    if not researcher:
        raise HTTPException(
            status_code=422,
            detail="Researcher must not be empty.",
        )

    if not reason:
        raise HTTPException(
            status_code=422,
            detail="Authorization reason must not be empty.",
        )

    try:
        return approve_synthetic_dataset(
            dataset_id,
            approved_by=researcher,
            reason=reason,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


@router.post("/{dataset_id}/revoke")
def revoke(
    dataset_id: str,
):
    """
    Revoke synthetic research training authorization.

    Does not delete datasets, jobs, or model records.
    """

    try:
        return revoke_training_approval(
            dataset_id
        )

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error