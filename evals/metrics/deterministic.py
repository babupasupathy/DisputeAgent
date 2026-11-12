"""Deterministic per-case checks against the rule-derived labels."""
from __future__ import annotations

from evals.metrics.fabrication import check as fabrication_check
from evals.metrics.letter_checks import check as letter_check


def score_case(case: dict, result: dict) -> dict:
    L, d = case["labels"], case["dispute"]
    out = result.get("output")
    if out is None:
        return {"case_id": case["case_id"], "error": result.get("error", "no output")}
    cls, ev, dec = out["classification"], out["evidence"], out["decision"]

    # classification
    classification = {
        "category_correct": cls["category"] == L["category"],
        "reason_code_correct": cls["reason_code"].strip().upper() == L["reason_code"].upper()
                               and cls["network"] == L["network"],
    }

    # evidence completeness
    lab_req, lab_present = set(L["required_evidence"]), set(L["required_present"])
    lab_missing, lab_strong = set(L["required_missing"]), set(L["strong_present"])
    a_present, a_missing, a_strong = set(ev["required_present"]), set(ev["required_missing"]), set(ev["strong_present"])
    false_missing = sorted(lab_present - a_present)          # really there, agent did not credit it
    false_present = sorted(lab_missing & a_present)           # agent claims an item that is not there
    strong_tp = len(lab_strong & a_strong)
    evidence = {
        "required_set_correct": (a_present | a_missing) == lab_req,
        "required_exact": a_present == lab_present and a_missing == lab_missing,
        "false_missing": false_missing,
        "false_present": false_present,
        "n_required": len(lab_req),
        "n_label_present": len(lab_present),
        "strong_tp": strong_tp, "strong_fp": len(a_strong - lab_strong), "strong_fn": len(lab_strong - a_strong),
    }

    # decision & escalation
    action = dec["action"]
    decision = {
        "predicted": action, "expected": L["decision"], "correct": action == L["decision"],
        "wrongful_auto_accept": action == "accept" and L["decision"] != "accept",
        "wrongful_auto_accept_amount": d["amount"] if (action == "accept" and L["decision"] != "accept") else 0.0,
        "fought_should_escalate": action == "fight" and L["decision"] == "escalate",
    }
    escalation = {"predicted": action == "escalate", "expected": L["expected_escalation"]}

    # tool use (versions with tools)
    called = [c["tool"] for c in result.get("tool_calls") or []]
    if result.get("tool_calls") is not None and called:
        req, unneeded = set(L["required_tools"]), set(L["unneeded_tools"])
        tool_use = {"applicable": True, "required_called": len(req & set(called)) / len(req),
                    "all_required_called": req <= set(called),
                    "unneeded_called": sorted(set(called) & unneeded), "n_calls": len(called)}
    else:
        tool_use = {"applicable": False}

    fab = fabrication_check(out, d, result.get("trace") or [])
    letter = letter_check((out.get("draft") or {}).get("narrative", ""))
    return {"case_id": case["case_id"], "category": L["category"], "scenario": case["scenario"],
            "classification": classification, "evidence": evidence, "decision": decision,
            "escalation": escalation, "tool_use": tool_use, "fabrication": fab, "letter": letter,
            "usage": result.get("usage", {})}
