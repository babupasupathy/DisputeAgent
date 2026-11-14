import pandas as pd
import streamlit as st

from data import per_case, scores

st.title("Results")
st.caption("Every version runs on the same 162 synthetic disputes and is scored the same way. "
           "Letters are graded by a calibrated Opus 5.5 judge.")

VERSIONS = {"V0 baseline": "v0", "V0 + account-age fix": "v0-agefix", "V1": "v1"}
S = {k: scores(v) for k, v in VERSIONS.items()}


def row(name, f):
    return {"": name, **{k: f(s) for k, s in S.items()}}


tbl = pd.DataFrame([
    row("Decision accuracy", lambda s: f"{s['decision']['accuracy']:.1%}"),
    row("Wrongful auto-accepts", lambda s: f"{s['decision']['wrongful_auto_accepts']} (${s['decision']['wrongful_auto_accept_usd']:,.0f})"),
    row("Winnable cases escalated", lambda s: str(s['decision']['confusion_expected_x_predicted'].get('fight->escalate', 0))),
    row("Escalation precision / recall", lambda s: f"{s['escalation']['precision']:.0%} / {s['escalation']['recall']:.0%}"),
    row("Required evidence exactly right", lambda s: f"{s['evidence']['required_exact_rate']:.1%}"),
    row("Letters passing the judge", lambda s: f"{s['draft_quality']['pass_rate']:.1%} of {s['draft_quality']['n_judged']}"),
    row("Letters flagged by the fact checker", lambda s: str(s['fabrication']['drafts_with_unsupported_tokens'])),
    row("Letters with internal field names", lambda s: str(s['letter'].get('with_field_names', '–'))),
    row("Cost per case", lambda s: f"${s['cost_latency']['mean_usd_per_case']:.4f}"),
    row("Latency p50 / p95", lambda s: f"{s['cost_latency']['latency_p50_s']:.1f} / {s['cost_latency']['latency_p95_s']:.1f} s"),
])
st.dataframe(tbl, hide_index=True, width="stretch")
st.caption("V1 letters: 76 drafted up front pass 89.5% as judged; 5 of the 8 failures are verified judge false "
           "failures on a true sentence ('placed 120 to 365 days before this order'), so 96.1% after correction. "
           "50 conflict / missing-evidence escalations get a reviewer brief instead of a letter. "
           "Field names were only counted from V1 on (–).")

st.subheader("What each step fixed")
st.markdown(
    """
| Step | Change | Effect |
|---|---|---|
| **V0** | One model call, every record pasted in | 76% decisions; 20 winnable cases escalated; 14 wrongful auto-accepts ($5,377) |
| **Account-age fix** | The tool reports age at order time instead of today; same agent, same prompt | Letters 62% → 92%; account-age failures 38 → 0; decisions unchanged |
| **V1** | Decisions in code; the model reads text and writes letters; brief now, letter later | Decisions 100%; 0 wrongful auto-accepts; cost −52%; p50 latency 10.6 s → 2.6 s |
"""
)

st.subheader("Decisions: correct answer vs what each version chose")
pick = st.radio("Version", list(VERSIONS), horizontal=True, index=0)
d = S[pick]["decision"]
rows = [{"Correct answer": k.split("->")[0], "Chose": k.split("->")[1], "n": v}
        for k, v in d["confusion_expected_x_predicted"].items()]
cm = (pd.DataFrame(rows).pivot_table(index="Correct answer", columns="Chose", values="n", fill_value=0)
      .reindex(index=["fight", "escalate", "accept"], columns=["fight", "escalate", "accept"], fill_value=0).astype(int))
left, right = st.columns([3, 2])
with left:
    st.dataframe(cm.style.background_gradient(cmap="Blues", axis=None), width="stretch")
    st.caption("Diagonal = correct.")
with right:
    bc = pd.DataFrame({"category": [k.replace("_", " ") for k in d["by_category"]],
                       "accuracy": list(d["by_category"].values())})
    st.bar_chart(bc, x="category", y="accuracy", horizontal=True, y_label="", x_label="decision accuracy")

st.subheader("How the letter judge was calibrated")
st.markdown(
    """
An LLM judge grades every letter. Before trusting it, the project owner graded letters blind, then settled every
disagreement with the judge's reasoning and the records side by side.

**Round 1: 40 V0 letters.**

| Grader vs 40 settled labels | Agreement | Kappa | Bad letters passed | Good letters failed |
|---|---|---|---|---|
| Owner, first pass | 65% | 0.04 | 13 | 1 |
| Original judge: any unsupported claim fails | 70% | 0.42 | 2 | 10 |
| **Final judge: material errors only, plus a code check for concessions** | **87.5%** | **0.73** | **2** | **3** |

**Round 2: 20 fresh V1 letters the rubric was never tuned on.** Agreement 14 of 20; the judge failed no good letter.
All 6 misses had one cause: letters claimed delivery to the order's address while the delivery scan was in another
city. The judge trusted the carrier's match flag and never checked it against the scan location.

**What human grading found that no automated check did:**
- **Account age** measured on the wrong date (fixed in the tool)
- **Notes to the reviewer** inside the issuer letter (V1 keeps them in a separate field)
- **Delivery scans** in a different city from a "matched" address, in 112 of 131 deliveries (a synthetic-data bug, fixed at the source)

Caveat: the rubric was refined on round 1's letters; round 2 is the cleaner test.
"""
)

st.subheader("Cost and speed (V1)")
pc = per_case("v1")
lat = pd.DataFrame([{"case": k, "latency_s": v["usage"].get("latency_s", 0), "cost_usd": v["usage"].get("cost_usd", 0)}
                    for k, v in pc.items()])
st.scatter_chart(lat, x="latency_s", y="cost_usd", x_label="latency (s)", y_label="cost (USD)")
st.caption("Bottom-left: accepts and brief-only escalations (no letter, often no model call). "
           "Upper-right: cases with a letter. Grading 76 letters with Opus costs about $2.70 per run.")
