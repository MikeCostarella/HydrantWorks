from conftest import READ, WRITE


def test_out_of_service_and_back(client):
    hid = client.get("/hydrants", params={"size": 1, "page": 2}, headers=READ).json()["items"][0]["hydrant_id"]
    r = client.post(f"/hydrants/{hid}/out-of-service", json={"reason": "Hit by a car"}, headers=WRITE)
    assert r.status_code == 200
    assert r.json()["status"] == "out_of_service"

    oos = client.get("/hydrants", params={"status": "out_of_service"}, headers=READ).json()
    assert oos["total"] == 1

    back = client.post(f"/hydrants/{hid}/in-service", json={"reason": "Replaced"}, headers=WRITE)
    assert back.json()["status"] == "in_service"

    log = client.get("/audit", params={"entity": "hydrant", "entity_id": hid}, headers=WRITE).json()["items"]
    assert [e["action"] for e in log] == ["hydrant.in_service", "hydrant.out_of_service"]
    assert log[1]["before"]["status"] == "in_service"


def test_status_change_needs_a_reason(client):
    hid = client.get("/hydrants", params={"size": 1, "page": 2}, headers=READ).json()["items"][0]["hydrant_id"]
    r = client.post(f"/hydrants/{hid}/out-of-service", json={"reason": ""}, headers=WRITE)
    assert r.status_code == 422
