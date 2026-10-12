"""Load the hydrant inventory and generate the synthetic work history.

The hydrant inventory (data/hydrants.csv) is real: the Trumbull County
Auditor's hydrant export, 7,126 hydrants, as published in the Trumbull County
Hydrants map. Everything else — inspections, work orders, out-of-service
notices — is SYNTHETIC sample data generated here from a fixed random seed.
It is not a record of any real inspection or repair.

Run directly to rebuild the database from scratch:

    python -m hydrantworks.seed
"""

from __future__ import annotations

import csv
import random
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .config import load_settings
from .db import connect, create_schema, transaction

SEED = 2026
# Synthetic history is generated relative to this fixed date so every copy of
# the database starts identical. "Overdue" is computed against the real clock.
ANCHOR = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
CREWS = [f"Crew {n}" for n in range(1, 9)]
DISPATCHERS = ["dispatch-warren", "dispatch-howland", "dispatch-niles", "dispatch-county"]


def _float(v: str) -> float | None:
    return float(v) if v not in ("", None) else None


def _int(v: str) -> int | None:
    return int(v) if v not in ("", None) else None


def load_hydrants(conn: sqlite3.Connection, csv_path: Path) -> int:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = [
            (
                r["hydrant_id"],
                float(r["lat"]),
                float(r["lng"]),
                _float(r["elevation_ft"]),
                r["street"],
                r["alt_street"],
                r["municipality"],
                r["subdivision"],
                r["county"],
                r["state"],
                r["hydrant_type"],
                _int(r["gps_quality"]),
                r["survey_date"] or None,
                r["jurisdiction"],
            )
            for r in csv.DictReader(f)
        ]
    with transaction(conn):
        conn.executemany(
            "INSERT INTO hydrants (hydrant_id, lat, lng, elevation_ft, street, alt_street, municipality,"
            " subdivision, county, state, hydrant_type, gps_quality, survey_date, jurisdiction)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
    return len(rows)


def _note(rng: random.Random, cap: str, operable: bool, leaking: bool, static: float) -> str:
    parts = [rng.choice(["Opened and closed fully.", "Operated full turn.", "Opened OK.", "Flushed 2 min."])]
    if not operable:
        parts = [rng.choice(["Stem will not turn.", "Could not open, operating nut rounded.", "Seized, no flow."])]
    if cap == "missing":
        parts.append(rng.choice(["Steamer cap missing.", "Side cap gone.", "Pumper cap missing, chained."]))
    elif cap == "worn":
        parts.append(rng.choice(["Cap threads worn.", "Cap gasket cracked."]))
    if leaking:
        parts.append(rng.choice(["Slow leak at base.", "Weeping at barrel flange.", "Leaks when shut."]))
    if static < 35:
        parts.append("Low pressure.")
    if rng.random() < 0.15:
        extras = ["Needs paint.", "Weeds around barrel.", "Bollard knocked down.", "Reflector missing."]
        parts.append(rng.choice(extras))
    return " ".join(parts)


def generate_work_history(conn: sqlite3.Connection) -> dict[str, int]:
    rng = random.Random(SEED)
    hydrant_ids = [r[0] for r in conn.execute("SELECT hydrant_id FROM hydrants ORDER BY hydrant_id")]
    inspections: list[tuple] = []
    work_orders: list[tuple] = []
    out_of_service: list[tuple[str, str]] = []

    start = datetime(2022, 6, 1, tzinfo=UTC)
    span_days = (ANCHOR - start).days

    for hid in hydrant_ids:
        if rng.random() < 0.22:
            continue  # never inspected in the system
        for _ in range(rng.choice([1, 1, 2, 2, 3, 4])):
            when = start + timedelta(days=rng.randrange(span_days), hours=rng.randrange(13, 22))
            cap = rng.choices(["good", "worn", "missing"], weights=[86, 10, 4])[0]
            operable = rng.random() > 0.03
            leaking = rng.random() < 0.05
            static = round(rng.gauss(62, 12), 1)
            residual = round(max(10.0, static - abs(rng.gauss(14, 6))), 1)
            flow = round(rng.gauss(1150, 250), 0) if operable and rng.random() < 0.6 else None
            inspections.append(
                (
                    hid,
                    when.isoformat(timespec="seconds"),
                    rng.choice(CREWS),
                    static if operable else None,
                    residual if operable else None,
                    flow,
                    cap,
                    int(operable),
                    int(leaking),
                    _note(rng, cap, operable, leaking, static),
                    "seed",
                )
            )
            problem = None
            if not operable:
                problem = ("repair", "urgent", "Hydrant inoperable at inspection.")
            elif leaking:
                problem = ("repair", "high", "Leak reported at inspection.")
            elif cap == "missing":
                problem = ("replace_cap", "normal", "Cap missing at inspection.")
            if problem and rng.random() < 0.85:
                created = when + timedelta(hours=rng.randrange(1, 48))
                closed = created + timedelta(days=rng.randrange(2, 60))
                is_closed = closed < ANCHOR and rng.random() < 0.8
                work_orders.append(
                    (
                        hid,
                        problem[0],
                        problem[1],
                        "closed" if is_closed else rng.choice(["open", "assigned"]),
                        rng.choice(CREWS) if is_closed or rng.random() < 0.5 else "",
                        problem[2],
                        created.isoformat(timespec="seconds"),
                        rng.choice(DISPATCHERS),
                        closed.isoformat(timespec="seconds") if is_closed else None,
                    )
                )
                if not operable and not is_closed:
                    out_of_service.append((hid, "Inoperable at inspection; repair pending."))

    with transaction(conn):
        conn.executemany(
            "INSERT INTO inspections (hydrant_id, inspected_at, inspector, static_psi, residual_psi, flow_gpm,"
            " cap_condition, operable, leaking, notes, source) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            inspections,
        )
        conn.executemany(
            "INSERT INTO work_orders (hydrant_id, kind, priority, status, assigned_to, description, created_at,"
            " created_by, closed_at) VALUES (?,?,?,?,?,?,?,?,?)",
            work_orders,
        )
        conn.executemany(
            "UPDATE hydrants SET status = 'out_of_service', status_reason = ? WHERE hydrant_id = ?",
            [(reason, hid) for hid, reason in out_of_service],
        )
    return {"inspections": len(inspections), "work_orders": len(work_orders), "out_of_service": len(out_of_service)}


def build_database(db_path: Path, csv_path: Path, with_work_data: bool = True) -> dict[str, int]:
    """Create a fresh database file. An existing file at db_path is replaced."""
    if db_path.exists():
        db_path.unlink()
    conn = connect(db_path)
    try:
        create_schema(conn)
        counts = {"hydrants": load_hydrants(conn, csv_path)}
        if with_work_data:
            counts.update(generate_work_history(conn))
        return counts
    finally:
        conn.close()


if __name__ == "__main__":
    s = load_settings()
    result = build_database(s.db_path, s.hydrants_csv, s.seed_work_data)
    print(f"Built {s.db_path}: " + ", ".join(f"{v:,} {k.replace('_', ' ')}" for k, v in result.items()))
