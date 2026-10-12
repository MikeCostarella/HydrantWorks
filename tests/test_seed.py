from pathlib import Path

from hydrantworks.db import connect
from hydrantworks.seed import build_database

DATA = Path(__file__).resolve().parent.parent / "data" / "hydrants.csv"


def test_full_inventory_loads(tmp_path):
    counts = build_database(tmp_path / "full.db", DATA, with_work_data=True)
    assert counts["hydrants"] == 7126
    assert counts["inspections"] > 0 and counts["work_orders"] > 0


def test_seed_is_repeatable(tmp_path):
    a = build_database(tmp_path / "a.db", DATA)
    b = build_database(tmp_path / "b.db", DATA)
    assert a == b
    conn = connect(tmp_path / "a.db")
    assert conn.execute("SELECT COUNT(*) FROM hydrants WHERE county <> 'Trumbull'").fetchone()[0] == 33
