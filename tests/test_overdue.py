import random
from datetime import UTC, datetime, timedelta

from hydrantworks import repository as repo


def test_never_inspected_is_overdue():
    assert repo.is_overdue(None, datetime.now(UTC))


def test_recent_inspection_is_not_overdue():
    now = datetime(2026, 9, 1, tzinfo=UTC)
    assert not repo.is_overdue((now - timedelta(days=30)).isoformat(), now)


def test_overdue_count_matches_ages(client):
    """Inspect hydrants at assorted ages and check the overdue list agrees."""
    conn = client.app.state.conn
    now = datetime.now(UTC)
    hydrants = [r[0] for r in conn.execute("SELECT hydrant_id FROM hydrants ORDER BY hydrant_id LIMIT 10")]
    ages = {hid: random.randint(330, 430) for hid in hydrants}
    for hid, age in ages.items():
        when = (now - timedelta(days=age)).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO inspections (hydrant_id, inspected_at, inspector, cap_condition, operable, leaking)"
            " VALUES (?, ?, 'Crew 1', 'good', 1, 0)",
            (hid, when),
        )
    conn.commit()
    expected = sum(1 for age in ages.values() if age > 365)
    _, total = repo.list_overdue(conn, None, 1, 500, now)
    never_inspected = 36 - len(hydrants)
    assert total - never_inspected == expected
