"""Ground-truth dataset checks: determinism, coverage, scenario intent, hand-written cases."""
import json
from collections import Counter

from evals.paths import CASES_DIR

INTENT = {  # scenario -> allowed decisions, applied to generated cases
    "strong": {"fight"},
    "weak": {"accept", "escalate"},
    "conflicting": {"escalate"},
    "deadline_near": {"escalate"},
    "deadline_passed": {"accept"},
    "partial_refund_mismatch": {"escalate"},
    "partial_refund_consistent": {"fight"},
    "full_refund": {"fight"},
    "high_value": {"escalate"},
    "repeat_disputer": {"escalate"},
    "low_amount": {"accept"},
    "merchant_fault": {"accept"},
}


def test_regeneration_is_deterministic_and_matches_committed(fresh_build, committed_cases):
    _, cases = fresh_build
    assert [json.dumps(c, sort_keys=True) for c in cases] == \
           [json.dumps(c, sort_keys=True) for c in committed_cases]


def test_scenario_intent_matches_derived_label(committed_cases):
    bad = [(c["case_id"], c["scenario"], c["labels"]["decision"], c["labels"]["decision_reason"])
           for c in committed_cases if c["source"] == "generated"
           and c["labels"]["decision"] not in INTENT[c["scenario"]]]
    assert not bad, bad


def test_handwritten_expectations(committed_cases):
    exp = json.load(open(CASES_DIR / "handwritten_expectations.json"))
    hw = {c["case_id"]: c["labels"] for c in committed_cases if c["source"] == "handwritten"}
    assert set(hw) == {k for k in exp if not k.startswith("_")}
    mismatches = {cid: {k: (v, hw[cid][k]) for k, v in e.items() if hw[cid][k] != v}
                  for cid, e in exp.items() if not cid.startswith("_")}
    assert not any(mismatches.values()), mismatches


def test_coverage(committed_cases):
    gen = [c for c in committed_cases if c["source"] == "generated"]
    by = Counter((c["labels"]["category"], c["scenario"]) for c in gen)
    for cat in ("item_not_received", "fraud", "not_as_described"):
        for scen in ("strong", "weak", "conflicting", "deadline_near", "partial_refund_mismatch",
                     "high_value", "repeat_disputer"):
            assert by[(cat, scen)] >= 2, (cat, scen)
    decisions = Counter(c["labels"]["decision"] for c in committed_cases)
    assert all(decisions[d] >= 30 for d in ("fight", "accept", "escalate")), decisions
    nets = Counter(c["labels"]["network"] for c in committed_cases)
    assert set(nets) == {"visa", "mastercard", "amex"}


def test_labels_internally_consistent(committed_cases):
    for c in committed_cases:
        L = c["labels"]
        assert set(L["required_present"]) | set(L["required_missing"]) == set(L["required_evidence"])
        assert not set(L["required_present"]) & set(L["required_missing"])
        assert c["dispute"]["network"] == L["network"]
        if c["dispute"]["network"] == "mastercard" and c["dispute"]["reason_code"] == "4853":
            assert c["dispute"]["reason_category"] == "general" and c["dispute"]["issuer_message"]


def test_unique_customers_per_case(fresh_build, committed_cases):
    from src.backend.db import connect
    db, _ = fresh_build
    conn = connect(db)
    custs = [conn.execute("SELECT customer_id FROM disputes WHERE dispute_id=?",
                          (c["dispute"]["dispute_id"],)).fetchone()[0] for c in committed_cases]
    assert len(custs) == len(set(custs))


def test_message_timeline_is_coherent(fresh_build, committed_cases):
    """Narrative sanity: 'where is my order' precedes delivery; nothing is dated after the dispute."""
    from src.backend import repository as repo
    from src.backend.db import connect
    db, _ = fresh_build
    conn = connect(db)
    for c in committed_cases:
        d = c["dispute"]
        ship = repo.get_shipping_tracking(conn, d["order_id"])
        for m in repo.get_support_communications(conn, d["order_id"])["messages"]:
            assert m["ts"] < d["received_at"], (c["case_id"], m)
            asks_status = any(k in m["body"] for k in ("tracking", "still coming", "when my package"))
            if m["sender"] == "customer" and asks_status and "shows delivered" not in m["body"] \
                    and ship.get("delivered_at"):
                assert m["ts"] < ship["delivered_at"], (c["case_id"], m)
