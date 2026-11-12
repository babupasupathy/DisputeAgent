import json

import pandas as pd
import streamlit as st

from data import action_label, cases, judge, outputs, per_case

st.title("Case explorer")
st.caption("Every one of the 162 test disputes: the correct answer, what V0 decided, and the letter it wrote.")

C, O, P, J = cases(), outputs("v0"), per_case("v0"), judge("v0")

rows = []
for cid, case in C.items():
    lab = case["labels"]
    out = (O.get(cid) or {}).get("output") or {}
    pred = (out.get("decision") or {}).get("action")
    rows.append({
        "case": cid, "scenario": case["scenario"], "category": lab["category"].replace("_", " "),
        "network": case["dispute"]["network"], "amount": case["dispute"]["amount"],
        "correct answer": lab["decision"], "V0": pred, "right": pred == lab["decision"],
    })
df = pd.DataFrame(rows)

f1, f2, f3 = st.columns(3)
only = f1.selectbox("Show", ["All cases", "V0 wrong", "V0 right", "Wrongful auto-accepts"])
scen = f2.multiselect("Scenario", sorted(df["scenario"].unique()))
cat = f3.multiselect("Category", sorted(df["category"].unique()))
view = df
if only == "V0 wrong":
    view = view[~view["right"]]
elif only == "V0 right":
    view = view[view["right"]]
elif only == "Wrongful auto-accepts":
    view = view[(view["V0"] == "accept") & (view["correct answer"] != "accept")]
if scen:
    view = view[view["scenario"].isin(scen)]
if cat:
    view = view[view["category"].isin(cat)]

st.dataframe(view, hide_index=True, width="stretch",
             column_config={"amount": st.column_config.NumberColumn(format="$%.2f"),
                            "right": st.column_config.CheckboxColumn("V0 right?")})
if view.empty:
    st.stop()

cid = st.selectbox("Open a case", view["case"].tolist())
case, lab = C[cid], C[cid]["labels"]
res = O.get(cid) or {}
out = res.get("output") or {}
dec = out.get("decision") or {}

st.divider()
st.subheader(f"{cid} · {case['dispute']['network'].title()} {case['dispute']['reason_code']} · ${case['dispute']['amount']:,.2f}")
if case.get("scenario_note"):
    st.caption(case["scenario_note"])
st.markdown(f"> **Issuer's note:** {case['dispute'].get('issuer_message') or '(empty)'}")

a, b = st.columns(2)
with a:
    st.markdown("##### Correct answer (from the rules)")
    st.markdown(f"**{action_label(lab['decision'])}**")
    st.write(f"Reason: {lab.get('decision_reason', '')}")
    st.write(f"Expected value: ${lab.get('expected_value', 0):,.2f} · P(win) {lab.get('p_win', 0):.2f}")
    st.write("Required evidence present: " + (", ".join(lab.get("required_present", [])) or "none"))
    st.write("Required evidence missing: " + (", ".join(lab.get("required_missing", [])) or "none"))
    if lab.get("escalation_triggers"):
        st.write("Escalation triggers: " + ", ".join(lab["escalation_triggers"]))
with b:
    st.markdown("##### What V0 decided")
    ok = dec.get("action") == lab["decision"]
    st.markdown(f"**{action_label(dec.get('action'))}** {'✅' if ok else '❌'}")
    st.write(dec.get("rationale", ""))
    if dec.get("escalation_reasons"):
        st.write("Escalation reasons: " + ", ".join(dec["escalation_reasons"]))

with st.expander("V0's evidence findings"):
    findings = (out.get("evidence") or {}).get("findings") or []
    if findings:
        st.dataframe(pd.DataFrame(findings)[["evidence_id", "status", "basis"]], hide_index=True, width="stretch")

draft = out.get("draft") or {}
with st.expander("Drafted response letter", expanded=dec.get("action") != "accept"):
    st.markdown(draft.get("narrative", "_none_"))
    if draft.get("evidence_list"):
        st.markdown("**Exhibits**")
        for item in draft["evidence_list"]:
            st.markdown(f"- {item.get('item')} _(source: {item.get('source')})_")

j = J.get(cid)
if j and j.get("scores"):
    calibrated = j.get("rubric_version") == "v4-material"
    with st.expander(f"Opus judge: {'pass' if j.get('pass') else 'fail'}" + ("" if calibrated else " (uncalibrated)")):
        st.write(" · ".join(f"{k.replace('_', ' ')} {v}/5" for k, v in j["scores"].items()))
        issues = j.get("issues") or []
        for sev, label in (("material", "**Material problems** (fail the letter)"), ("minor", "**Minor problems** (noted only)")):
            items = [i for i in issues if i["severity"] == sev]
            if items:
                st.markdown(label)
                for i in items:
                    st.markdown(f"- “{i['claim']}”: {i['problem']}")
        for k, v in (j.get("reasoning") or {}).items():
            st.markdown(f"**{k.replace('_', ' ')}:** {v}")

with st.expander("Records the agent saw (masked, synthetic)"):
    for t in res.get("trace", []):
        st.markdown(f"**{t['tool']}**")
        st.code(json.dumps(t["output"], indent=1), language="json")

u = (P.get(cid) or {}).get("usage") or res.get("usage") or {}
if u:
    st.caption(f"Cost ${u.get('cost_usd', 0):.4f} · {u.get('latency_s', 0):.1f} s · "
               f"{u.get('input_tokens', 0) + u.get('cache_read_input_tokens', 0):,} input / {u.get('output_tokens', 0):,} output tokens")
