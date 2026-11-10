import streamlit as st

from data import scores

s = scores("v0")
d, e, c = s.get("decision", {}), s.get("escalation", {}), s.get("cost_latency", {})

st.title("Dispute Agent")
st.markdown(
    "#### An AI agent that answers card chargebacks for an online store, built to be measured.\n"
    "It reads a dispute, gathers the order, shipping, support and refund records, decides whether "
    "to **fight, accept or escalate** to a person, and drafts the response letter for human review. "
    "The point of the project is the product work around the model: the decision policy, the eval "
    "suite, and the evidence for each design choice."
)

st.info("All data is synthetic: a generated store with 162 labelled disputes across Visa, "
        "Mastercard and Amex. No real card or customer data is used.", icon="ℹ️")

st.subheader("Where it started: the V0 baseline")
st.caption("One Claude Sonnet 5.5 call per dispute, every record pasted into the prompt, no rules table. "
           "Measured on all 162 cases.")
cols = st.columns(5)
cols[0].metric("Decision accuracy", f"{d.get('accuracy', 0):.0%}")
cols[1].metric("Reason code accuracy", f"{s.get('classification', {}).get('reason_code_accuracy', 0):.0%}")
cols[2].metric("Wrongful auto-accepts", f"{d.get('wrongful_auto_accepts', 0)}",
               f"${d.get('wrongful_auto_accept_usd', 0):,.0f} given up", delta_color="inverse", delta_arrow="off")
cols[3].metric("Escalation recall", f"{e.get('recall', 0):.0%}")
cols[4].metric("Cost per case", f"${c.get('mean_usd_per_case', 0):.3f}",
               f"{c.get('latency_p50_s', 0):.1f} s typical", delta_color="off", delta_arrow="off")

st.markdown(
    "**What V0 taught:** the model classifies disputes perfectly, but it doesn't know which evidence "
    "each reason code requires, so it escalated 20 winnable cases. The costly misses are the other "
    "way round: 13 cases with conflicting records were accepted with no human review."
)

st.subheader("Where it is going")
left, right = st.columns(2)
with left:
    st.markdown(
        "**Next: move the decision off the LLM.** Required evidence, evidence checks, win probability, "
        "expected value and the escalation rules are lookups and arithmetic, so code should do them. "
        "The model keeps the two jobs only it can do: reading free text and writing the letter. "
        "See **LLM vs code**."
    )
with right:
    st.markdown(
        "**Then: earn trust before automation.** A reviewer screen that records every override, "
        "a judge calibrated against human grades, and auto-submit only for low-risk cases once "
        "measured accuracy supports it. See **Roadmap**."
    )

st.subheader("Product decisions made so far")
st.markdown(
    "| Decision | Choice | Why |\n|---|---|---|\n"
    "| When to fight | Only when expected value is positive: P(win) × amount − $35 | Fighting costs a $15 fee plus ~20 min of analyst time |\n"
    "| Expected value before missing evidence | A low-value case is accepted, not escalated | Otherwise every weak case lands on a person |\n"
    "| Always a human | $750 and over; 2+ prior disputes; under 72 h left; conflicting records | Large or risky losses get human eyes |\n"
    "| Never auto-submit (yet) | Every response passes a human review gate | Auto-submit must be earned by measured accuracy |\n"
    "| Separate grader | Agent on Sonnet 5.5, letters graded by Opus 5.5 | A stronger model judges the weaker one |\n"
    "| Thresholds in config | `config/decision.toml`, not code | They are product calls to tune, not engineering details |"
)

st.subheader("How progress is measured")
st.markdown(
    "Every version runs on the same 162 cases and is scored on classification, evidence completeness, "
    "decision accuracy, **wrongful auto-accepts in dollars**, escalation precision and recall, invented "
    "facts in the letter, letter quality (LLM judge), cost and latency. The harness was validated "
    "first: an answer key read straight from the labels scores 100%, and deliberately broken answers fail."
)
