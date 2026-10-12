"""All SQL lives here. Routers call these functions; nothing else touches the database."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from .db import transaction
from .models import InspectionCreate, StatusChange, WorkOrderCreate, WorkOrderUpdate

OVERDUE_DAYS = 365


def utcnow() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


# ---------------------------------------------------------------- audit


def audit(
    conn: sqlite3.Connection,
    actor: str,
    action: str,
    entity: str,
    entity_id: str,
    before: dict | None,
    after: dict | None,
    trace_id: str,
) -> None:
    conn.execute(
        "INSERT INTO audit_log (at, actor, action, entity, entity_id, before, after, trace_id)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (
            _iso(utcnow()),
            actor,
            action,
            entity,
            entity_id,
            json.dumps(before) if before is not None else None,
            json.dumps(after) if after is not None else None,
            trace_id,
        ),
    )


def list_audit(conn: sqlite3.Connection, entity: str | None, entity_id: str | None, page: int, size: int):
    where, args = [], []
    if entity:
        where.append("entity = ?")
        args.append(entity)
    if entity_id:
        where.append("entity_id = ?")
        args.append(entity_id)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM audit_log {clause}", args).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM audit_log {clause} ORDER BY id DESC LIMIT ? OFFSET ?",
        [*args, size, (page - 1) * size],
    ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["before"] = json.loads(d["before"]) if d["before"] else None
        d["after"] = json.loads(d["after"]) if d["after"] else None
        items.append(d)
    return items, total


# ---------------------------------------------------------------- hydrants


def last_inspected_at(conn: sqlite3.Connection, hydrant_id: str) -> str | None:
    row = conn.execute("SELECT MAX(inspected_at) FROM inspections WHERE hydrant_id = ?", (hydrant_id,)).fetchone()
    return row[0]


def list_hydrants(
    conn: sqlite3.Connection,
    jurisdiction: str | None,
    street: str | None,
    status: str | None,
    page: int,
    size: int,
):
    where, args = [], []
    if jurisdiction:
        where.append("jurisdiction = ?")
        args.append(jurisdiction)
    if street:
        where.append("(street LIKE ? OR alt_street LIKE ?)")
        args += [f"%{street}%", f"%{street}%"]
    if status:
        where.append("status = ?")
        args.append(status)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM hydrants {clause}", args).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM hydrants {clause} ORDER BY hydrant_id LIMIT ? OFFSET ?",
        [*args, size, page * size],
    ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["last_inspected_at"] = last_inspected_at(conn, d["hydrant_id"])
        items.append(d)
    return items, total


def get_hydrant(conn: sqlite3.Connection, hydrant_id: str) -> dict | None:
    d = _row(conn.execute("SELECT * FROM hydrants WHERE hydrant_id = ?", (hydrant_id,)).fetchone())
    if d is not None:
        d["last_inspected_at"] = last_inspected_at(conn, hydrant_id)
    return d


def days_since(iso: str, now: datetime) -> int:
    return (now.date() - datetime.fromisoformat(iso).astimezone(UTC).date()).days


def is_overdue(last_iso: str | None, now: datetime) -> bool:
    """Overdue: no inspection within the last OVERDUE_DAYS days (never inspected counts)."""
    return last_iso is None or days_since(last_iso, now) >= OVERDUE_DAYS


def list_overdue(conn: sqlite3.Connection, jurisdiction: str | None, page: int, size: int, now: datetime | None = None):
    now = now or utcnow()
    args: list[Any] = []
    clause = ""
    if jurisdiction:
        clause = "WHERE jurisdiction = ?"
        args.append(jurisdiction)
    overdue = []
    for r in conn.execute(f"SELECT * FROM hydrants {clause} ORDER BY hydrant_id", args).fetchall():
        d = dict(r)
        d["last_inspected_at"] = last_inspected_at(conn, d["hydrant_id"])
        if is_overdue(d["last_inspected_at"], now):
            overdue.append(d)
    start = (page - 1) * size
    return overdue[start : start + size], len(overdue)


def list_jurisdictions(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT jurisdiction, COUNT(*) AS hydrants,"
        " SUM(CASE WHEN status = 'out_of_service' THEN 1 ELSE 0 END) AS out_of_service"
        " FROM hydrants GROUP BY jurisdiction ORDER BY jurisdiction"
    ).fetchall()
    return [dict(r) for r in rows]


def set_status(
    conn: sqlite3.Connection, hydrant_id: str, status: str, change: StatusChange, actor: str, trace_id: str
) -> dict | None:
    before = get_hydrant(conn, hydrant_id)
    if before is None:
        return None
    with transaction(conn):
        conn.execute(
            "UPDATE hydrants SET status = ?, status_reason = ? WHERE hydrant_id = ?",
            (status, change.reason, hydrant_id),
        )
        after = get_hydrant(conn, hydrant_id)
        audit(
            conn,
            actor,
            f"hydrant.{status}",
            "hydrant",
            hydrant_id,
            {"status": before["status"], "status_reason": before["status_reason"]},
            {"status": after["status"], "status_reason": after["status_reason"]},
            trace_id,
        )
    return after


# ---------------------------------------------------------------- inspections


def list_inspections(conn: sqlite3.Connection, hydrant_id: str, limit: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM inspections WHERE hydrant_id = ? ORDER BY inspected_at DESC LIMIT ?",
        (hydrant_id, limit),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["operable"] = bool(d["operable"])
        d["leaking"] = bool(d["leaking"])
        out.append(d)
    return out


def create_inspection(conn: sqlite3.Connection, body: InspectionCreate, actor: str, trace_id: str) -> dict:
    # Store every timestamp in UTC.
    when = body.inspected_at.replace(tzinfo=UTC)
    with transaction(conn):
        cur = conn.execute(
            "INSERT INTO inspections (hydrant_id, inspected_at, inspector, static_psi, residual_psi, flow_gpm,"
            " cap_condition, operable, leaking, notes, source) VALUES (?,?,?,?,?,?,?,?,?,?, 'api')",
            (
                body.hydrant_id,
                _iso(when),
                body.inspector,
                body.static_psi,
                body.residual_psi,
                body.flow_gpm,
                body.cap_condition,
                int(body.operable),
                int(body.leaking),
                body.notes,
            ),
        )
        created = dict(conn.execute("SELECT * FROM inspections WHERE id = ?", (cur.lastrowid,)).fetchone())
        created["operable"] = bool(created["operable"])
        created["leaking"] = bool(created["leaking"])
        audit(conn, actor, "inspection.create", "inspection", str(cur.lastrowid), None, created, trace_id)
    return created


# ---------------------------------------------------------------- work orders


def list_work_orders(conn: sqlite3.Connection, status: str | None, hydrant_id: str | None, page: int, size: int):
    where, args = [], []
    if status:
        where.append("status = ?")
        args.append(status)
    if hydrant_id:
        where.append("hydrant_id = ?")
        args.append(hydrant_id)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM work_orders {clause}", args).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM work_orders {clause} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        [*args, size, (page - 1) * size],
    ).fetchall()
    return [dict(r) for r in rows], total


def get_work_order(conn: sqlite3.Connection, wo_id: int) -> dict | None:
    return _row(conn.execute("SELECT * FROM work_orders WHERE id = ?", (wo_id,)).fetchone())


def create_work_order(conn: sqlite3.Connection, body: WorkOrderCreate, actor: str, trace_id: str) -> dict:
    with transaction(conn):
        cur = conn.execute(
            "INSERT INTO work_orders (hydrant_id, kind, priority, status, description, created_at, created_by)"
            " VALUES (?,?,?, 'open', ?,?,?)",
            (body.hydrant_id, body.kind, body.priority, body.description, _iso(utcnow()), actor),
        )
        created = get_work_order(conn, cur.lastrowid)
        audit(conn, actor, "work_order.create", "work_order", str(cur.lastrowid), None, created, trace_id)
    return created  # type: ignore[return-value]


def update_work_order(
    conn: sqlite3.Connection, wo_id: int, body: WorkOrderUpdate, actor: str, trace_id: str
) -> dict | None:
    before = get_work_order(conn, wo_id)
    if before is None:
        return None
    changes = body.model_dump(exclude_none=True)
    if not changes:
        return before
    sets = ", ".join(f"{k} = ?" for k in changes)
    with transaction(conn):
        conn.execute(f"UPDATE work_orders SET {sets} WHERE id = ?", [*changes.values(), wo_id])
        after = get_work_order(conn, wo_id)
        audit(conn, actor, "work_order.update", "work_order", str(wo_id), before, after, trace_id)
    return after
