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
    "- **V0 baseline measured.** 76% decision accuracy, 14 wrongful auto-accepts ($5,377), $0.023 per case."
)

st.subheader("Next")
st.markdown(
    "| Step | What changes | Prediction to test |\n|---|---|---|\n"
    "| **V1: decision layer to code** | Rules table, evidence field checks, P(win), EV and the 7 rules run as code. The model reads text and writes the letter. | Winnable cases escalated drop from 20 to under 5; wrongful auto-accepts from 14 to under 3; cost per case roughly halves |\n"
    "| **Text-reading labels** | Hand-written, messy support messages with human labels for the text-based evidence | Becomes the real test once decisions are code; target 95% agreement |\n"
    "| **Smaller model for reading** | Haiku 5.5 reads issuer notes and support messages | Keeps accuracy within 2 points of Sonnet at a fraction of the cost |\n"
    "| **Judge calibration** | 40 letters graded by hand, compared to the Opus judge | Agreement (Cohen's kappa) above 0.6 before judge scores are trusted |\n"
    "| **V2: learn from outcomes** | P(win) fit on human-reviewed outcomes; reviewed past cases retrieved as examples | Better-calibrated P(win) changes fewer than 10% of decisions |\n"
    "| **V3: critic step** | A second pass checks each letter against the reason code's requirements before review | Judge pass rate up; kept only if the gain is measurable |\n"
    "| **Reviewer screen** | Shows why a case was escalated, what is missing and a ready letter; records every override | Review time under 2 minutes; override rate becomes a headline metric |\n"
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
