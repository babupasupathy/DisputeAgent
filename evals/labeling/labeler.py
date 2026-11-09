"""Rule-based ground-truth labeler.

Labels are derived from the stored backend records + the rules table + config/decision.toml.
No model judgment is involved. The only input that is not re-derivable from the DB is the
true dispute category (for Mastercard 4853 the category lives only in the issuer message
text), which the generator supplies.

This module is eval-side code. The agent must never import it.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from src.config import decision_config
from src.knowledge.rules import lookup

ALL_TOOLS = [
    "get_order_details", "get_shipping_tracking", "get_customer_history",
    "get_support_communications", "get_refund_status", "get_dispute_details", "check_deadline",
]
REQUIRED_TOOLS = {
    "item_not_received": ["get_dispute_details", "check_deadline", "get_order_details",
                          "get_shipping_tracking", "get_support_communications", "get_refund_status"],
    "fraud": ["get_dispute_details", "check_deadline", "get_order_details", "get_shipping_tracking",
              "get_customer_history", "get_refund_status"],
    "not_as_described": ["get_dispute_details", "check_deadline", "get_order_details",
                         "get_support_communications", "get_refund_status"],
}
# Tools that add nothing for the category. get_shipping_tracking is allowed (not penalized)
# for not_as_described because dispatch photos live on the shipment record.
OPTIONAL_TOOLS = {"not_as_described": ["get_shipping_tracking"]}


def _dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def _tags(conn: sqlite3.Connection, order_id: str) -> set[str]:
    rows = conn.execute(
        "SELECT l.tag FROM _gen_message_labels l JOIN support_messages m USING(message_id) WHERE m.order_id=?",
        (order_id,)).fetchall()
    return {r["tag"] for r in rows}


def derive_evidence(conn: sqlite3.Connection, order_id: str) -> dict[str, bool]:
    """Evaluate every evidence item defined in data/rules/evidence_definitions.csv."""
    o = conn.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
    sh = conn.execute("SELECT * FROM shipments WHERE order_id=?", (order_id,)).fetchone()
    items = conn.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,)).fetchall()
    cust = conn.execute("SELECT * FROM customers WHERE customer_id=?", (o["customer_id"],)).fetchone()
    tags = _tags(conn, order_id)
    order_at = _dt(o["created_at"])

    delivered = sh is not None and sh["status"] == "delivered" and sh["tracking_number"] is not None
    # prior undisputed delivered orders
    priors = conn.execute(
        """SELECT o.* FROM orders o JOIN shipments s USING(order_id)
           WHERE o.customer_id=? AND o.created_at < ? AND s.status='delivered'
             AND o.order_id NOT IN (SELECT order_id FROM disputes)""",
        (o["customer_id"], o["created_at"])).fetchall()
    in_window = [p for p in priors
                 if timedelta(days=120) <= order_at - _dt(p["created_at"]) <= timedelta(days=365)]
    device_ip = any(p["device_id"] == o["device_id"] and p["ip_address"] == o["ip_address"] for p in priors)
    returns = conn.execute("SELECT * FROM returns WHERE order_id=?", (order_id,)).fetchall()

    return {
        "carrier_tracking": sh is not None and sh["tracking_number"] is not None,
        "delivery_confirmation": delivered,
        "address_match": delivered and sh["delivered_address_match"] == 1,
        "proof_of_delivery": delivered and bool(sh["signature_on_file"] or sh["photo_on_file"]),
        "customer_ack_receipt": "customer_ack_receipt" in tags,
        "avs_cvv_match": o["avs_result"] == "Y" and o["cvv_result"] == "M",
        "delivered_to_billing_address": delivered and o["billing_address"] == o["shipping_address"],
        "prior_undisputed_orders": len(in_window) >= 2,
        "device_ip_match": device_ip,
        "established_account": (order_at - _dt(cust["created_at"])) >= timedelta(days=180),
        "product_listing": bool(items) and all(i["listing_snapshot_id"] for i in items),
        "return_policy_accepted": o["policy_version_accepted"] is not None,
        "merchant_offered_remedy": "merchant_offered_remedy" in tags,
        "no_return_attempted": len(returns) == 0,
        "dispatch_photo": sh is not None and bool(sh["dispatch_photo_on_file"]),
    }


def label_dispute(conn: sqlite3.Connection, dispute_id: str, category: str, as_of: datetime) -> dict:
    cfg = decision_config()
    d = conn.execute("SELECT * FROM disputes WHERE dispute_id=?", (dispute_id,)).fetchone()
    o = conn.execute("SELECT * FROM orders WHERE order_id=?", (d["order_id"],)).fetchone()
    sh = conn.execute("SELECT * FROM shipments WHERE order_id=?", (d["order_id"],)).fetchone()
    rule = lookup(d["network"], d["reason_code"], category)
    ev = derive_evidence(conn, d["order_id"])
    tags = _tags(conn, d["order_id"])

    required_present = [e for e in rule.required_evidence if ev[e]]
    required_missing = [e for e in rule.required_evidence if not ev[e]]
    strong_present = [e for e in rule.strong_evidence if ev[e]]
    strong_missing = [e for e in rule.strong_evidence if not ev[e]]

    refunds = conn.execute("SELECT * FROM refunds WHERE order_id=? AND ts < ?",
                           (d["order_id"], d["received_at"])).fetchall()
    refunded = round(sum(r["amount"] for r in refunds), 2)
    unrefunded = round(o["total"] - refunded, 2)
    credit_full = refunded >= o["total"] - 0.005

    # conflicts: explicit, rule-detectable contradictions between records
    conflicts = []
    if category == "item_not_received":
        if ev["delivery_confirmation"] and sh["delivered_address_match"] == 0:
            conflicts.append("delivered_to_different_address")
        if ev["delivery_confirmation"] and "merchant_ack_nondelivery" in tags:
            conflicts.append("merchant_acknowledged_nondelivery")
    elif category == "fraud":
        if not ev["avs_cvv_match"] and (ev["device_ip_match"] or ev["prior_undisputed_orders"]):
            conflicts.append("avs_cvv_failed_but_customer_history_matches")
    elif category == "not_as_described":
        if "merchant_admitted_defect" in tags:
            conflicts.append("merchant_admitted_defect")
    if 0 < refunded and not credit_full and d["amount"] > unrefunded + 0.005:
        conflicts.append("dispute_amount_exceeds_unrefunded_balance")

    # merchant at fault: records affirmatively support the cardholder
    merchant_fault = []
    if category == "item_not_received" and sh is not None and sh["status"] in ("lost", "returned_to_sender"):
        merchant_fault.append(f"shipment_{sh['status']}")
    if category == "not_as_described":
        received_returns = conn.execute(
            "SELECT 1 FROM returns WHERE order_id=? AND status='received'", (d["order_id"],)).fetchone()
        if received_returns and refunded == 0:
            merchant_fault.append("return_received_without_refund")

    # P(win)
    pc = cfg["p_win"]
    if credit_full:
        p = pc["credit_issued_p"]
    else:
        p = pc["base"][category] * pc["missing_penalty"] ** len(required_missing)
        p += pc["strong_bonus"] * len(strong_present)
        if conflicts:
            p *= pc["conflict_multiplier"]
    p = round(min(pc["max_p"], max(pc["min_p"], p)), 4)
    cost = cfg["cost"]["representment_fee"] + cfg["cost"]["handling_cost"]
    ev_usd = round(p * d["amount"] - cost, 2)

    hours_remaining = round((_dt(d["response_due_at"]) - as_of.replace(tzinfo=None)).total_seconds() / 3600, 2)
    prior_disputes = conn.execute(
        "SELECT COUNT(*) c FROM disputes WHERE customer_id=? AND dispute_id<>? AND received_at < ? AND received_at >= ?",
        (d["customer_id"], dispute_id, d["received_at"],
         (_dt(d["received_at"]) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ"))).fetchone()["c"]

    esc = cfg["escalation"]
    triggers = []
    if d["amount"] >= esc["high_value_amount"]:
        triggers.append("high_value")
    if 0 < hours_remaining < esc["deadline_buffer_hours"]:
        triggers.append("deadline_near")
    if prior_disputes >= esc["repeat_disputer_min_prior"]:
        triggers.append("repeat_disputer")
    if not credit_full:
        if conflicts and esc["escalate_on_conflict"]:
            triggers.append("conflicting_evidence")
        if required_missing and esc["escalate_on_missing_required"]:
            triggers.append("missing_required_evidence")

    # Decision precedence (documented in docs/decisions.md)
    if hours_remaining <= 0:
        decision, why = "accept", "deadline_passed"
    elif "high_value" in triggers:
        decision, why = "escalate", "high_value"
    elif merchant_fault and not credit_full:
        decision, why = "accept", "merchant_at_fault"
    elif ev_usd <= 0:
        decision, why = "accept", "negative_expected_value"
    elif triggers:
        decision, why = "escalate", triggers[0]
    else:
        decision, why = "fight", "positive_expected_value"

    used_tools = REQUIRED_TOOLS[category]
    unneeded = [t for t in ALL_TOOLS if t not in used_tools and t not in OPTIONAL_TOOLS.get(category, [])]

    return {
        "network": d["network"],
        "reason_code": d["reason_code"],
        "category": category,
        "required_evidence": list(rule.required_evidence),
        "strong_evidence": list(rule.strong_evidence),
        "required_present": required_present,
        "required_missing": required_missing,
        "strong_present": strong_present,
        "strong_missing": strong_missing,
        "conflicts": conflicts,
        "merchant_fault": merchant_fault,
        "refunded_before_dispute": refunded,
        "credit_issued_full": credit_full,
        "prior_disputes_365d": prior_disputes,
        "hours_remaining": hours_remaining,
        "p_win": p,
        "cost_to_fight": cost,
        "expected_value": ev_usd,
        "escalation_triggers": triggers,
        "decision": decision,
        "decision_reason": why,
        "expected_escalation": decision == "escalate",
        "required_tools": used_tools,
        "unneeded_tools": unneeded,
    }
