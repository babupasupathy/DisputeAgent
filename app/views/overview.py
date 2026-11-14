import streamlit as st

from data import scores

v0, fix, v1 = scores("v0"), scores("v0-agefix"), scores("v1")

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

st.subheader("From baseline to V1")
c = st.columns(5)
c[0].metric("Decision accuracy", f"{v1['decision']['accuracy']:.0%}", f"V0: {v0['decision']['accuracy']:.0%}",
            delta_color="off", delta_arrow="off")
c[1].metric("Wrongful auto-accepts", f"{v1['decision']['wrongful_auto_accepts']}",
            f"V0: {v0['decision']['wrongful_auto_accepts']} (${v0['decision']['wrongful_auto_accept_usd']:,.0f})",
            delta_color="off", delta_arrow="off")
c[2].metric("Letters ready to send", "96%", "V0: 62%", delta_color="off", delta_arrow="off",
            help="V1 letters drafted up front that pass the calibrated judge, after removing 5 verified judge "
                 "false failures (89.5% as judged). V0: 61.7% as judged.")
c[3].metric("Cost per case", f"${v1['cost_latency']['mean_usd_per_case']:.3f}",
            f"V0: ${v0['cost_latency']['mean_usd_per_case']:.3f}", delta_color="off", delta_arrow="off")
c[4].metric("Typical latency", f"{v1['cost_latency']['latency_p50_s']:.1f} s",
            f"V0: {v0['cost_latency']['latency_p50_s']:.1f} s", delta_color="off", delta_arrow="off")

st.markdown(
    """
**1. V0, the baseline.** One Claude Sonnet 5.5 call per dispute with every record pasted in. It classified every
dispute correctly but got 24% of decisions wrong: it escalated 20 winnable cases because it didn't know which evidence
each reason code requires, and accepted 13 conflicting cases with no human review.

**2. The evals pointed at the data, not the model.** A calibrated judge showed most failing letters stated the
customer's account age wrongly. The tool reported age *today*, and the agent presented it as age *at order time*.
Fixing the tool alone, same agent and prompt, raised the letter pass rate from 62% to 92%.

**3. V1 moved the decision to code.** Lookups, evidence checks, expected value and the escalation rules are
arithmetic, so code does them; the model only reads free text (with quotes that code verifies) and writes letters.
Escalations with conflicts or missing evidence get a reviewer brief instead of a letter. Decisions went to
100%, cost halved, and the model is not called at all for 16 cases.

**4. Humans in the loop kept the numbers honest.** Grading 60 letters blind and settling every disagreement
calibrated the judge, and found three data bugs that every automated check had missed.
"""
)

st.subheader("Product decisions made along the way")
st.markdown(
    "| Decision | Choice | Why |\n|---|---|---|\n"
    "| When to fight | Only when expected value is positive: P(win) × amount − $35 | Fighting costs a $15 fee plus ~20 min of analyst time |\n"
    "| Expected value before missing evidence | A low-value case is accepted, not escalated | Otherwise every weak case lands on a person |\n"
    "| Always a human | $750 and over; 2+ prior disputes; under 72 h left; conflicting records | Large or risky losses get human eyes |\n"
    "| Decisions in code (V1) | The model reads and writes; code applies the policy | V0's errors came from the model applying rules, not from missing data |\n"
    "| Brief now, letter later | Conflict / missing-evidence escalations get a brief; the letter is drafted only if a reviewer contests | Pre-written letters for these cases were the weakest; most should be accepted |\n"
    "| What fails a letter | Contradictions, invented facts, wrong numbers, concessions; not wording | Settled with the owner while calibrating the judge |\n"
    "| Never auto-submit (yet) | Every response passes a human review gate | Auto-submit must be earned by measured accuracy |"
)
st.caption("Details: **Results** for the numbers, **Case explorer** for every dispute, **LLM vs code** for the "
           "V1 design, **Roadmap** for what's next.")
