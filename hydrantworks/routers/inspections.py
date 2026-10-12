from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from .. import repository as repo
from ..auth import Caller, writer
from ..deps import get_conn, trace_id
from ..models import Inspection, InspectionCreate

router = APIRouter(tags=["inspections"])


@router.post("/inspections", response_model=Inspection, status_code=status.HTTP_201_CREATED)
def create_inspection(
    body: InspectionCreate,
    conn: sqlite3.Connection = Depends(get_conn),
    who: Caller = Depends(writer),
    tid: str = Depends(trace_id),
):
    """Record one field inspection. Audited."""
    if repo.get_hydrant(conn, body.hydrant_id) is None:
        raise HTTPException(404, f"No hydrant with id {body.hydrant_id!r}.")
    return repo.create_inspection(conn, body, who.actor, tid)
