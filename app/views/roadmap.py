import streamlit as st

st.title("Roadmap")
st.caption("Each step states its prediction before it runs, so the results can prove it wrong.")

st.subheader("Done")
st.markdown(
    """
**Foundation**
- **Synthetic world.** A generated store (orders, shipping, support messages, refunds) and 162 labelled disputes:
  147 generated across 12 scenarios plus 15 hand-written edge cases.
- **Decision policy.** Expected-value-first rules with thresholds in config, signed off as product decisions.
- **Eval harness.** Exact-match scoring, a fact checker for letters, an Opus judge, and an answer-key self-test
  that scores 100%.

**V0 baseline: one model call does everything**
- 76% decision accuracy, 14 wrongful auto-accepts ($5,377), 62% of letters passing, $0.023 per case.
- **Letter judge calibrated** against 40 V0 letters graded blind by the owner (κ 0.42 → 0.73 vs settled labels).
- **Data fix measured on its own:** account age reported at order time instead of today took letters from 62% to
  92%, with the same agent and prompt.

**V1: code decides, the model reads and writes**
- 100% decisions, 0 wrongful auto-accepts, 99% of up-front letters passing, $0.012 per case, 2.4 s typical.
- **Brief now, letter later** for conflict and missing-evidence escalations, with an admission guardrail on
  letters drafted on demand (89.5% pass).
- **Judge re-checked blind on 20 fresh V1 letters:** no good letter failed; the 6 misses traced to a
  synthetic-data bug (delivery scan city), fixed at the source.
- **Reading step tested** on 30 messy, hand-written threads labelled by the owner: every field right on 29.
- **Haiku vs Sonnet for reading:** Haiku matched on every decision-driving field at 1/18 of the cost but missed
  more implied receipts; Sonnet stays, because one lost dispute ($200–500) outweighs ~$0.002 saved per dispute.

**Human in the loop**
- **Review queue:** reviewers work V1's cases by deadline, edit and approve letters, accept losses, or draft a
  letter on demand; every decision is recorded, so override rate and letter edits are measured.
"""
)

st.subheader("Next")
st.markdown(
    "| Step | What changes | Prediction to test |\n|---|---|---|\n"
    "| **V2: learn from outcomes** | P(win) fit on human-reviewed outcomes instead of fixed base rates | Better-calibrated P(win) changes fewer than 10% of decisions |\n"
    "| **Merchant-at-fault escalations as brief-only** | No up-front letter when the merchant received a return and never refunded (V1's one failing letter) | Up-front letters reach 100% with no change to decisions |\n"
    "| **Measure review time and overrides** | Reviewers use the queue on real cases | Review time under 2 minutes; override rate under 10% before any auto-submit |\n"
    "| **Auto-submit, maybe** | Low-risk fight cases skip review | Only if measured accuracy clears a bar set in advance |"
)

st.subheader("What success means")
st.markdown(
    "One headline number in dollars: **net recovered per 100 disputes**, meaning money won minus fight costs, "
    "minus reviewer time, minus wrongful auto-accepts. It is guarded by hard limits: wrongful auto-accepts under 2% "
    "of disputed dollars, no invented facts in letters, and an escalation rate the review team can handle. "
    "A version that adds complexity without moving these numbers is reported as such."
)

st.subheader("Open questions I own")
st.markdown(
    "- The rules table is built from secondary sources; every row needs checking against Visa, Mastercard and Amex documents.\n"
    "- The win-rate base rates are assumptions; a sensitivity analysis will show which ones change decisions.\n"
    "- The labels come from the same rules the decision code would use, so the honest test is on the text the model reads."
)
