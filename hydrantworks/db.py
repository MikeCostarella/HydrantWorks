"""SQLite storage: one file, created and seeded on first start."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS hydrants (
    hydrant_id    TEXT PRIMARY KEY,
    lat           REAL NOT NULL,
    lng           REAL NOT NULL,
    elevation_ft  REAL,
    street        TEXT NOT NULL,
    alt_street    TEXT NOT NULL DEFAULT '',
    municipality  TEXT NOT NULL DEFAULT '',
    subdivision   TEXT NOT NULL DEFAULT '',
    county        TEXT NOT NULL,
    state         TEXT NOT NULL,
    hydrant_type  TEXT NOT NULL,
    gps_quality   INTEGER,
    survey_date   TEXT,
    jurisdiction  TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'in_service',   -- in_service | out_of_service
    status_reason TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS inspections (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    hydrant_id    TEXT NOT NULL REFERENCES hydrants(hydrant_id),
    inspected_at  TEXT NOT NULL,              -- ISO 8601, UTC
    inspector     TEXT NOT NULL,
    static_psi    REAL,
    residual_psi  REAL,
    flow_gpm      REAL,
    cap_condition TEXT NOT NULL,              -- good | worn | missing
    operable      INTEGER NOT NULL,           -- 0/1
    leaking       INTEGER NOT NULL,           -- 0/1
    notes         TEXT NOT NULL DEFAULT '',
    source        TEXT NOT NULL DEFAULT 'api' -- api | seed
);

CREATE TABLE IF NOT EXISTS work_orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    hydrant_id    TEXT NOT NULL REFERENCES hydrants(hydrant_id),
    kind          TEXT NOT NULL,              -- repair | flush | paint | replace_cap | flow_test | other
    priority      TEXT NOT NULL,              -- low | normal | high | urgent
    status        TEXT NOT NULL DEFAULT 'open', -- open | assigned | closed
    assigned_to   TEXT NOT NULL DEFAULT '',
    description   TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    created_by    TEXT NOT NULL,
    closed_at     TEXT
);
CREATE INDEX IF NOT EXISTS ix_work_orders_hydrant ON work_orders(hydrant_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    at         TEXT NOT NULL,
    actor      TEXT NOT NULL,
    action     TEXT NOT NULL,
    entity     TEXT NOT NULL,
    entity_id  TEXT NOT NULL,
    before     TEXT,
    after      TEXT,
    trace_id   TEXT NOT NULL DEFAULT ''
);
"""


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
