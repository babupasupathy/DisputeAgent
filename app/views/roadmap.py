import streamlit as st

st.title("Roadmap")
st.caption("Each step states its prediction before it runs, so the results can prove it wrong.")

st.subheader("Done")
st.markdown(
    "- **Synthetic world.** A generated store (orders, shipping, support messages, refunds) and 162 labelled "
    "disputes: 147 generated across 12 scenarios plus 15 hand-written edge cases.\n"
    "- **Decision policy.** Expected-value-first rules with thresholds in config, signed off as product decisions.\n"
    "- **Eval harness.** Ten scoring dimensions, a fact checker for letters, an Opus judge, and an answer-key "
    "self-test that scores 100%.\n"
    "- **V0 baseline measured.** 76% decision accuracy, 14 wrongful auto-accepts ($5,377), $0.023 per case.\n"
    "- **Letter judge calibrated** against 40 human-graded letters (kappa 0.73 vs settled labels).\n"
    "- **Data fix measured on its own.** Account age reported at order time instead of today: letter pass rate "
    "61.7% → 91.5%, account-age failures 38 → 0, decisions unchanged. Same agent, same prompt."
)

st.markdown(
    "- **V1 built and measured.** Decisions in code, the model reads text and writes letters, brief now letter later: "
    "decisions 100%, 0 wrongful auto-accepts, cost −52%, letters drafted up front 96% after verified judge corrections.\n"
    "- **Judge checked blind on 20 fresh V1 letters:** 14/20 agree, no good letter failed; all 6 misses traced to a "
    "synthetic-data bug (delivery scan city), fixed at the source."
)

st.subheader("Next")
st.markdown(
    "| Step | What changes | Prediction to test |\n|---|---|---|\n"
    "| **Messy messages for the reader** | Hand-written, realistic support messages (typos, sarcasm, reversals) labelled by the owner | The reader keeps ≥ 95% agreement on the four text facts; decisions are only as good as this step now |\n"
    "| **Admission guardrail** | Before drafting an on-demand letter, warn when the merchant's own agent admitted the fault | Blocks most of the on-demand letters that fail today |\n"
    "| **Smaller model for reading** | Haiku 5.5 reads issuer notes and support messages | Keeps reading accuracy within 2 points of Sonnet at a fraction of the cost |\n"
    "| **V2: learn from outcomes** | P(win) fit on human-reviewed outcomes | Better-calibrated P(win) changes fewer than 10% of decisions |\n"
    "| **Reviewer screen** | Shows the brief, a ready letter, and records every override | Review time under 2 minutes; override rate becomes a headline metric |\n"
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
