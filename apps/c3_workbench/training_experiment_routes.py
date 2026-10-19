"""Explicit synthetic research admission; never grants field deployment approval."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.c3_workbench.golden_training_adapter import export_golden_training_dataset
from apps.c3_workbench.golden_training_readiness import assess_training_readiness
from apps.c3_workbench.training_approval import (
    approve_synthetic_dataset,
    get_training_approval,
    revoke_training_approval,
)

router = APIRouter(prefix='/training/experiments', tags=['C3 Experiment Admission'])

class Authorization(BaseModel):
    researcher: str
    reason: str
    confirm_synthetic: bool
    acknowledge_not_field_approved: bool

@router.get('/{dataset_id}/admission')
def admission(dataset_id: str):
    try:
        readiness = assess_training_readiness(dataset_id)
        approval = get_training_approval(dataset_id)
        authorized = approval.get('approval_status') == 'APPROVED' and approval.get('research_profile') == 'SYNTHETIC_RESEARCH'
        return {'dataset_id': dataset_id, 'temporal_ready': readiness['temporal_ready'], 'synthetic_experiment_authorized': authorized, 'field_approved': False, 'mode': 'SYNTHETIC_RESEARCH', 'approval': approval}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.post('/{dataset_id}/prepare')
def prepare(dataset_id: str):
    try:
        return export_golden_training_dataset(dataset_id)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.post('/{dataset_id}/authorize')
def authorize(dataset_id: str, payload: Authorization):
    if not payload.confirm_synthetic or not payload.acknowledge_not_field_approved:
        raise HTTPException(status_code=422, detail='Explicit synthetic-only declaration and field-use disclaimer are required.')
    try:
        return approve_synthetic_dataset(dataset_id, approved_by=payload.researcher, reason=payload.reason)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.post('/{dataset_id}/revoke')
def revoke(dataset_id: str):
    try:
        return revoke_training_approval(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
