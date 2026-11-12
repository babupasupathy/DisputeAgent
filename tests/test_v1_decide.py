"""V1's decision code, given the true text facts and category, must reproduce the answer key on
every case. This checks the code's fidelity to the written policy, with no model involved."""
import pytest

from src.agent.context import full_context
from src.agent.decide import TEXT_FACTS, decide
from src.backend.db import connect
from src.knowledge.rules import lookup


@pytest.fixture(scope="module")
def conn(fresh_build):
    db, _ = fresh_build
    c = connect(db)
    yield c
    c.close()


def _true_facts(conn, order_id):
    tags = {r["tag"]: r["message_id"] for r in conn.execute(
        "SELECT l.tag, m.message_id FROM _gen_message_labels l JOIN support_messages m USING(message_id) "
        "WHERE m.order_id=?", (order_id,))}
    return {f: {"present": f in tags, "message_id": tags.get(f), "quote": ""} for f in TEXT_FACTS}


def test_decision_code_matches_answer_key_given_true_inputs(conn, committed_cases):
    mismatches = []
    for case in committed_cases:
        d, lab = case["dispute"], case["labels"]
        rec = {t["tool"]: t["output"] for t in full_context(conn, d)}
        dec = decide(rec, lookup(d["network"], d["reason_code"], lab["category"]), _true_facts(conn, d["order_id"]))
        got = (dec.action, dec.rule_fired, sorted(dec.required_present), sorted(dec.strong_present),
               sorted(dec.conflicts), round(dec.expected_value, 2), dec.prior_disputes)
        want = (lab["decision"], lab["decision_reason"], sorted(lab["required_present"]), sorted(lab["strong_present"]),
                sorted(lab["conflicts"]), round(lab["expected_value"], 2), lab["prior_disputes_365d"])
        if got != want:
            mismatches.append((case["case_id"], got, want))
    assert not mismatches, mismatches[:5]
