"""Read/write functions behind the agent tools and the mock API.

Rules:
  * Outputs are masked: no full addresses, emails, raw IPs, or card data beyond brand + last4.
  * Generator-only metadata (tables prefixed `_gen_`) is never read here.
  * submit_response refuses without a human approval (v1 review gate).
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta

from src.backend.clock import now
from src.backend.generator import iso

PROCESSOR_FORM_FIELDS = {
    "product_not_received": ["shipping_carrier", "shipping_tracking_number", "shipping_date",
                             "shipping_address", "customer_communication", "rebuttal_text"],
    "fraudulent": ["customer_purchase_ip_token", "billing_address_check", "shipping_address",
                   "prior_undisputed_transactions", "customer_communication", "rebuttal_text"],
    "product_unacceptable": ["product_description", "refund_policy", "refund_refusal_explanation",
                             "customer_communication", "rebuttal_text"],
    "general": ["rebuttal_text", "customer_communication", "uncategorized_file"],
}


class NotFound(LookupError):
    pass


def _dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def mask_address(addr: str) -> str:
    # "1234 Maple St, Springfield, ST 01234" -> "**** Maple St, Springfield, ST 0****"
    addr = re.sub(r"^\d+", "****", addr)
    return re.sub(r"(\d)\d{4}$", r"\1****", addr)


def mask_email(email: str) -> str:
    user, _, domain = email.partition("@")
    return f"{user[:1]}***@{domain}"


def ip_token(ip: str) -> str:
    return "ip_" + hashlib.sha256(ip.encode()).hexdigest()[:10]


def _one(conn, sql, args, what):
    row = conn.execute(sql, args).fetchone()
    if row is None:
        raise NotFound(f"{what} not found")
    return row


def get_order_details(conn: sqlite3.Connection, order_id: str) -> dict:
    o = _one(conn, "SELECT * FROM orders WHERE order_id=?", (order_id,), f"order {order_id}")
    items = []
    for i in conn.execute(
            """SELECT i.*, p.title, s.title AS snap_title, s.description AS snap_desc, s.captured_at
               FROM order_items i JOIN products p USING(product_id)
               LEFT JOIN listing_snapshots s ON s.snapshot_id = i.listing_snapshot_id
               WHERE i.order_id=?""", (order_id,)):
        items.append({
            "product_id": i["product_id"], "title": i["title"], "qty": i["qty"], "unit_price": i["unit_price"],
            "listing_snapshot": ({"title": i["snap_title"], "description": i["snap_desc"],
                                  "captured_at": i["captured_at"]} if i["listing_snapshot_id"] else None),
        })
    return {
        "order_id": o["order_id"], "customer_id": o["customer_id"], "created_at": o["created_at"],
        "items": items, "subtotal": o["subtotal"], "shipping_fee": o["shipping_fee"], "total": o["total"],
        "currency": o["currency"],
        "billing_address": mask_address(o["billing_address"]),
        "shipping_address": mask_address(o["shipping_address"]),
        "shipping_matches_billing": o["billing_address"] == o["shipping_address"],
        "payment": {"card_brand": o["card_brand"], "card_last4": "****" + o["card_last4"],
                    "avs_result": o["avs_result"], "cvv_result": o["cvv_result"],
                    "avs_legend": "Y=match N=no match U=unavailable",
                    "cvv_legend": "M=match N=no match U=unavailable"},
        "ip_token": ip_token(o["ip_address"]), "device_id": o["device_id"],
        "return_policy_accepted": o["policy_version_accepted"],
    }


def get_shipping_tracking(conn: sqlite3.Connection, order_id: str) -> dict:
    s = conn.execute("SELECT * FROM shipments WHERE order_id=?", (order_id,)).fetchone()
    if s is None:
        return {"order_id": order_id, "shipment": None}
    events = [dict(ts=e["ts"], status=e["status"], location=e["location"], detail=e["detail"])
              for e in conn.execute("SELECT * FROM tracking_events WHERE shipment_id=? ORDER BY ts",
                                    (s["shipment_id"],))]
    am = s["delivered_address_match"]
    return {
        "order_id": order_id, "carrier": s["carrier"], "service": s["service"],
        "tracking_number": s["tracking_number"], "status": s["status"], "shipped_at": s["shipped_at"],
        "delivered_at": s["delivered_at"],
        "delivered_address_match": None if am is None else bool(am),
        "signature_on_file": bool(s["signature_on_file"]), "photo_on_file": bool(s["photo_on_file"]),
        "dispatch_photo_on_file": bool(s["dispatch_photo_on_file"]),
        "events": events,
    }


def get_customer_history(conn: sqlite3.Connection, customer_id: str) -> dict:
    c = _one(conn, "SELECT * FROM customers WHERE customer_id=?", (customer_id,), f"customer {customer_id}")
    t = now().replace(tzinfo=None)
    orders = []
    for o in conn.execute(
            """SELECT o.order_id, o.created_at, o.total, o.device_id, o.ip_address, s.status AS ship_status,
                      (SELECT COUNT(*) FROM disputes d WHERE d.order_id=o.order_id) AS n_disputes
               FROM orders o LEFT JOIN shipments s USING(order_id)
               WHERE o.customer_id=? ORDER BY o.created_at""", (customer_id,)):
        orders.append({"order_id": o["order_id"], "created_at": o["created_at"], "total": o["total"],
                       "shipment_status": o["ship_status"], "disputed": o["n_disputes"] > 0,
                       "device_id": o["device_id"], "ip_token": ip_token(o["ip_address"])})
    disputes = [dict(dispute_id=d["dispute_id"], order_id=d["order_id"], reason_code=d["reason_code"],
                     network=d["network"], received_at=d["received_at"], status=d["status"])
                for d in conn.execute("SELECT * FROM disputes WHERE customer_id=? ORDER BY received_at",
                                      (customer_id,))]
    return {
        "customer_id": customer_id, "email": mask_email(c["email"]), "account_created_at": c["created_at"],
        "account_age_days": (t - _dt(c["created_at"])).days,
        "orders": orders, "disputes": disputes,
    }


def get_support_communications(conn: sqlite3.Connection, order_id: str) -> dict:
    msgs = [dict(message_id=m["message_id"], ts=m["ts"], channel=m["channel"], sender=m["sender"], body=m["body"])
            for m in conn.execute("SELECT * FROM support_messages WHERE order_id=? ORDER BY ts", (order_id,))]
    return {"order_id": order_id, "messages": msgs}


def get_refund_status(conn: sqlite3.Connection, order_id: str) -> dict:
    refunds = [dict(refund_id=r["refund_id"], ts=r["ts"], amount=r["amount"], reason=r["reason"])
               for r in conn.execute("SELECT * FROM refunds WHERE order_id=? ORDER BY ts", (order_id,))]
    returns = [dict(return_id=r["return_id"], requested_at=r["requested_at"], status=r["status"],
                    received_at=r["received_at"])
               for r in conn.execute("SELECT * FROM returns WHERE order_id=? ORDER BY requested_at", (order_id,))]
    return {"order_id": order_id, "refunds": refunds,
            "total_refunded": round(sum(r["amount"] for r in refunds), 2), "returns": returns}


def get_dispute_details(conn: sqlite3.Connection, dispute_id: str) -> dict:
    d = _one(conn, "SELECT * FROM disputes WHERE dispute_id=?", (dispute_id,), f"dispute {dispute_id}")
    return {
        "dispute_id": d["dispute_id"], "order_id": d["order_id"], "network": d["network"],
        "reason_code": d["reason_code"], "reason_category": d["reason_category"], "amount": d["amount"],
        "currency": d["currency"], "received_at": d["received_at"], "response_due_at": d["response_due_at"],
        "issuer_message": d["issuer_message"], "status": d["status"],
        "response_form_fields": PROCESSOR_FORM_FIELDS[d["reason_category"]],
        "accepted_attachment_types": ["pdf", "png", "jpg"],
    }


def check_deadline(conn: sqlite3.Connection, dispute_id: str) -> dict:
    d = _one(conn, "SELECT response_due_at FROM disputes WHERE dispute_id=?", (dispute_id,),
             f"dispute {dispute_id}")
    secs = (_dt(d["response_due_at"]) - now().replace(tzinfo=None)).total_seconds()
    return {"dispute_id": dispute_id, "now": iso(now()), "response_due_at": d["response_due_at"],
            "hours_remaining": round(secs / 3600, 2), "days_remaining": round(secs / 86400, 2),
            "expired": secs <= 0}


def escalate_to_human(conn: sqlite3.Connection, dispute_id: str, summary: str, reason: str) -> dict:
    _one(conn, "SELECT 1 FROM disputes WHERE dispute_id=?", (dispute_id,), f"dispute {dispute_id}")
    cur = conn.execute("INSERT INTO escalations (dispute_id, summary, reason, created_at) VALUES (?,?,?,?)",
                       (dispute_id, summary, reason, iso(now())))
    conn.commit()
    return {"escalation_id": cur.lastrowid, "dispute_id": dispute_id, "status": "queued_for_review"}


class ApprovalRequired(PermissionError):
    pass


def submit_response(conn: sqlite3.Connection, dispute_id: str, payload: dict,
                    approved_by: str | None = None) -> dict:
    """Mock submission. v1: refuses unless a human reviewer approved it."""
    if not approved_by:
        raise ApprovalRequired("v1 policy: submissions require human reviewer approval")
    d = _one(conn, "SELECT * FROM disputes WHERE dispute_id=?", (dispute_id,), f"dispute {dispute_id}")
    if _dt(d["response_due_at"]) <= now().replace(tzinfo=None):
        raise PermissionError("response deadline has passed")
    cur = conn.execute("INSERT INTO submissions (dispute_id, payload, approved_by, created_at) VALUES (?,?,?,?)",
                       (dispute_id, json.dumps(payload, sort_keys=True), approved_by, iso(now())))
    conn.commit()
    return {"submission_id": cur.lastrowid, "dispute_id": dispute_id, "status": "submitted"}
