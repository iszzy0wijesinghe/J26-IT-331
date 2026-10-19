"""Read-only model registry API. No model activation or rollback side effects."""
from fastapi import APIRouter, HTTPException, Query

from apps.c3_workbench.golden_db import get_connection, initialize_golden_database
from apps.c3_workbench.model_activation import (
    ModelActivationError,
    list_active_model_assignments,
    list_model_activation_history,
)

router = APIRouter(prefix="/research/models", tags=["C3 Model Review"])

@router.get("/candidates")
def candidates(dataset_id: str | None = None, job_id: str | None = None):
    initialize_golden_database()
    sql = """SELECT model_version_id,job_id,dataset_id,model_name,
             horizon_minutes,validation_mae,validation_rmse,status,created_at
             FROM c3_model_versions WHERE 1=1"""
    params = []
    if dataset_id:
        sql += " AND dataset_id=?"
        params.append(dataset_id)
    if job_id:
        sql += " AND job_id=?"
        params.append(job_id)
    sql += " ORDER BY horizon_minutes, validation_mae, validation_rmse, model_name"
    with get_connection() as conn:
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    return {"candidates": rows, "total": len(rows), "selection_basis": "validation metrics only"}

@router.get("/active")
def active():
    return {"assignments": list_active_model_assignments()}

@router.get("/history")
def history(horizon_minutes: int | None = Query(default=None)):
    try:
        return {"events": list_model_activation_history(horizon_minutes)}
    except ModelActivationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
