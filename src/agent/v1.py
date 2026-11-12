"""V1: records fetched in code; rules table, evidence checks, P(win), EV and the decision rules in code
(src/agent/decide.py); the model only reads free text and writes the letter.

Model steps (ANTHROPIC_MODEL, same as V0):
  1. reader: category for ambiguous reason codes + four text facts, each with a quote that code verifies.
     Skipped when the category is unambiguous and there is no human-written message to read.
  2. writer: letter for fight / escalate only, from a verified fact sheet. Accept gets a template.
Output uses the shared schema (src/agent/schema.py); V1 adds a top-level "review" block for the reviewer.
"""
from __future__ import annotations

import json

from src.agent.context import full_context
from src.agent.decide import TEXT_FACTS, decide
from src.agent.llm import Usage, agent_config, structured_call
from src.agent.prompts import v1_reader_schema, v1_reader_system, v1_writer_schema, v1_writer_system
from src.knowledge.rules import lookup, rules_for

VERSION = "v1"


def _verify(facts: dict, messages: list[dict]) -> tuple[dict, list[str]]:
    """Keep a fact only if its quote appears in the cited message from the right sender."""
    by_id = {m["message_id"]: m for m in messages}
    want = {"customer_ack_receipt": "customer"}  # the other three must come from the merchant's agent
    out, warnings = {}, []
    for k in TEXT_FACTS:
        f = facts.get(k) or {}
        ok = False
        if f.get("present"):
            m = by_id.get(f.get("message_id", ""))
            sender_ok = m is not None and m["sender"] == want.get(k, "agent")
            quote = (f.get("quote") or "").strip()
            ok = bool(m) and sender_ok and bool(quote) and quote in m["body"]
            if not ok:
                warnings.append(f"{k}: reader said present but the quote/message did not verify ({f.get('message_id')})")
        out[k] = {"present": ok, "message_id": f.get("message_id") if ok else None,
                  "quote": f.get("quote") if ok else None}
    return out, warnings


def _read(client, model, usage, dispute: dict, candidates: list[str], messages: list[dict]) -> dict:
    human = [m for m in messages if m["sender"] != "system"]
    if len(candidates) == 1 and not human:
        return {"category": candidates[0], "category_rationale": "Single category for this reason code; no "
                "human-written messages to read.", "facts": {k: {"present": False} for k in TEXT_FACTS}, "skipped": True}
    cfg = agent_config()["v1_reader"]
    user = (f"Issuer's note: {dispute.get('issuer_message') or '(empty)'}\n"
            f"Network {dispute['network']}, reason code {dispute['reason_code']}, processor category "
            f"'{dispute['reason_category']}'.\nCandidate categories: {', '.join(candidates)}\n\n"
            f"Support messages:\n{json.dumps(messages, indent=1)}")
    res, _ = structured_call(client, model=model, system=v1_reader_system(),
                             messages=[{"role": "user", "content": user}], schema=v1_reader_schema(candidates),
                             effort=cfg["effort"], max_tokens=cfg["max_tokens"], usage=usage)
    return res


def _fact_sheet(dispute: dict, rule, dec, facts: dict) -> dict:
    return {
        "dispute": {k: dispute[k] for k in ("dispute_id", "order_id", "network", "reason_code", "amount",
                                            "currency", "issuer_message")},
        "reason": f"{rule.network} {rule.reason_code} {rule.reason_name} ({dec.category})",
        "evidence_the_network_expects": [f for f in dec.findings if f["evidence_id"] in rule.required_evidence],
        "evidence_that_strengthens": [f for f in dec.findings if f["evidence_id"] in rule.strong_evidence],
        "customer_messages_cited": {k: v for k, v in facts.items() if v["present"]},
        "refunds_before_dispute": dec.refunded_before_dispute,
        "full_refund_before_dispute": dec.credit_full,
        "decision": {"action": dec.action, "why": dec.rationale, "conflicts": dec.conflicts},
    }


def run_case(client, conn, dispute: dict, model: str) -> dict:
    usage = Usage()
    trace = full_context(conn, dispute)
    rec = {t["tool"]: t["output"] for t in trace}
    d = rec["get_dispute_details"]
    rows = rules_for(d["network"], d["reason_code"])
    if not rows:
        raise ValueError(f"no rules-table row for {d['network']} {d['reason_code']}")
    candidates = sorted({r.category for r in rows})
    messages = rec["get_support_communications"]["messages"]

    read = _read(client, model, usage, d, candidates, messages)
    facts, warnings = _verify(read.get("facts") or {}, messages)
    rule = lookup(d["network"], d["reason_code"], read["category"])
    dec = decide(rec, rule, facts)

    notes = list(warnings)
    if dec.action in ("fight", "escalate"):
        cfg = agent_config()["v1_writer"]
        sheet = _fact_sheet(d, rule, dec, facts)
        user = (f"Fact sheet:\n{json.dumps(sheet, indent=1)}\n\nRecords:\n"
                f"{json.dumps(rec, indent=1, sort_keys=True)}")
        w, _ = structured_call(client, model=model, system=v1_writer_system(),
                               messages=[{"role": "user", "content": user}], schema=v1_writer_schema(),
                               effort=cfg["effort"], max_tokens=cfg["max_tokens"], usage=usage)
        draft = {"narrative": w["narrative"], "evidence_list": w["evidence_list"]}
        notes += w["reviewer_notes"]
    else:
        plain = {"deadline_passed": "the response deadline has passed",
                 "merchant_at_fault": "the records show the merchant at fault",
                 "negative_expected_value": "the cost of contesting exceeds the expected recovery"}[dec.rule_fired]
        draft = {"narrative": f"The merchant accepts this dispute and will not contest it because {plain}.",
                 "evidence_list": []}

    output = {
        "classification": {"network": d["network"], "reason_code": d["reason_code"], "category": dec.category,
                           "rationale": read.get("category_rationale", "")},
        "evidence": {"required_present": dec.required_present, "required_missing": dec.required_missing,
                     "strong_present": dec.strong_present, "findings": dec.findings},
        "assessment": {"conflicts": dec.conflicts, "merchant_at_fault": bool(dec.merchant_fault),
                       "refund_already_issued": dec.refunded_before_dispute, "hours_remaining": dec.hours_remaining,
                       "prior_disputes": dec.prior_disputes, "p_win": dec.p_win, "expected_value": dec.expected_value,
                       "confidence": 0.5 if warnings else 1.0},
        "decision": {"action": dec.action,
                     "escalation_reasons": dec.triggers if dec.action == "escalate" else [],
                     "rationale": dec.rationale},
        "draft": draft,
        "review": {"rule_fired": dec.rule_fired, "reviewer_notes": notes, "text_facts": facts,
                   "reader_skipped": bool(read.get("skipped"))},
    }
    return {"output": output, "trace": trace, "tool_calls": [], "usage": usage.to_dict()}
