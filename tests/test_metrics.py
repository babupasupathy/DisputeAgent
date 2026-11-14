"""The scoring harness must catch errors, not just pass the oracle."""
import copy
import json
from types import SimpleNamespace

import pytest

from evals.metrics.deterministic import score_case
from evals.metrics.fabrication import check
from evals import oracle


@pytest.fixture(scope="module")
def conn(fresh_build):
    from src.backend.db import connect
    db, _ = fresh_build
    c = connect(db)
    yield c
    c.close()


def _case(cases, cid):
    return next(c for c in cases if c["case_id"] == cid)


def test_oracle_is_clean(conn, committed_cases):
    for c in committed_cases[:30]:
        s = score_case(c, oracle.run_case(conn, c))
        assert s["decision"]["correct"] and s["evidence"]["required_exact"]
        assert not s["fabrication"]["fabricated"], s["fabrication"]


def test_fabrication_catches_invented_facts(conn, committed_cases):
    c = _case(committed_cases, "GEN-002")
    r = oracle.run_case(conn, c)
    r["output"]["draft"]["narrative"] += (" Tracking SYN1Z999999999999 shows delivery on 2019-02-03; "
                                          "the cardholder was refunded $12.34 on card ending 9999. See ORD-999999.")
    f = check(r["output"], c["dispute"], r["trace"])
    assert f["fabricated"]
    assert set(f["unsupported"]) == {"tracking", "dates", "amounts", "card", "ids"}


def test_fabrication_allows_real_and_derived_facts(conn, committed_cases):
    c = _case(committed_cases, "HW-13")  # $600 order, 50% refund -> $300 balance is derived
    r = oracle.run_case(conn, c)
    track = next(t["output"] for t in r["trace"] if t["tool"] == "get_shipping_tracking")
    deliv = track["delivered_at"][:10]
    r["output"]["draft"]["narrative"] += (f" Delivered {deliv} via {track['tracking_number']}. "
                                          f"We refunded $300.00, leaving $300.00 of the $600.00 order.")
    f = check(r["output"], c["dispute"], r["trace"])
    assert not f["fabricated"], f


def test_metrics_detect_errors(conn, committed_cases):
    c = _case(committed_cases, "GEN-002")   # INR strong -> fight, all required present
    r = oracle.run_case(conn, c)
    bad = copy.deepcopy(r)
    ev = bad["output"]["evidence"]
    ev["required_present"].remove("delivery_confirmation")
    ev["required_missing"].append("delivery_confirmation")
    bad["output"]["decision"]["action"] = "accept"
    bad["output"]["classification"]["category"] = "fraud"
    s = score_case(c, bad)
    assert s["evidence"]["false_missing"] == ["delivery_confirmation"]
    assert s["decision"]["wrongful_auto_accept"] and s["decision"]["wrongful_auto_accept_amount"] == c["dispute"]["amount"]
    assert not s["classification"]["category_correct"]


class FakeClient:
    """Records the request and returns a canned structured response."""
    def __init__(self, payload):
        self.payload, self.requests = payload, []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.requests.append(kw)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=json.dumps(self.payload))], stop_reason="end_turn",
            model=kw["model"], usage=SimpleNamespace(input_tokens=1000, output_tokens=500,
                                                     cache_read_input_tokens=0, cache_creation_input_tokens=0))


def test_v0_request_shape_and_cost(conn, committed_cases):
    from src.agent import v0
    c = _case(committed_cases, "GEN-002")
    payload = oracle.run_case(conn, c)["output"]
    client = FakeClient(payload)
    r = v0.run_case(client, conn, c["dispute"], "claude-sonnet-5-5")
    req = client.requests[0]
    assert req["model"] == "claude-sonnet-5-5" and "tools" not in req
    assert req["output_config"]["format"]["type"] == "json_schema"
    user = req["messages"][0]["content"]
    assert c["dispute"]["order_id"] in user and "get_shipping_tracking" in user   # everything pasted in
    assert "required_evidence" not in req["system"][0]["text"]                     # no rules table in V0
    assert r["usage"]["cost_usd"] == pytest.approx((1000 * 2 + 500 * 10) / 1e6)
    assert score_case(c, {**r, "tool_calls": []})["decision"]["correct"]


def test_model_name_comes_from_env(monkeypatch):
    from src.agent.llm import model_from_env
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    with pytest.raises(RuntimeError):
        model_from_env()
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    assert model_from_env() == "claude-sonnet-5-5"


def test_judge_parses_and_applies_pass_rule(conn, committed_cases):
    from evals.metrics.judge import CRITERIA, judge_draft
    c = _case(committed_cases, "GEN-002")
    r = oracle.run_case(conn, c)
    good = {"criteria": {k: {"reasoning": "ok", "score": 5} for k in CRITERIA},
            "issues": [{"claim": "accepted at checkout", "problem": "timing not recorded", "severity": "minor"}]}
    j = judge_draft(FakeClient(good), "claude-opus-5-5", c["dispute"], "item_not_received", r["trace"], r["output"])
    assert j["pass"] and j["usage"]["cost_usd"] == pytest.approx((1000 * 4 + 500 * 20) / 1e6)
    bad = {"criteria": {k: {"reasoning": "x", "score": 5} for k in CRITERIA},
           "issues": [{"claim": "signed for by the cardholder", "problem": "signature_on_file is false",
                       "severity": "material"}]}
    jb = judge_draft(FakeClient(bad), "claude-opus-5-5", c["dispute"], "item_not_received", r["trace"], r["output"])
    assert not jb["pass"] and len(jb["unsupported_claims"]) == 1
    assert j["unsupported_claims"] == []  # minor issues are not counted as unsupported claims


def test_judge_pass_rule_fails_only_on_material_issues():
    from evals.metrics.judge import passes
    good = {"addresses_requirements": 5, "grounded": 4, "clarity": 5, "format": 4}
    minor = [{"claim": "accepted at checkout", "problem": "timing not recorded", "severity": "minor"}]
    material = [{"claim": "pending internal review", "problem": "no record of any review", "severity": "material"}]
    assert passes(good, [])
    assert passes(good, minor)
    assert not passes(good, material)
    assert not passes(good, minor + material)
    assert not passes({**good, "format": 3}, [])


def test_letter_checks_flag_concessions_not_gap_notes():
    from evals.metrics.letter_checks import check
    gap = "Delivered on 2026-09-01. Note for reviewer: no signature is on file. We request a reversal."
    conc = "Internal reviewer note: recommend accepting this dispute or issuing the refund instead of contesting."
    plain = "The carrier confirmed delivery. The customer acknowledged receipt by email."
    assert check(gap)["reviewer_note"] and not check(gap)["concession"]
    assert check(conc)["reviewer_note"] and check(conc)["concession"]
    assert check(plain) == {"reviewer_note": False, "concession": False, "notes": [], "concessions": [], "field_names": []}
    leak = check("The carrier shows delivered_address_match = True; device dev_045ed4ea5a4b matched ORD-100742.")
    assert leak["field_names"] == ["delivered_address_match", "dev_045ed4ea5a4b"]
