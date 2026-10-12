from conftest import READ, WRITE


def _hid(client) -> str:
    return client.get("/hydrants", params={"size": 1, "page": 3}, headers=READ).json()["items"][0]["hydrant_id"]


def test_create_and_read_work_order(client):
    hid = _hid(client)
    r = client.post(
        "/work-orders",
        json={"hydrant_id": hid, "kind": "replace_cap", "priority": "high", "description": "Steamer cap missing"},
        headers=WRITE,
    )
    assert r.status_code == 201, r.text
    wo = r.json()
    assert wo["status"] == "open"
    assert wo["created_by"] == "writer"
    assert client.get(f"/work-orders/{wo['id']}", headers=READ).json()["kind"] == "replace_cap"


def test_assign_work_order(client):
    hid = _hid(client)
    wo = client.post(
        "/work-orders", json={"hydrant_id": hid, "kind": "paint", "description": "Needs paint"}, headers=WRITE
    ).json()
    r = client.patch(f"/work-orders/{wo['id']}", json={"status": "assigned", "assigned_to": "Crew 2"}, headers=WRITE)
    assert r.status_code == 200
    assert r.json()["assigned_to"] == "Crew 2"
    audit = client.get("/audit", params={"entity": "work_order", "entity_id": str(wo["id"])}, headers=WRITE).json()
    assert [e["action"] for e in audit["items"]] == ["work_order.update", "work_order.create"]
    assert audit["items"][0]["before"]["status"] == "open"
    assert audit["items"][0]["after"]["status"] == "assigned"


def test_filter_by_status(client):
    hid = _hid(client)
    client.post("/work-orders", json={"hydrant_id": hid, "kind": "flush", "description": "Annual flush"}, headers=WRITE)
    r = client.get("/work-orders", params={"status": "open"}, headers=READ).json()
    assert r["total"] >= 1
    assert all(w["status"] == "open" for w in r["items"])


def test_bad_kind_is_rejected(client):
    hid = _hid(client)
    r = client.post("/work-orders", json={"hydrant_id": hid, "kind": "demolish", "description": "x" * 5}, headers=WRITE)
    assert r.status_code == 422


def test_unknown_work_order_is_404(client):
    assert client.get("/work-orders/999999", headers=READ).status_code == 404
