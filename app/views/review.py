"""Reviewer screen: the human gate between V1 and the card issuer.

A reviewer works the queue of cases V1 proposes to fight or escalates, reads the brief or the drafted letter,
edits it, and approves, accepts the loss, or escalates further. Every decision is recorded (src/review_ui/store.py),
so the override rate and the letter edit rate are measured. Brief-only escalations get a letter only when the
reviewer decides to contest (draft_letter, with the admission guardrail).
"""
import os

import pandas as pd
import streamlit as st

from data import ROOT, action_label, cases, outputs
from src.review_ui.store import ACTIONS, CONTESTS, Review, ReviewStore

STORE = ReviewStore(ROOT / "data" / "reviews" / "reviews.jsonl")
VERSION = "v1"

st.title("Review queue")
st.caption("Every response passes a person before it reaches the issuer. Decisions here are recorded so the "
           "override rate and how much reviewers edit letters are measured, not guessed. On the hosted demo, "
           "decisions last until the app restarts; run the app locally to keep them.")

C, O = cases(), outputs(VERSION)
reviews = STORE.latest()

m = STORE.metrics()
c = st.columns(4)
c[0].metric("Reviewed", f"{m.get('reviewed', 0)}")
c[1].metric("Override rate", f"{m['override_rate']:.0%}" if m.get("reviewed") else "–",
            help="Share of reviewed cases where the reviewer reversed the agent (a proposed fight accepted, or a "
                 "proposed accept contested). Resolving an escalation either way is not an override.")
c[2].metric("Letters edited", f"{m['letter_edit_rate']:.0%}" if m.get("letter_edit_rate") is not None else "–",
            help="Share of sent letters the reviewer changed by more than 2%.")
c[3].metric("Guardrail overrides", f"{m.get('guardrail_overrides', 0)}",
            help="Letters drafted although the merchant's own agent had admitted the fault.")

rows = []
for cid, r in O.items():
    out = (r or {}).get("output") or {}
    act = (out.get("decision") or {}).get("action")
    if act not in ("fight", "escalate"):
        continue
    rv, d = out.get("review") or {}, C[cid]["dispute"]
    rows.append({"case": cid, "order": d["order_id"], "amount": d["amount"], "agent proposes": act,
                 "why": rv.get("rule_fired", "").replace("_", " "),
                 "hours left": (out.get("assessment") or {}).get("hours_remaining"),
                 "letter": {"drafted": "ready", "brief_only": "brief only"}.get(rv.get("letter_status"), rv.get("letter_status")),
                 "reviewed": reviews.get(cid, {}).get("reviewer_action", "").replace("_", " ")})
if not rows:
    st.info("No V1 results to review yet.")
    st.stop()
q = pd.DataFrame(rows).sort_values("hours left")

f1, f2 = st.columns(2)
show = f1.selectbox("Show", ["Needs a decision", "Reviewed", "All"])
kind = f2.multiselect("Agent proposes", ["fight", "escalate"])
view = q
if show == "Needs a decision":
    view = view[view["reviewed"] == ""]
elif show == "Reviewed":
    view = view[view["reviewed"] != ""]
if kind:
    view = view[view["agent proposes"].isin(kind)]
st.dataframe(view, hide_index=True, width="stretch", height=260,
             column_config={"amount": st.column_config.NumberColumn(format="$%.2f"),
                            "hours left": st.column_config.NumberColumn(format="%d h")})
st.caption(f"{len(view)} of {len(q)} cases · most urgent deadline first")
if view.empty:
    st.success("Nothing left in this view.")
    st.stop()

cid = st.selectbox("Open a case", view["case"].tolist())
case, out = C[cid], O[cid]["output"]
d, dec, rv, a = case["dispute"], out["decision"], out.get("review") or {}, out.get("assessment") or {}

st.divider()
st.subheader(f"{d['order_id']} · {d['network'].title()} {d['reason_code']} · ${d['amount']:,.2f}")
st.markdown(f"> **Issuer's note:** {d.get('issuer_message') or '(empty)'}")
k = st.columns(4)
k[0].metric("Agent proposes", action_label(dec["action"]))
k[1].metric("Hours to deadline", f"{a.get('hours_remaining', 0):.0f}")
k[2].metric("P(win)", f"{a.get('p_win', 0):.2f}")
k[3].metric("Expected value", f"${a.get('expected_value', 0):,.2f}")
st.write(dec.get("rationale", ""))

brief = rv.get("brief") or {}
facts = rv.get("text_facts") or {}
adm = {"merchant_ack_nondelivery": "acknowledged that the package was not delivered",
       "merchant_admitted_defect": "admitted the item was defective or not as described"}
