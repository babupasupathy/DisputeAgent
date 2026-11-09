"""Gather every backend record for a dispute (used by V0, which gets everything pasted in)."""
from __future__ import annotations

from src.backend import repository as repo


def full_context(conn, dispute: dict) -> list[dict]:
    """Return the same records the tools would return, as a trace of pseudo tool calls."""
    did, oid = dispute["dispute_id"], dispute["order_id"]
    order = repo.get_order_details(conn, oid)
    calls = [
        ("get_dispute_details", {"dispute_id": did}, repo.get_dispute_details(conn, did)),
        ("check_deadline", {"dispute_id": did}, repo.check_deadline(conn, did)),
        ("get_order_details", {"order_id": oid}, order),
        ("get_shipping_tracking", {"order_id": oid}, repo.get_shipping_tracking(conn, oid)),
        ("get_customer_history", {"customer_id": order["customer_id"]},
         repo.get_customer_history(conn, order["customer_id"])),
        ("get_support_communications", {"order_id": oid}, repo.get_support_communications(conn, oid)),
        ("get_refund_status", {"order_id": oid}, repo.get_refund_status(conn, oid)),
    ]
    return [{"tool": n, "input": i, "output": o} for n, i, o in calls]
