import pandas as pd
import streamlit as st

from data import outputs, per_case, scores

st.title("V0 baseline results")
st.caption("One Sonnet 5.5 call per dispute with every record in the prompt. 162 synthetic cases, run 9 November 2026.")

s = scores("v0")
if not s:
    st.warning("No scored results found in evals/results/v0.")
    st.stop()
d, ev, esc, fab, dq, cl = (s["decision"], s["evidence"], s["escalation"], s["fabrication"],
                           s["draft_quality"], s["cost_latency"])

c = st.columns(4)
c[0].metric("Decision accuracy", f"{d['accuracy']:.1%}")
c[1].metric("Wrongful auto-accepts", f"{d['wrongful_auto_accepts']}", f"${d['wrongful_auto_accept_usd']:,.0f}", delta_color="inverse", delta_arrow="off")
c[2].metric("Escalation precision / recall", f"{esc['precision']:.0%} / {esc['recall']:.0%}")
c[3].metric("Total run cost", f"${cl['total_usd']:.2f}", f"${cl['mean_usd_per_case']:.3f} per case", delta_color="off", delta_arrow="off")

st.subheader("Decisions: expected vs what V0 chose")
rows = []
for k, v in d["confusion_expected_x_predicted"].items():
    exp, pred = k.split("->")
    rows.append({"Correct answer": exp, "V0 chose": pred, "n": v})
cm = (pd.DataFrame(rows).pivot_table(index="Correct answer", columns="V0 chose", values="n", fill_value=0)
      .reindex(index=["fight", "escalate", "accept"], columns=["fight", "escalate", "accept"], fill_value=0)
      .astype(int))
left, right = st.columns([3, 2])
with left:
    st.dataframe(cm.style.background_gradient(cmap="Blues", axis=None), width="stretch")
    st.caption("Diagonal = correct. Read each row: of the 51 cases that should be fought, V0 fought 30 and escalated 20.")
with right:
    st.markdown("**Accuracy by dispute category**")
    bc = pd.DataFrame({"category": list(d["by_category"]), "accuracy": list(d["by_category"].values())})
    bc["category"] = bc["category"].str.replace("_", " ")
    st.bar_chart(bc, x="category", y="accuracy", horizontal=True, y_label="", x_label="decision accuracy")

st.subheader("What went wrong, and why it matters")
st.markdown(
    f"""
1. **Escalating winnable cases (20 of 51).** V0 has no rules table, so it treats optional evidence
   (signature or photo proof of delivery) as required, finds it "missing", and escalates. Its required-evidence
   list was exactly right in only **{ev['required_exact_rate']:.0%}** of cases. Cost: reviewer time on cases that needed none.
2. **Accepting cases that needed a person (13).** All 13 are disputes with conflicting records. Under the
   policy, conflicts go to a human; V0 accepted them instead, giving up money with no review. This is the
   error to drive down first.
3. **Letters: one data bug causes most failures.** The calibrated judge passes **{dq['pass_rate']:.0%}** of
   {dq['n_judged']} letters. 35 of the failures come from a single tool problem: customer history reports account age
   on the day the records were pulled, and the agent presents it as age at order time. Fixing the tool, not the
   prompt, is the first change for V1 (estimated pass rate about 92% once fixed).
"""
)

st.subheader("Evidence and letters")
c = st.columns(4)
c[0].metric("Required list exactly right", f"{ev['required_exact_rate']:.1%}")
c[1].metric("Real evidence marked missing", f"{ev['false_missing_rate']:.1%}")
c[2].metric("Evidence claimed but absent", f"{ev['false_present_rate']:.1%}")
c[3].metric("Letters passing judge", f"{dq['pass_rate']:.0%}",
            "calibrated" if dq.get("judge_calibrated") else "uncalibrated", delta_color="off", delta_arrow="off")
ms = dq["mean_scores"]
st.caption("Judge mean scores (1–5): " + " · ".join(f"{k.replace('_', ' ')} {v:.2f}" for k, v in ms.items()))

st.subheader("How the letter judge was calibrated")
st.markdown(
    """
An LLM judge (Opus 5.5) grades every letter. Before trusting it, I graded 40 letters blind myself, then settled
every disagreement with the judge's reasoning and the records side by side.

| Grader vs 40 settled labels | Agreement | Kappa | Bad letters passed | Good letters failed |
|---|---|---|---|---|
| My first-pass grades | 65% | 0.04 | 13 | 1 |
| Original judge: any unsupported claim fails | 70% | 0.42 | 2 | 10 |
| **Final judge: material errors only, plus a code check for concessions** | **87.5%** | **0.73** | **2** | **3** |

- **Unaided review misses contradictions.** Checking claims one at a time, I passed 13 letters that contradict the
  records or invent facts (for example an invented "pending internal review").
- **The original judge was too strict.** It failed letters over wording such as "accepted the return policy *at checkout*".
- **The fix was product rules, not prompt tweaks:** what counts as a material error (contradiction, invented fact,
  wrong number, conceding the dispute), written into the rubric, with clear-cut rules moved into code.
- **Stable:** two identical runs agreed on all 40 letters. The rubric is now frozen; fresh V1 letters graded blind are the next test.

Caveat: the rubric was refined on these same 40 letters, so 0.73 is optimistic.
"""
)
c = st.columns(3)
c[0].metric("Letters with a note to the reviewer", f"{s['letter']['with_reviewer_note']}", "allowed: every draft is reviewed",
            delta_color="off", delta_arrow="off")
c[1].metric("Letters conceding the dispute", f"{s['letter']['with_concession']}", "fails automatically",
            delta_color="off", delta_arrow="off")
c[2].metric("Account age at the wrong date", "35 letters", "fail on this alone", delta_color="off", delta_arrow="off")

st.subheader("Cost and speed")
pc, outs = per_case("v0"), outputs("v0")
lat = pd.DataFrame([{"case": k, "latency_s": v["usage"]["latency_s"], "cost_usd": v["usage"]["cost_usd"]}
                    for k, v in pc.items()])
c = st.columns(4)
c[0].metric("Typical latency", f"{cl['latency_p50_s']:.1f} s")
c[1].metric("95th percentile", f"{cl['latency_p95_s']:.1f} s")
c[2].metric("Avg output tokens", f"{cl['mean_output_tokens']:,}")
c[3].metric("Model served", ", ".join(cl["served_models"]))
st.scatter_chart(lat, x="latency_s", y="cost_usd", x_label="latency (s)", y_label="cost (USD)")
st.caption("Output tokens (including the model's reasoning) are about three quarters of the cost per case. "
           "Grading 115 letters with Opus costs about $4 per run, about the same as running the agent.")
