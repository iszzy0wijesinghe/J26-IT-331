"""FastAPI routes for read-only Golden Database exploration."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from apps.c3_workbench.golden_explorer import (
    export_observations_csv,
    get_observation_filters,
    list_observations,
)

router = APIRouter(
    prefix="/database/observations",
    tags=["C3 Golden Database Explorer"],
)


@router.get("")
def observations(
    dataset_id: str | None = None,
    device_id: str | None = None,
    episode_id: str | None = None,
    operating_mode: str | None = None,
    timestamp_from: str | None = None,
    timestamp_to: str | None = None,
    search: str | None = Query(default=None, max_length=200),
    sort_by: str = "timestamp",
    sort_order: str = "desc",
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    try:
        return list_observations(
            dataset_id=dataset_id,
            device_id=device_id,
            episode_id=episode_id,
            operating_mode=operating_mode,
            timestamp_from=timestamp_from,
            timestamp_to=timestamp_to,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


@router.get("/filters")
def observation_filters(
    dataset_id: str | None = None,
):
    return get_observation_filters(dataset_id)


@router.get("/export")
def export_observations(
    dataset_id: str | None = None,
    device_id: str | None = None,
    episode_id: str | None = None,
    operating_mode: str | None = None,
    timestamp_from: str | None = None,
    timestamp_to: str | None = None,
    search: str | None = Query(default=None, max_length=200),
):
    try:
        content = export_observations_csv(
            dataset_id=dataset_id,
            device_id=device_id,
            episode_id=episode_id,
            operating_mode=operating_mode,
            timestamp_from=timestamp_from,
            timestamp_to=timestamp_to,
            search=search,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition":
                'attachment; filename="geonex_c3_golden_observations.csv"'
        },
    )