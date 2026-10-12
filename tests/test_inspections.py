from conftest import READ, WRITE


def _any_hydrant(client) -> str:
    return client.get("/hydrants", params={"size": 1, "page": 2}, headers=READ).json()["items"][0]["hydrant_id"]


def _inspection(hid: str, **over):
    body = {
        "hydrant_id": hid,
        "inspected_at": "2026-05-04T14:30:00Z",
        "inspector": "Crew 3",
        "static_psi": 64,
        "residual_psi": 50,
        "flow_gpm": 1100,
        "cap_condition": "good",
        "operable": True,
        "leaking": False,
        "notes": "Opened OK.",
    }
    body.update(over)
    return body


def test_create_inspection_in_utc(client):
    hid = _any_hydrant(client)
    r = client.post("/inspections", json=_inspection(hid), headers=WRITE)
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["inspected_at"].startswith("2026-05-04T14:30:00")
    assert created["source"] == "api"
    history = client.get(f"/hydrants/{hid}/inspections", headers=READ).json()
    assert history[0]["id"] == created["id"]


def test_unknown_field_is_rejected(client):
    hid = _any_hydrant(client)
    r = client.post("/inspections", json=_inspection(hid, color="red"), headers=WRITE)
    assert r.status_code == 422


def test_pressure_out_of_range_is_rejected(client):
    hid = _any_hydrant(client)
    r = client.post("/inspections", json=_inspection(hid, static_psi=900), headers=WRITE)
    assert r.status_code == 422


def test_unknown_hydrant_is_404(client):
    r = client.post("/inspections", json=_inspection("no-such-hydrant"), headers=WRITE)
    assert r.status_code == 404


def test_inspection_is_audited_with_trace_id(client):
    hid = _any_hydrant(client)
    r = client.post("/inspections", json=_inspection(hid), headers={**WRITE, "X-Trace-Id": "trace-abc"})
    assert r.headers["X-Trace-Id"] == "trace-abc"
    log = client.get("/audit", params={"entity": "inspection"}, headers=WRITE).json()
    entry = log["items"][0]
    assert entry["action"] == "inspection.create"
    assert entry["actor"] == "writer"
    assert entry["trace_id"] == "trace-abc"
    assert entry["after"]["hydrant_id"] == hid