warnings = brief.get("warnings") or [f"The merchant's own agent {why} ({f['message_id']}: \"{f['quote']}\")."
                                     for key, why in adm.items() if (f := facts.get(key) or {}).get("present")]
for w in warnings:
    st.warning("Guardrail: " + w + " A contest letter would argue against that statement; accepting is usually right.")
for n in brief.get("signals") or []:
    st.info(n)

ev = pd.DataFrame(out["evidence"]["findings"])
if not ev.empty:
    with st.expander("Evidence on file and missing", expanded=bool(brief)):
        st.dataframe(ev.rename(columns={"evidence_id": "evidence", "basis": "what the records show"}),
                     hide_index=True, width="stretch")
if rv.get("reviewer_notes"):
    with st.expander("Notes from the agent"):
        for n in rv["reviewer_notes"]:
            st.markdown(f"- {n}")

# ---- the letter: drafted up front, or drafted on demand for a brief-only case
key = f"letter_{cid}"
if key not in st.session_state:
    st.session_state[key] = out["draft"].get("narrative") or ""
letter_status = rv.get("letter_status", "drafted")

if letter_status == "brief_only" and not st.session_state[key]:
    st.markdown("##### No letter yet")
    st.write("This escalation got a brief instead of a letter. Accept the loss, or draft a letter if you decide to contest.")
    override = st.checkbox("Draft even though the merchant admitted the fault", key=f"ovr_{cid}") if warnings else False
    can_draft = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("DISPUTE_AGENT_ANTHROPIC_KEY")) \
        and (ROOT / "data" / "synthetic" / "store.db").exists()
    if st.button("Draft letter", disabled=bool(warnings and not override) or not can_draft, key=f"draft_{cid}"):
        with st.spinner("Drafting from the verified facts…"):
            from src.agent.llm import make_client
            from src.agent.v1 import draft_letter
            from src.backend.db import connect
            res = draft_letter(make_client(), connect(), d, os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
                               st.session_state.get(f"dir_{cid}") or "Contest this dispute with the strongest honest case.",
                               override_admission=override)
        if res.get("blocked"):
            st.error("Not drafted: " + " ".join(res["warnings"]))
        else:
            st.session_state[key] = res["draft"]["narrative"]
            st.session_state[f"ondemand_{cid}"] = True
            st.rerun()
    st.text_input("Your direction for the letter (optional)", key=f"dir_{cid}",
                  placeholder="e.g. lead with the customer's receipt email; leave out the address question")
    if not can_draft:
        st.caption("Drafting on demand calls the model, so it works when you run the app locally with an API key and "
                   "the store database. On the hosted demo it is switched off.")
        sim = outputs("v1-ondemand").get(cid)
        if sim and (sim.get("output") or {}).get("draft"):
            with st.expander("Example: the letter the eval drafted when a simulated reviewer contested this case"):
                st.markdown(sim["output"]["draft"]["narrative"])

if st.session_state[key]:
    st.markdown("##### Letter to the issuer")
    st.text_area("Edit before approving", key=key, height=320, label_visibility="collapsed")
    if out["draft"].get("evidence_list"):
        st.caption("Exhibits: " + "; ".join(f"{e['item']} ({e['source']})" for e in out["draft"]["evidence_list"]))

note = st.text_input("Reviewer note (optional)", key=f"note_{cid}")
b = st.columns(3)
letter_now, letter_orig = st.session_state[key], (out["draft"].get("narrative") or "")


def save(action: str):
    STORE.add(Review(case_id=cid, version=VERSION, agent_action=dec["action"],
                     letter_status="on_demand" if st.session_state.get(f"ondemand_{cid}") else letter_status,
                     reviewer_action=action, letter_before=letter_orig or (letter_now if action in CONTESTS else ""),
                     letter_after=letter_now if action in CONTESTS else "", note=note,
                     guardrail_override=bool(warnings and action in CONTESTS)))
    st.toast(f"Saved: {ACTIONS[action]}")
    st.rerun()


if b[0].button("Approve and contest", type="primary", disabled=not letter_now.strip(), key=f"ok_{cid}"):
    save("edit_and_approve" if letter_orig and letter_now.strip() != letter_orig.strip() else "approve")
if b[1].button("Accept the loss", key=f"acc_{cid}"):
    save("accept_loss")
if b[2].button("Escalate to senior reviewer", key=f"esc_{cid}"):
    save("escalate")
if cid in reviews:
    st.caption(f"Last decision: {reviews[cid]['reviewer_action'].replace('_', ' ')} at {reviews[cid]['ts']}")
