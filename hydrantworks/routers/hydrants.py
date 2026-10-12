from __future__ import annotations

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import repository as repo
from ..auth import Caller, reader, writer
from ..deps import Paging, get_conn, trace_id
from ..models import Hydrant, HydrantSummary, Inspection, Jurisdiction, Page, StatusChange

router = APIRouter(tags=["hydrants"])


@router.get("/jurisdictions", response_model=list[Jurisdiction])
def jurisdictions(conn: sqlite3.Connection = Depends(get_conn), _: Caller = Depends(reader)):
    """Every jurisdiction with its hydrant count and how many are out of service."""
    return repo.list_jurisdictions(conn)


@router.get("/hydrants", response_model=Page[HydrantSummary])
def list_hydrants(
    jurisdiction: str | None = Query(None, description="e.g. 'Howland Township' or 'Warren'."),
    street: str | None = Query(None, description="Substring of the street or alternate street."),
    status: Literal["in_service", "out_of_service"] | None = None,
    paging: Paging = Depends(),
    conn: sqlite3.Connection = Depends(get_conn),
    _: Caller = Depends(reader),
):
    items, total = repo.list_hydrants(conn, jurisdiction, street, status, paging.page, paging.size)
    return Page(items=items, page=paging.page, size=paging.size, total=total)


@router.get("/hydrants/overdue", response_model=Page[HydrantSummary])
def overdue(
    jurisdiction: str | None = None,
    paging: Paging = Depends(),
    conn: sqlite3.Connection = Depends(get_conn),
    _: Caller = Depends(reader),
):
    """Hydrants with no inspection in the last 365 days, including never-inspected ones."""
    items, total = repo.list_overdue(conn, jurisdiction, paging.page, paging.size)
    return Page(items=items, page=paging.page, size=paging.size, total=total)


@router.get("/hydrants/{hydrant_id}", response_model=Hydrant)
def get_hydrant(hydrant_id: str, conn: sqlite3.Connection = Depends(get_conn), _: Caller = Depends(reader)):
    h = repo.get_hydrant(conn, hydrant_id)
    if h is None:
        raise HTTPException(404, f"No hydrant with id {hydrant_id!r}.")
    return h


@router.get("/hydrants/{hydrant_id}/inspections", response_model=list[Inspection])
def hydrant_inspections(
    hydrant_id: str,
    limit: int = Query(20, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_conn),
    _: Caller = Depends(reader),
):
    """Most recent inspections first."""
    if repo.get_hydrant(conn, hydrant_id) is None:
        raise HTTPException(404, f"No hydrant with id {hydrant_id!r}.")
    return repo.list_inspections(conn, hydrant_id, limit)


@router.post("/hydrants/{hydrant_id}/out-of-service", response_model=Hydrant)
def take_out_of_service(
    hydrant_id: str,
    body: StatusChange,
    conn: sqlite3.Connection = Depends(get_conn),
    who: Caller = Depends(writer),
    tid: str = Depends(trace_id),
):
    """Mark a hydrant out of service. Fire departments rely on this flag — audited."""
    h = repo.set_status(conn, hydrant_id, "out_of_service", body, who.actor, tid)
    if h is None:
        raise HTTPException(404, f"No hydrant with id {hydrant_id!r}.")
    return h


@router.post("/hydrants/{hydrant_id}/in-service", response_model=Hydrant)
def return_to_service(
    hydrant_id: str,
    body: StatusChange,
    conn: sqlite3.Connection = Depends(get_conn),
    who: Caller = Depends(writer),
    tid: str = Depends(trace_id),
):
    h = repo.set_status(conn, hydrant_id, "in_service", body, who.actor, tid)
    if h is None:
        raise HTTPException(404, f"No hydrant with id {hydrant_id!r}.")
    return h
