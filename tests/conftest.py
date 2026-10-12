from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hydrantworks.config import Settings
from hydrantworks.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"
READ = {"X-API-Key": "test-read"}
WRITE = {"X-API-Key": "test-write"}


def make_settings(tmp_path: Path, **overrides) -> Settings:
    base = dict(
        db_path=tmp_path / "test.db",
        hydrants_csv=FIXTURES / "hydrants_small.csv",
        read_key="test-read",
        write_key="test-write",
        seed_work_data=False,
    )
    base.update(overrides)
    return Settings(**base)


@pytest.fixture
def client(tmp_path: Path):
    with TestClient(create_app(make_settings(tmp_path))) as c:
        yield c


@pytest.fixture
def make_client(tmp_path: Path):
    """For tests that need non-default settings (chaos mode, a request log)."""
    clients = []

    def _make(**overrides):
        c = TestClient(create_app(make_settings(tmp_path, **overrides)))
        c.__enter__()
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)
