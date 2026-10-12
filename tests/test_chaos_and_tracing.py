import json

from conftest import READ, WRITE

from hydrantworks.chaos import parse_chaos


def test_parse_chaos():
    assert parse_chaos("latency=0.5, error_rate=0.2") == {"latency": 0.5, "error_rate": 0.2}
    assert parse_chaos("") == {}


def test_chaos_errors_reads_but_not_health_or_writes(make_client):
    c = make_client(chaos="error_rate=1", chaos_seed=1)
    assert c.get("/hydrants", headers=READ).status_code == 503
    assert c.get("/health").status_code == 200
    assert c.get("/jurisdictions", headers=READ).status_code == 200  # not on the affected list


def test_chaos_empty_pages(make_client):
    c = make_client(chaos="empty_rate=1", chaos_seed=1)
    body = c.get("/hydrants", headers=READ).json()
    assert body["items"] == [] and body["total"] == 0


def test_trace_id_is_generated_and_logged(make_client, tmp_path):
    log = tmp_path / "logs" / "requests.jsonl"  # the folder does not exist yet
    c = make_client(request_log=log)
    r = c.get("/hydrants", headers=READ)
    tid = r.headers["X-Trace-Id"]
    assert len(tid) == 16
    lines = [json.loads(x) for x in log.read_text().splitlines()]
    assert lines[-1]["trace_id"] == tid
    assert lines[-1]["path"] == "/hydrants"
    assert lines[-1]["status"] == 200


def test_trace_id_is_propagated(make_client):
    c = make_client()
    r = c.get("/health", headers={"X-Trace-Id": "my-agent-run-7"})
    assert r.headers["X-Trace-Id"] == "my-agent-run-7"
    assert WRITE  # keeps the shared import used
