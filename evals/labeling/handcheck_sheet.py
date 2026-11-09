"""Render a stratified sample of cases as a human-review sheet built from TOOL OUTPUTS only.

    python -m evals.labeling.handcheck_sheet --n 40 > docs/handcheck_sample.md
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from datetime import datetime

from src.backend import repository as repo
from src.backend.db import connect
from evals.paths import CASES_DIR


def _d(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def render(conn, c) -> str:
    d, L = c["dispute"], c["labels"]
    o = repo.get_order_details(conn, d["order_id"])
    s = repo.get_shipping_tracking(conn, d["order_id"])
    h = repo.get_customer_history(conn, o["customer_id"])
    m = repo.get_support_communications(conn, d["order_id"])
    r = repo.get_refund_status(conn, d["order_id"])
    k = repo.check_deadline(conn, d["dispute_id"])
    acct_age_at_order = (_d(o["created_at"]) - _d(h["account_created_at"])).days
    prior = [x for x in h["orders"] if x["created_at"] < o["created_at"]]
    win = [x for x in prior if not x["disputed"] and x["shipment_status"] == "delivered"
           and 120 <= (_d(o["created_at"]) - _d(x["created_at"])).days <= 365]
    dev = [x for x in prior if not x["disputed"] and x["device_id"] == o["device_id"]
           and x["ip_token"] == o["ip_token"]]
    other_disputes = [x for x in h["disputes"] if x["dispute_id"] != d["dispute_id"]]
    lines = [
        f"### {c['case_id']} - {L['category']} / {c['scenario']} ({c['scenario_note'] or '-'})",
        f"- Dispute {d['dispute_id']}: {d['network']} {d['reason_code']} (processor cat: {d['reason_category']}), "
        f"${d['amount']:.2f}; issuer msg: \"{d['issuer_message']}\"; {k['hours_remaining']} h left",
        f"- Order {o['order_id']} total ${o['total']:.2f}, AVS {o['payment']['avs_result']} / CVV {o['payment']['cvv_result']}, "
        f"ship==bill {o['shipping_matches_billing']}, policy {'yes' if o['return_policy_accepted'] else 'NO'}, "
        f"listing snapshot {'yes' if all(i['listing_snapshot'] for i in o['items']) else 'NO'}",
        f"- Shipment: {s.get('carrier')} {s.get('service')}, tracking {s.get('tracking_number') or 'NONE'}, status {s.get('status')}, "
        f"addr match {s.get('delivered_address_match')}, sig {s.get('signature_on_file')}, photo {s.get('photo_on_file')}, "
        f"dispatch photo {s.get('dispatch_photo_on_file')}; last event: "
        f"{(s['events'][-1]['detail'] if s.get('events') else '-')}",
        f"- Customer: account {acct_age_at_order} d old at order; prior orders {len(prior)}, "
        f"undisputed+delivered in 120-365d window {len(win)}, same device+IP {len(dev)}; other disputes {len(other_disputes)}",
        f"- Refunds: ${r['total_refunded']:.2f}; returns: {[x['status'] for x in r['returns']] or 'none'}",
        "- Messages:" + "".join(f"\n    - [{x['sender']}] {x['body']}" for x in m["messages"] if x["sender"] != "system"),
        f"- **Label**: present {L['required_present']} | missing {L['required_missing']} | strong {L['strong_present']} | "
        f"conflicts {L['conflicts'] or '-'} | fault {L['merchant_fault'] or '-'} | credit_full {L['credit_issued_full']} | "
        f"p={L['p_win']} EV=${L['expected_value']} | triggers {L['escalation_triggers'] or '-'} | "
        f"**{L['decision'].upper()}** ({L['decision_reason']})",
        "- Reviewer verdict: [ ] agree  [ ] disagree - note:",
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    cases = [json.loads(l) for l in open(CASES_DIR / "cases.jsonl")]
    by = defaultdict(list)
    for c in cases:
        by[(c["labels"]["category"], c["labels"]["decision"])].append(c)
    rng = random.Random(args.seed)
    sample, strata = [], sorted(by)
    while len(sample) < args.n:
        for st in strata:
            pool = [c for c in by[st] if c not in sample]
            if pool and len(sample) < args.n:
                sample.append(rng.choice(pool))
    sample.sort(key=lambda c: c["case_id"])
    conn = connect()
    print("# Hand-check sample (synthetic data)\n")
    print(f"{args.n} cases, stratified by category x decision (seed {args.seed}). Built from tool outputs only.\n")
    for c in sample:
        print(render(conn, c))


if __name__ == "__main__":
    main()
