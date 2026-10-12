from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from .. import repository as repo
from ..auth import Caller, writer
from ..deps import Paging, get_conn
from ..models import AuditEntry, Page

router = APIRouter(tags=["audit"])


@router.get("/audit", response_model=Page[AuditEntry])
def audit_log(
    entity: str | None = None,
    entity_id: str | None = None,
    paging: Paging = Depends(),
    conn: sqlite3.Connection = Depends(get_conn),
    _: Caller = Depends(writer),
):
    """Every write, newest first: who, what, before and after, and the trace id. Needs the write key."""
    items, total = repo.list_audit(conn, entity, entity_id, paging.page, paging.size)
    return Page(items=items, page=paging.page, size=paging.size, total=total)
