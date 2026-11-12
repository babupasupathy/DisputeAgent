"""Score a version's stored outputs on every eval dimension.

    python -m evals.score --version v0

Reads evals/results/<version>/outputs.jsonl (+ judge.jsonl if present), writes scores.json
and report.md next to it, and prints the headline table.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from evals.metrics.deterministic import score_case
from evals.paths import CASES_DIR, RESULTS_DIR


def _latest(path: Path) -> dict[str, dict]:
    out = {}
    if path.exists():
        for line in open(path):
            r = json.loads(line)
            if r.get("output") is not None or r["case_id"] not in out:
                out[r["case_id"]] = r
    return out


def _rate(num, den):
    return round(num / den, 4) if den else None


def _pct(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(q * len(xs)))], 2)


# The judge rubric that passed human calibration (docs/evals.md, "Frozen judge").
CALIBRATED_RUBRIC = "v4-material"
CALIBRATION = {"n_letters": 40, "gold": "evals/results/v0/judge_gold_labels.csv", "agreement": 0.875, "kappa": 0.73,
               "note": "kappa vs adjudicated human labels; rubric fitted on the same 40 letters, so optimistic"}


def aggregate(cases: list[dict], results: dict[str, dict], judge: dict[str, dict]) -> dict:
    per = []
    errors = []
    for c in cases:
        r = results.get(c["case_id"])
        if r is None:
            errors.append({"case_id": c["case_id"], "error": "not run"})
            continue
        s = score_case(c, r)
        (errors if "error" in s else per).append(s)
    ok = [s for s in per]
    n = len(cases)
    amounts = {c["case_id"]: c["dispute"]["amount"] for c in cases}

    cls = {"category_accuracy": _rate(sum(s["classification"]["category_correct"] for s in ok), n),
           "reason_code_accuracy": _rate(sum(s["classification"]["reason_code_correct"] for s in ok), n)}

    tu = [s["tool_use"] for s in ok if s["tool_use"]["applicable"]]
    tool_use = ({"applicable": True,
                 "mean_required_recall": round(statistics.mean(t["required_called"] for t in tu), 4),
                 "all_required_called_rate": _rate(sum(t["all_required_called"] for t in tu), len(tu)),
                 "mean_unneeded_calls": round(statistics.mean(len(t["unneeded_called"]) for t in tu), 3),
                 "mean_calls": round(statistics.mean(t["n_calls"] for t in tu), 2)}
                if tu else {"applicable": False})

    ev = [s["evidence"] for s in ok]
    fm = sum(len(e["false_missing"]) for e in ev)
    fp = sum(len(e["false_present"]) for e in ev)
    lp = sum(e["n_label_present"] for e in ev)
    lm = sum(e["n_required"] - e["n_label_present"] for e in ev)
    stp, sfp, sfn = (sum(e[k] for e in ev) for k in ("strong_tp", "strong_fp", "strong_fn"))
    evidence = {"required_set_correct_rate": _rate(sum(e["required_set_correct"] for e in ev), n),
                "required_exact_rate": _rate(sum(e["required_exact"] for e in ev), n),
                "false_missing_rate": _rate(fm, lp), "false_present_rate": _rate(fp, lm),
                "strong_f1": _rate(2 * stp, 2 * stp + sfp + sfn)}

    dec = [s["decision"] for s in ok]
    conf = Counter((d["expected"], d["predicted"]) for d in dec)
    by_cat = defaultdict(list)
    for s in ok:
        by_cat[s["category"]].append(s["decision"]["correct"])
    decision = {"accuracy": _rate(sum(d["correct"] for d in dec), n),
                "by_category": {k: _rate(sum(v), len(v)) for k, v in sorted(by_cat.items())},
                "confusion_expected_x_predicted": {f"{e}->{p}": k for (e, p), k in sorted(conf.items())},
                "wrongful_auto_accepts": sum(d["wrongful_auto_accept"] for d in dec),
                "wrongful_auto_accept_usd": round(sum(d["wrongful_auto_accept_amount"] for d in dec), 2),
                "fought_should_escalate": sum(d["fought_should_escalate"] for d in dec)}

    esc = [s["escalation"] for s in ok]
    tp = sum(e["predicted"] and e["expected"] for e in esc)
    escalation = {"precision": _rate(tp, sum(e["predicted"] for e in esc)),
                  "recall": _rate(tp, sum(c["labels"]["expected_escalation"] for c in cases)),
                  "predicted_rate": _rate(sum(e["predicted"] for e in esc), n),
                  "expected_rate": _rate(sum(c["labels"]["expected_escalation"] for c in cases), n)}

    lt = [s.get("letter") or {} for s in ok]
    letter = {"with_reviewer_note": sum(bool(x.get("reviewer_note")) for x in lt),
              "with_concession": sum(bool(x.get("concession")) for x in lt),
              "concession_cases": [s["case_id"] for s in ok if (s.get("letter") or {}).get("concession")]}

    fab = [s["fabrication"] for s in ok]
    fabrication = {"drafts_with_unsupported_tokens": sum(f["fabricated"] for f in fab),
                   "rate": _rate(sum(f["fabricated"] for f in fab), len(fab)),
                   "by_type": dict(Counter(k for f in fab for k in f["unsupported"]))}

    judged = [s for s in ok if s["case_id"] in judge and judge[s["case_id"]].get("scores")]
    jv = [judge[s["case_id"]] for s in judged]
    if jv:
        keys = jv[0]["scores"].keys()
        # A letter passes when the judge passes it AND the deterministic check finds no concession.
        passed = [judge[s["case_id"]]["pass"] and not (s.get("letter") or {}).get("concession") for s in judged]
        rubrics = sorted({j.get("rubric_version") or "v1" for j in jv})
        draft_quality = {"n_judged": len(jv),
                         "mean_scores": {k: round(statistics.mean(j["scores"][k] for j in jv), 3) for k in keys},
                         "pass_rate": _rate(sum(passed), len(jv)),
                         "judge_pass_rate": _rate(sum(j["pass"] for j in jv), len(jv)),
                         "drafts_with_unsupported_claims": sum(bool(j["unsupported_claims"]) for j in jv),
                         "rubric_versions": rubrics,
                         "judge_calibrated": rubrics == [CALIBRATED_RUBRIC],
                         "calibration": CALIBRATION if rubrics == [CALIBRATED_RUBRIC] else None}
    else:
        draft_quality = {"n_judged": 0}

    us = [s["usage"] for s in ok if s["usage"]]
    cost = {"total_usd": round(sum(u.get("cost_usd", 0) for u in us), 4),
            "mean_usd_per_case": round(statistics.mean(u.get("cost_usd", 0) for u in us), 5) if us else None,
            "latency_p50_s": _pct([u.get("latency_s", 0) for u in us], 0.5),
            "latency_p95_s": _pct([u.get("latency_s", 0) for u in us], 0.95),
            "mean_input_tokens": round(statistics.mean(u.get("input_tokens", 0) for u in us)) if us else None,
            "mean_output_tokens": round(statistics.mean(u.get("output_tokens", 0) for u in us)) if us else None,
            "served_models": sorted({m for u in us for m in u.get("served_models", [])})}

    failures = {
        "classification": [{"case_id": s["case_id"], "expected": next(c["labels"]["category"] for c in cases if c["case_id"] == s["case_id"])}
                           for s in ok if not s["classification"]["category_correct"]][:8],
        "false_missing": [{"case_id": s["case_id"], "items": s["evidence"]["false_missing"]}
                          for s in ok if s["evidence"]["false_missing"]][:8],
        "false_present": [{"case_id": s["case_id"], "items": s["evidence"]["false_present"]}
                          for s in ok if s["evidence"]["false_present"]][:8],
        "decision": [{"case_id": s["case_id"], "scenario": s["scenario"], "expected": s["decision"]["expected"],
                      "predicted": s["decision"]["predicted"], "amount": amounts[s["case_id"]]}
                     for s in ok if not s["decision"]["correct"]][:12],
        "fabrication": [{"case_id": s["case_id"], **s["fabrication"]["unsupported"]}
                        for s in ok if s["fabrication"]["fabricated"]][:8],
        "errors": errors[:8],
    }
    return {"n_cases": n, "n_scored": len(ok), "n_errors": len(errors), "classification": cls,
            "tool_use": tool_use, "evidence": evidence, "decision": decision, "escalation": escalation,
            "fabrication": fabrication, "letter": letter, "draft_quality": draft_quality, "cost_latency": cost,
            "failures": failures, "per_case": per}


def headline(s: dict) -> list[tuple[str, object]]:
    return [
        ("cases scored / errors", f"{s['n_scored']} / {s['n_errors']}"),
        ("category accuracy", s["classification"]["category_accuracy"]),
        ("reason code accuracy", s["classification"]["reason_code_accuracy"]),
        ("tool use: required recall", s["tool_use"].get("mean_required_recall", "n/a (no tools)")),
        ("tool use: unneeded calls / case", s["tool_use"].get("mean_unneeded_calls", "n/a (no tools)")),
        ("evidence: exact required lists", s["evidence"]["required_exact_rate"]),
        ("evidence: required set correct", s["evidence"]["required_set_correct_rate"]),
        ("evidence: false-missing rate", s["evidence"]["false_missing_rate"]),
        ("evidence: false-present rate", s["evidence"]["false_present_rate"]),
        ("evidence: strong-evidence F1", s["evidence"]["strong_f1"]),
        ("decision accuracy", s["decision"]["accuracy"]),
        ("wrongful auto-accepts (count / $)", f"{s['decision']['wrongful_auto_accepts']} / ${s['decision']['wrongful_auto_accept_usd']:.2f}"),
        ("fought when should escalate", s["decision"]["fought_should_escalate"]),
        ("escalation precision", s["escalation"]["precision"]),
        ("escalation recall", s["escalation"]["recall"]),
        ("escalation rate (pred / expected)", f"{s['escalation']['predicted_rate']} / {s['escalation']['expected_rate']}"),
        ("drafts with unsupported tokens", f"{s['fabrication']['drafts_with_unsupported_tokens']} ({s['fabrication']['rate']})"),
        ("letters with a reviewer note / a concession", f"{s['letter']['with_reviewer_note']} / {s['letter']['with_concession']}"),
        ("draft quality pass rate (judge " + ("calibrated, kappa 0.73" if s["draft_quality"].get("judge_calibrated") else "uncalibrated") + ")",
         s["draft_quality"].get("pass_rate", "not judged")),
        ("cost per case (USD)", s["cost_latency"]["mean_usd_per_case"]),
        ("total cost (USD)", s["cost_latency"]["total_usd"]),
        ("latency p50 / p95 (s)", f"{s['cost_latency']['latency_p50_s']} / {s['cost_latency']['latency_p95_s']}"),
    ]


def write_report(version: str, s: dict, out_dir: Path):
    lines = [f"# Eval results: {version}", "", "Synthetic data. Labels are rule-derived (see docs/data.md).", "",
             "| Metric | Value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in headline(s)]
    lines += ["", "## Decision confusion (expected -> predicted)", "",
              "| pair | count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in s["decision"]["confusion_expected_x_predicted"].items()]
    lines += ["", "## Decision accuracy by category", ""]
    lines += [f"- {k}: {v}" for k, v in s["decision"]["by_category"].items()]
    lines += ["", "## Failure examples", ""]
    for k, v in s["failures"].items():
        lines.append(f"### {k}")
        lines += [f"- `{json.dumps(x, sort_keys=True)}`" for x in v] or ["- none"]
        lines.append("")
    (out_dir / "report.md").write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    args = ap.parse_args()
    out_dir = RESULTS_DIR / args.version
    cases = [json.loads(l) for l in open(CASES_DIR / "cases.jsonl")]
    results = _latest(out_dir / "outputs.jsonl")
    judge = _latest(out_dir / "judge.jsonl")
    s = aggregate(cases, results, judge)
    (out_dir / "scores.json").write_text(json.dumps({k: v for k, v in s.items() if k != "per_case"}, indent=1))
    (out_dir / "per_case.jsonl").write_text("\n".join(json.dumps(p, sort_keys=True) for p in s["per_case"]) + "\n")
    write_report(args.version, s, out_dir)
    for k, v in headline(s):
        print(f"{k:<48} {v}")


if __name__ == "__main__":
    main()
