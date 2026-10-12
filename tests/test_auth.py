from conftest import READ, WRITE


def test_health_needs_no_key(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_missing_key_is_401(client):
    assert client.get("/hydrants").status_code == 401


def test_wrong_key_is_401(client):
    assert client.get("/hydrants", headers={"X-API-Key": "nope"}).status_code == 401


def test_read_key_can_read(client):
    assert client.get("/hydrants", headers=READ).status_code == 200


def test_read_key_cannot_write(client):
    body = {"hydrant_id": "x", "kind": "paint", "description": "Needs paint"}
    r = client.post("/work-orders", json=body, headers=READ)
    assert r.status_code == 403
    assert "read-only" in r.json()["detail"]


def test_audit_needs_write_key(client):
    assert client.get("/audit", headers=READ).status_code == 403
    assert client.get("/audit", headers=WRITE).status_code == 200
