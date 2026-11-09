import json
import re
from pathlib import Path

import pytest

from src.backend import repository as repo
from src.backend.db import connect

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def conn(fresh_build):
    db, _ = fresh_build
    c = connect(db)
    yield c
    c.close()


def _all_outputs(conn, case):
    d = case["dispute"]
    order = repo.get_order_details(conn, d["order_id"])
    return [order, repo.get_shipping_tracking(conn, d["order_id"]),
            repo.get_customer_history(conn, order["customer_id"]),
            repo.get_support_communications(conn, d["order_id"]), repo.get_refund_status(conn, d["order_id"]),
            repo.get_dispute_details(conn, d["dispute_id"]), repo.check_deadline(conn, d["dispute_id"])]


def test_outputs_are_masked(conn, committed_cases):
    raw = conn.execute("SELECT billing_address, ip_address FROM orders").fetchall()
    raw_ips = {r[1] for r in raw}
    for case in committed_cases[:40]:
        blob = json.dumps(_all_outputs(conn, case))
        assert not any(ip in blob for ip in raw_ips)
        assert not re.search(r"\b\d{2,4} [A-Z][a-z]+ St\b", blob)       # street numbers masked
        assert not re.search(r"\b\d{13,19}\b", blob)                     # nothing PAN-shaped
        assert not re.search(r"[a-z]{2,}\.[a-z]+\.\d{4}@", blob)         # emails masked


def test_no_generator_metadata_leaks(conn, committed_cases):
    src = (ROOT / "src/backend/repository.py").read_text() + (ROOT / "src/backend/api.py").read_text()
    assert not re.search(r"(FROM|JOIN|INTO)\s+_gen_", src)
    for case in committed_cases[:40]:
        blob = json.dumps(_all_outputs(conn, case))
        for tag in ("customer_ack_receipt", "merchant_offered_remedy", "merchant_admitted_defect",
                    "merchant_ack_nondelivery", "scenario"):
            assert tag not in blob


def test_agent_code_never_reads_eval_cases_or_labeler():
    for p in (ROOT / "src").rglob("*.py"):
        text = p.read_text()
        assert not re.search(r"^\s*(from|import)\s+evals", text, re.M), p
        assert "cases.jsonl" not in text, p


def test_submit_requires_approval(conn, committed_cases):
    did = committed_cases[0]["dispute"]["dispute_id"]
    with pytest.raises(repo.ApprovalRequired):
        repo.submit_response(conn, did, {"x": 1})
    assert repo.submit_response(conn, did, {"x": 1}, approved_by="reviewer-1")["status"] == "submitted"


def test_deadline_matches_label(conn, committed_cases):
    for c in committed_cases:
        got = repo.check_deadline(conn, c["dispute"]["dispute_id"])["hours_remaining"]
        assert got == pytest.approx(c["labels"]["hours_remaining"], abs=0.01)


def test_api_smoke(monkeypatch, fresh_build, committed_cases):
    from fastapi.testclient import TestClient
    import src.backend.api as api
    db, _ = fresh_build
    monkeypatch.setattr(api, "connect", lambda: connect(db))
    client = TestClient(api.app)
    d = committed_cases[0]["dispute"]
    assert client.get(f"/orders/{d['order_id']}").status_code == 200
    assert client.get(f"/processor/disputes/{d['dispute_id']}/deadline").status_code == 200
    assert client.get("/orders/NOPE").status_code == 404
    r = client.post(f"/processor/disputes/{d['dispute_id']}/submit", json={"payload": {}})
    assert r.status_code == 403
