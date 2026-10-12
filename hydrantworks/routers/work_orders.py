from __future__ import annotations

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status

from .. import repository as repo
from ..auth import Caller, reader, writer
from ..deps import Paging, get_conn, trace_id
from ..models import Page, WorkOrder, WorkOrderCreate, WorkOrderUpdate

router = APIRouter(tags=["work orders"])


@router.get("/work-orders", response_model=Page[WorkOrder])
def list_work_orders(
    status: Literal["open", "assigned", "closed"] | None = None,
    hydrant_id: str | None = None,
    paging: Paging = Depends(),
    conn: sqlite3.Connection = Depends(get_conn),
    _: Caller = Depends(reader),
):
    """Newest first."""
    items, total = repo.list_work_orders(conn, status, hydrant_id, paging.page, paging.size)
    return Page(items=items, page=paging.page, size=paging.size, total=total)


@router.get("/work-orders/{wo_id}", response_model=WorkOrder)
def get_work_order(wo_id: int, conn: sqlite3.Connection = Depends(get_conn), _: Caller = Depends(reader)):
    wo = repo.get_work_order(conn, wo_id)
    if wo is None:
        raise HTTPException(404, f"No work order {wo_id}.")
    return wo


@router.post("/work-orders", response_model=WorkOrder, status_code=status.HTTP_201_CREATED)
def create_work_order(
    body: WorkOrderCreate,
    conn: sqlite3.Connection = Depends(get_conn),
    who: Caller = Depends(writer),
    tid: str = Depends(trace_id),
):
    """Open a work order against a hydrant. Audited."""
    if repo.get_hydrant(conn, body.hydrant_id) is None:
        raise HTTPException(404, f"No hydrant with id {body.hydrant_id!r}.")
    return repo.create_work_order(conn, body, who.actor, tid)


@router.patch("/work-orders/{wo_id}", response_model=WorkOrder)
def update_work_order(
    wo_id: int,
    body: WorkOrderUpdate,
    conn: sqlite3.Connection = Depends(get_conn),
    who: Caller = Depends(writer),
    tid: str = Depends(trace_id),
):
    """Assign, re-prioritize, or close a work order. Audited."""
    wo = repo.update_work_order(conn, wo_id, body, who.actor, tid)
    if wo is None:
        raise HTTPException(404, f"No work order {wo_id}.")
    return wo
