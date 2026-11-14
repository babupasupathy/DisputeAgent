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


# Owner decision 2026-11-12 ("brief now, letter later"): an escalation caused only by conflicting records
# or missing required evidence gets a reviewer brief and no letter. If the reviewer decides to contest,
# draft_letter() writes the letter then, following the reviewer's direction. Escalations for high value,
# a near deadline or a repeat disputer still get a full letter up front.
BRIEF_ONLY_TRIGGERS = {"conflicting_evidence", "missing_required_evidence"}


def brief_only(dec) -> bool:
    return dec.action == "escalate" and set(dec.triggers) <= BRIEF_ONLY_TRIGGERS


def _write(client, model, usage, sheet: dict, rec: dict, reviewer_direction: str | None = None) -> dict:
    cfg = agent_config()["v1_writer"]
    user = f"Fact sheet:\n{json.dumps(sheet, indent=1)}\n\nRecords:\n{json.dumps(rec, indent=1, sort_keys=True)}"
    if reviewer_direction:
        user = (f"The store's reviewer has decided to contest this dispute. Reviewer's direction: "
                f"{reviewer_direction}\n\n" + user)
    w, _ = structured_call(client, model=model, system=v1_writer_system(),
                           messages=[{"role": "user", "content": user}], schema=v1_writer_schema(),
                           effort=cfg["effort"], max_tokens=cfg["max_tokens"], usage=usage)
    return w


def _brief(d: dict, rec: dict, dec, facts: dict) -> dict:
    """What the reviewer needs to decide, built in code from verified facts (no model call)."""
    sh = rec["get_shipping_tracking"]
    conflict_detail = {
        "delivered_to_different_address": f"carrier delivered_address_match = {sh.get('delivered_address_match')}",
        "merchant_acknowledged_nondelivery": "merchant's agent acknowledged non-delivery",
        "merchant_admitted_defect": "merchant's agent admitted a defect",
        "avs_cvv_failed_but_customer_history_matches": "AVS/CVV did not match, but the customer's history does",
        "dispute_amount_exceeds_unrefunded_balance": f"disputed ${d['amount']:,.2f} exceeds the unrefunded balance",
    }
    quote_for = {"merchant_acknowledged_nondelivery": "merchant_ack_nondelivery",
                 "merchant_admitted_defect": "merchant_admitted_defect"}
    conflicts = []
    for c in dec.conflicts:
        f = facts.get(quote_for.get(c, ""), {})
        conflicts.append(conflict_detail.get(c, c) + (f" ({f['message_id']}: \"{f['quote']}\")" if f.get("present") else ""))
    return {
        "why_escalated": dec.rationale,
        "missing_required_evidence": [f"{x['evidence_id']}: {x['basis']}" for x in dec.findings
                                      if x["evidence_id"] in dec.required_missing],
        "conflicts": conflicts,
        "evidence_on_file": [f"{x['evidence_id']}: {x['basis']}" for x in dec.findings if x["status"] == "present"],
        "amount": d["amount"], "hours_remaining": dec.hours_remaining,
        "p_win": dec.p_win, "expected_value": dec.expected_value,
        "warnings": admission_warnings(facts),
        "options": ["accept the dispute", "contest: call draft_letter() with your direction"],
    }


ADMISSIONS = {"merchant_ack_nondelivery": "acknowledged that the package was not delivered",
              "merchant_admitted_defect": "admitted the item was defective or not as described"}


def admission_warnings(facts: dict) -> list[str]:
    """Guardrail (2026-11-14): a contest letter would argue against the merchant's own statement. In the
    on-demand eval, these cases made up most failing letters; a reviewer should normally accept them."""
    return [f"The merchant's own agent {why} ({facts[k]['message_id']}: \"{facts[k]['quote']}\"). A contest letter "
            f"would argue against that statement; accepting is usually right."
            for k, why in ADMISSIONS.items() if (facts.get(k) or {}).get("present")]


def draft_letter(client, conn, dispute: dict, model: str, reviewer_direction: str,
                 override_admission: bool = False) -> dict:
    """On-demand letter for a brief-only escalation the reviewer decided to contest. If the merchant's own
    agent admitted the fault, no letter is drafted unless the reviewer explicitly overrides."""
    usage = Usage()
    trace = full_context(conn, dispute)
    rec = {t["tool"]: t["output"] for t in trace}
    d = rec["get_dispute_details"]
    candidates = sorted({r.category for r in rules_for(d["network"], d["reason_code"])})
    messages = rec["get_support_communications"]["messages"]
    read = _read(client, model, usage, d, candidates, messages)
    facts, _ = _verify(read.get("facts") or {}, messages)
    rule = lookup(d["network"], d["reason_code"], read["category"])
    dec = decide(rec, rule, facts)
    warnings = admission_warnings(facts)
    if warnings and not override_admission:
        return {"blocked": True, "warnings": warnings, "draft": None, "reviewer_notes": [], "trace": trace,
                "usage": usage.to_dict(), "decision": dec}
    w = _write(client, model, usage, _fact_sheet(d, rule, dec, facts), rec, reviewer_direction)
    return {"blocked": False, "warnings": warnings,
            "draft": {"narrative": w["narrative"], "evidence_list": w["evidence_list"]},
            "reviewer_notes": w["reviewer_notes"], "trace": trace, "usage": usage.to_dict(), "decision": dec}


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
    letter_status, brief = "drafted", None
    if brief_only(dec):
        letter_status = "brief_only"
        brief = _brief(d, rec, dec, facts)
        draft = {"narrative": "", "evidence_list": []}
    elif dec.action in ("fight", "escalate"):
        w = _write(client, model, usage, _fact_sheet(d, rule, dec, facts), rec)
        draft = {"narrative": w["narrative"], "evidence_list": w["evidence_list"]}
        notes += w["reviewer_notes"]
    else:
        letter_status = "accept_template"
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
                   "reader_skipped": bool(read.get("skipped")), "letter_status": letter_status, "brief": brief},
    }
    return {"output": output, "trace": trace, "tool_calls": [], "usage": usage.to_dict()}
