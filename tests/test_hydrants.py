from conftest import READ


def test_list_reports_total(client):
    r = client.get("/hydrants", headers=READ)
    assert r.status_code == 200
    assert r.json()["total"] == 36


def test_list_respects_page_size(client):
    r = client.get("/hydrants", params={"size": 5}, headers=READ)
    assert len(r.json()["items"]) <= 5


def test_filter_by_jurisdiction(client):
    r = client.get("/hydrants", params={"jurisdiction": "Howland Township", "size": 100}, headers=READ)
    body = r.json()
    assert body["total"] == 10
    assert all(h["jurisdiction"] == "Howland Township" for h in body["items"])


def test_filter_by_street_substring(client):
    street = client.get("/hydrants", params={"size": 1, "page": 2}, headers=READ).json()["items"][0]["street"]
    r = client.get("/hydrants", params={"street": street[:5].lower(), "size": 100}, headers=READ).json()
    assert r["total"] >= 1
    assert all(street[:5].lower() in (h["street"] + h["alt_street"]).lower() for h in r["items"])


def test_get_hydrant_and_404(client):
    r = client.get("/hydrants", params={"jurisdiction": "Warren", "size": 1, "page": 2}, headers=READ)
    hid = r.json()["items"][0]["hydrant_id"]
    one = client.get(f"/hydrants/{hid}", headers=READ)
    assert one.status_code == 200
    assert one.json()["county"]
    assert client.get("/hydrants/does-not-exist", headers=READ).status_code == 404


def test_jurisdiction_counts_add_up(client):
    rows = client.get("/jurisdictions", headers=READ).json()
    assert sum(j["hydrants"] for j in rows) == 36
    assert {j["jurisdiction"] for j in rows} >= {"Warren", "Howland Township"}
