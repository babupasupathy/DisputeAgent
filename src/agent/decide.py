"""V1 decision layer: the merchant's written policy (docs/decisions.md, config/decision.toml) applied
in code to what the tools returned, plus four text facts the reader model extracted.

Inputs are only tool outputs (the same records V0 saw) and the reader's verified facts. This module
never reads the eval cases or the labeler; it is an independent implementation of the policy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.config import decision_config
from src.knowledge.rules import Rule

TEXT_FACTS = ("customer_ack_receipt", "merchant_offered_remedy", "merchant_ack_nondelivery", "merchant_admitted_defect")


def _dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Decision:
    category: str
    required_present: list[str]
    required_missing: list[str]
    strong_present: list[str]
    findings: list[dict]
    conflicts: list[str]
    merchant_fault: list[str]
    refunded_before_dispute: float
    credit_full: bool
    hours_remaining: float
    prior_disputes: int
    p_win: float
    expected_value: float
    cost_to_fight: float
    triggers: list[str]
    action: str
    rule_fired: str
    rationale: str
    evidence: dict[str, bool] = field(default_factory=dict)


def evidence(rec: dict, facts: dict[str, dict]) -> tuple[dict[str, bool], dict[str, str]]:
    """Every evidence item in data/rules/evidence_definitions.csv, with the record it rests on."""
    o, sh, hist = rec["get_order_details"], rec["get_shipping_tracking"], rec["get_customer_history"]
    rf = rec["get_refund_status"]
    shipped = sh.get("shipment", True) is not None and bool(sh.get("tracking_number"))
    delivered = shipped and sh.get("status") == "delivered"
    order_at = _dt(o["created_at"])
    priors = [p for p in hist["orders"] if p["order_id"] != o["order_id"] and _dt(p["created_at"]) < order_at
              and p["shipment_status"] == "delivered" and not p["disputed"]]
    in_window = [p for p in priors if timedelta(days=120) <= order_at - _dt(p["created_at"]) <= timedelta(days=365)]
    dev_ip = [p for p in priors if p["device_id"] == o["device_id"] and p["ip_token"] == o["ip_token"]]
    age = o["customer_account_age_days_at_order"]
    pay = o["payment"]
    items = o["items"]
    ev = {
        "carrier_tracking": shipped,
        "delivery_confirmation": delivered,
        "address_match": delivered and sh.get("delivered_address_match") is True,
        "proof_of_delivery": delivered and bool(sh.get("signature_on_file") or sh.get("photo_on_file")),
        "customer_ack_receipt": bool(facts.get("customer_ack_receipt", {}).get("present")),
        "avs_cvv_match": pay["avs_result"] == "Y" and pay["cvv_result"] == "M",
        "delivered_to_billing_address": delivered and o["shipping_matches_billing"],
        "prior_undisputed_orders": len(in_window) >= 2,
        "device_ip_match": bool(dev_ip),
        "established_account": age >= 180,
        "product_listing": bool(items) and all(i["listing_snapshot"] for i in items),
        "return_policy_accepted": o["return_policy_accepted"] is not None,
        "merchant_offered_remedy": bool(facts.get("merchant_offered_remedy", {}).get("present")),
        "no_return_attempted": len(rf["returns"]) == 0,
        "dispatch_photo": shipped and bool(sh.get("dispatch_photo_on_file")),
    }
    q = lambda k: (facts.get(k) or {}).get("quote") or ""
    mid = lambda k: (facts.get(k) or {}).get("message_id") or ""
    # Plain-language basis lines: the letter writer copies these, so no internal field names
    # (field names leaked into 26 of 112 V1 letters; owner graded it a format defect, 2026-11-14).
    yn = lambda b, yes, no: yes if b else no
    am = sh.get("delivered_address_match")
    basis = {
        "carrier_tracking": f"{sh.get('carrier')} tracking number {sh.get('tracking_number')}" if shipped else "no tracking number",
        "delivery_confirmation": f"the carrier recorded the package as delivered on {(sh.get('delivered_at') or '')[:10]}"
                                 if delivered else f"the carrier has not recorded a delivery (status: {sh.get('status')})",
        "address_match": {True: "the carrier confirmed delivery to the order's shipping address",
                          False: "the carrier reported delivery to a different address than the order's shipping address",
                          None: "the carrier did not confirm which address the package was delivered to"}[am],
        "proof_of_delivery": yn(sh.get("signature_on_file"), "the carrier has a recipient signature on file",
                                yn(sh.get("photo_on_file"), "the carrier has a delivery photo on file",
                                   "no signature or delivery photo is on file")),
        "customer_ack_receipt": f"in message {mid('customer_ack_receipt')} the customer wrote: \"{q('customer_ack_receipt')}\""
                                if ev["customer_ack_receipt"] else "no customer message acknowledging receipt",
        "avs_cvv_match": yn(ev["avs_cvv_match"], "the address check (AVS) and card security code check (CVV) both matched",
                            f"the address check (AVS) result was {pay['avs_result']} and the card security code check (CVV) "
                            f"result was {pay['cvv_result']}, so they did not both match"),
        "delivered_to_billing_address": yn(ev["delivered_to_billing_address"],
                                           "the order was shipped to the billing address and delivered",
                                           "the order was not delivered to the billing address"),
        "prior_undisputed_orders": f"{len(in_window)} earlier delivered, undisputed order(s) placed 120 to 365 days before this order"
                                   + (f": {', '.join(p['order_id'] for p in in_window)}" if in_window else ""),
        "device_ip_match": f"this order came from the same device and network (IP) as earlier undisputed order {dev_ip[0]['order_id']}"
                           if dev_ip else "no earlier undisputed order from the same device and network",
        "established_account": f"the customer's account was {age} days old when this order was placed",
        "product_listing": yn(ev["product_listing"], "an archived copy of the product listing is on file",
                              "no archived copy of the product listing is on file"),
        "return_policy_accepted": f"the customer accepted return policy {o['return_policy_accepted']}"
                                  if o["return_policy_accepted"] else "no accepted return policy is recorded",
        "merchant_offered_remedy": f"in message {mid('merchant_offered_remedy')} the merchant's agent wrote: \"{q('merchant_offered_remedy')}\""
                                   if ev["merchant_offered_remedy"] else "no offer of a return, refund or replacement in the support log",
        "no_return_attempted": "no return has been requested or received" if not rf["returns"]
                               else f"{len(rf['returns'])} return(s) on file",
        "dispatch_photo": yn(ev["dispatch_photo"], "a photo taken at dispatch is on file", "no dispatch photo is on file"),
    }
    return ev, basis


def decide(rec: dict, rule: Rule, facts: dict[str, dict]) -> Decision:
    cfg = decision_config()
    d, o, sh = rec["get_dispute_details"], rec["get_order_details"], rec["get_shipping_tracking"]
    hist, rf = rec["get_customer_history"], rec["get_refund_status"]
    category = rule.category
    ev, basis = evidence(rec, facts)
    req_present = [e for e in rule.required_evidence if ev[e]]
    req_missing = [e for e in rule.required_evidence if not ev[e]]
    strong_present = [e for e in rule.strong_evidence if ev[e]]
    findings = [{"evidence_id": e, "status": "present" if ev[e] else "missing", "basis": basis[e]}
                for e in (*rule.required_evidence, *rule.strong_evidence)]

    received = _dt(d["received_at"])
    refunded = round(sum(r["amount"] for r in rf["refunds"] if _dt(r["ts"]) < received), 2)
    credit_full = refunded >= o["total"] - 0.005
    unrefunded = round(o["total"] - refunded, 2)
    has = lambda k: bool((facts.get(k) or {}).get("present"))

    conflicts = []
    if category == "item_not_received":
        if ev["delivery_confirmation"] and sh.get("delivered_address_match") is False:
            conflicts.append("delivered_to_different_address")
        if ev["delivery_confirmation"] and has("merchant_ack_nondelivery"):
            conflicts.append("merchant_acknowledged_nondelivery")
    elif category == "fraud":
        if not ev["avs_cvv_match"] and (ev["device_ip_match"] or ev["prior_undisputed_orders"]):
            conflicts.append("avs_cvv_failed_but_customer_history_matches")
    elif category == "not_as_described" and has("merchant_admitted_defect"):
        conflicts.append("merchant_admitted_defect")
    if 0 < refunded and not credit_full and d["amount"] > unrefunded + 0.005:
        conflicts.append("dispute_amount_exceeds_unrefunded_balance")

    fault = []
    if category == "item_not_received" and sh.get("status") in ("lost", "returned_to_sender"):
        fault.append(f"shipment_{sh['status']}")
    if category == "not_as_described" and any(r["status"] == "received" for r in rf["returns"]) and refunded == 0:
        fault.append("return_received_without_refund")

    pc = cfg["p_win"]
    if credit_full:
        p = pc["credit_issued_p"]
    else:
        p = pc["base"][category] * pc["missing_penalty"] ** len(req_missing) + pc["strong_bonus"] * len(strong_present)
        if conflicts:
            p *= pc["conflict_multiplier"]
    p = round(min(pc["max_p"], max(pc["min_p"], p)), 4)
    cost = cfg["cost"]["representment_fee"] + cfg["cost"]["handling_cost"]
    ev_usd = round(p * d["amount"] - cost, 2)

    hours = rec["check_deadline"]["hours_remaining"]
    window_start = received - timedelta(days=365)
    prior = sum(1 for x in hist["disputes"] if x["dispute_id"] != d["dispute_id"]
                and window_start <= _dt(x["received_at"]) < received)

    esc = cfg["escalation"]
    triggers = []
    if d["amount"] >= esc["high_value_amount"]:
        triggers.append("high_value")
    if 0 < hours < esc["deadline_buffer_hours"]:
        triggers.append("deadline_near")
    if prior >= esc["repeat_disputer_min_prior"]:
        triggers.append("repeat_disputer")
    if not credit_full:
        if conflicts and esc["escalate_on_conflict"]:
            triggers.append("conflicting_evidence")
        if req_missing and esc["escalate_on_missing_required"]:
            triggers.append("missing_required_evidence")

    if hours <= 0:
        action, why = "accept", "deadline_passed"
    elif "high_value" in triggers:
        action, why = "escalate", "high_value"
    elif "repeat_disputer" in triggers:
        action, why = "escalate", "repeat_disputer"
    elif fault and not credit_full:
        action, why = "accept", "merchant_at_fault"
    elif ev_usd <= 0:
        action, why = "accept", "negative_expected_value"
    elif triggers:
        action, why = "escalate", triggers[0]
    else:
        action, why = "fight", "positive_expected_value"

    explain = {
        "deadline_passed": "The response deadline has passed (rule 1).",
        "high_value": f"The disputed amount ${d['amount']:,.2f} is at or above ${esc['high_value_amount']:,.0f} (rule 2).",
        "repeat_disputer": f"The customer has {prior} other disputes in the prior 365 days (rule 3).",
        "merchant_at_fault": f"The records show the merchant at fault: {', '.join(fault)} (rule 4).",
        "negative_expected_value": f"Expected value {p:.2f} x ${d['amount']:,.2f} - ${cost:.0f} = ${ev_usd:,.2f} is not positive (rule 5).",
        "deadline_near": f"Only {hours:.0f} hours remain, under the {esc['deadline_buffer_hours']}-hour buffer (rule 6).",
        "conflicting_evidence": f"The records conflict: {', '.join(conflicts)} (rule 6).",
        "missing_required_evidence": f"Required evidence is missing: {', '.join(req_missing)} (rule 6).",
        "positive_expected_value": f"Expected value {p:.2f} x ${d['amount']:,.2f} - ${cost:.0f} = ${ev_usd:,.2f} is positive and no escalation trigger applies (rule 7).",
    }[why]
    if why not in ("negative_expected_value", "positive_expected_value"):
        explain += f" Expected value: {p:.2f} x ${d['amount']:,.2f} - ${cost:.0f} = ${ev_usd:,.2f}."

    return Decision(category=category, required_present=req_present, required_missing=req_missing,
                    strong_present=strong_present, findings=findings, conflicts=conflicts, merchant_fault=fault,
                    refunded_before_dispute=refunded, credit_full=credit_full, hours_remaining=hours,
                    prior_disputes=prior, p_win=p, expected_value=ev_usd, cost_to_fight=cost, triggers=triggers,
                    action=action, rule_fired=why, rationale=explain, evidence=ev)
