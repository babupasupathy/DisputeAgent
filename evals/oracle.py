"""Oracle 'agent' that answers from the labels. Not a real version: it exists to validate the
scoring harness (it must score 100% on every deterministic dimension and 0 fabrications)."""
from __future__ import annotations

from src.agent.context import full_context


def run_case(conn, case: dict) -> dict:
    L, d = case["labels"], case["dispute"]
    trace = full_context(conn, d)
    order = next(t["output"] for t in trace if t["tool"] == "get_order_details")
    narrative = (f"Re: dispute {d['dispute_id']} for order {order['order_id']} (${d['amount']:.2f}). "
                 f"Evidence on file: {', '.join(L['required_present']) or 'none'}.")
    output = {
        "classification": {"network": L["network"], "reason_code": L["reason_code"], "category": L["category"],
                           "rationale": "oracle"},
        "evidence": {"required_present": L["required_present"], "required_missing": L["required_missing"],
                     "strong_present": L["strong_present"], "findings": []},
        "assessment": {"conflicts": L["conflicts"], "merchant_at_fault": bool(L["merchant_fault"]),
                       "refund_already_issued": L["refunded_before_dispute"], "hours_remaining": L["hours_remaining"],
                       "prior_disputes": L["prior_disputes_365d"], "p_win": L["p_win"],
                       "expected_value": L["expected_value"], "confidence": 1.0},
        "decision": {"action": L["decision"], "escalation_reasons": [], "rationale": L["decision_reason"]},
        "draft": {"narrative": narrative, "evidence_list": []},
    }
    return {"output": output, "trace": trace, "tool_calls": [{"tool": t} for t in L["required_tools"]],
            "usage": {"cost_usd": 0.0, "latency_s": 0.0}}
