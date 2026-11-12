"""Push stored eval results to Braintrust, and run the judge calibration through its review screen.

    python -m evals.braintrust_sync upload --version v0             # experiment "<version>": all cases + scores
    python -m evals.braintrust_sync calibration-upload --version v0 # blind 40-letter review set (no judge grades)
    python -m evals.braintrust_sync calibration-pull --version v0   # human grades -> judge_calibration.csv -> agreement
    python -m evals.braintrust_sync adjudication-upload --version v0  # human-vs-judge disagreements, both views shown
    python -m evals.braintrust_sync adjudication-pull --version v0    # verdicts -> judge_gold_labels.csv + agreement

Uploads only results already computed under evals/results; no model calls. Uses the Braintrust REST
API at api.braintrust.dev. Auth: BRAINTRUST_API_KEY if set, otherwise none is sent (in the cloud
session a network proxy adds the saved key). The local harness stays the source of truth.
"""
from __future__ import annotations

import argparse
import csv
import json
import os

import httpx

from evals.judge_calibration import agree, calibration_sample
from evals.metrics.judge import CRITERIA
from evals.paths import CASES_DIR, RESULTS_DIR
from evals.score import _latest
from src.knowledge.rules import lookup

API = os.environ.get("BRAINTRUST_API_URL", "https://api.braintrust.dev")
PROJECT = os.environ.get("BRAINTRUST_PROJECT", "DisputeAgent")
SEED = 11  # same sample as evals.judge_calibration.sheet


def _client() -> httpx.Client:
    key = os.environ.get("BRAINTRUST_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    return httpx.Client(base_url=API, headers=headers, timeout=60)


def _post(c: httpx.Client, path: str, body: dict) -> dict:
    r = c.post(path, json=body)
    if r.status_code >= 400:
        raise SystemExit(f"POST {path} -> {r.status_code}: {r.text[:500]}")
    return r.json()


def _project(c) -> dict:
    return _post(c, "/v1/project", {"name": PROJECT})


def _experiment(c, project_id: str, name: str, description: str, metadata: dict) -> dict:
    return _post(c, "/v1/experiment", {"project_id": project_id, "name": name, "description": description,
                                        "metadata": metadata})


def _insert(c, exp_id: str, events: list[dict]):
    for i in range(0, len(events), 50):
        _post(c, f"/v1/experiment/{exp_id}/insert", {"events": events[i:i + 50]})


def _load(version: str):
    d = RESULTS_DIR / version
    cases = {json.loads(l)["case_id"]: json.loads(l) for l in open(CASES_DIR / "cases.jsonl")}
    return (cases, _latest(d / "outputs.jsonl"), _latest(d / "per_case.jsonl"),
            _latest(d / "judge.jsonl") if (d / "judge.jsonl").exists() else {})


def _b(x) -> float:
    return 1.0 if x else 0.0


def upload(version: str):
    cases, outs, per, judge = _load(version)
    scores = json.loads((RESULTS_DIR / version / "scores.json").read_text())
    events = []
    for cid, case in cases.items():
        res, pc = outs.get(cid) or {}, per.get(cid) or {}
        out, lab = res.get("output") or {}, case["labels"]
        ev, dec, cl = out.get("evidence") or {}, out.get("decision") or {}, out.get("classification") or {}
        s = {
            "decision_correct": _b(pc.get("decision", {}).get("correct")),
            "no_wrongful_auto_accept": 1.0 - _b(pc.get("decision", {}).get("wrongful_auto_accept")),
            "escalation_correct": _b(pc.get("escalation", {}).get("expected") == pc.get("escalation", {}).get("predicted")),
            "category_correct": _b(pc.get("classification", {}).get("category_correct")),
            "reason_code_correct": _b(pc.get("classification", {}).get("reason_code_correct")),
            "required_evidence_exact": _b(pc.get("evidence", {}).get("required_exact")),
            "no_false_missing": 1.0 - _b(pc.get("evidence", {}).get("false_missing")),
            "no_unsupported_facts": 1.0 - _b(pc.get("fabrication", {}).get("fabricated")),
            "no_concession": 1.0 - _b((pc.get("letter") or {}).get("concession")),
        }
        j = judge.get(cid)
        if j and j.get("scores"):
            s["judge_pass"] = _b(j.get("pass") and not (pc.get("letter") or {}).get("concession"))
            s.update({f"judge_{k}": (v - 1) / 4 for k, v in j["scores"].items()})
        u = res.get("usage") or {}
        events.append({
            "id": cid,
            "input": {"dispute": case["dispute"], "scenario": case["scenario"]},
            "output": {"action": dec.get("action"), "category": cl.get("category"), "reason_code": cl.get("reason_code"),
                       "required_present": ev.get("required_present"), "required_missing": ev.get("required_missing"),
                       "rationale": dec.get("rationale"), "letter": (out.get("draft") or {}).get("narrative")},
            "expected": {"action": lab["decision"], "category": lab["category"], "reason_code": lab["reason_code"],
                         "required_present": lab["required_present"], "required_missing": lab["required_missing"],
                         "reason": lab.get("decision_reason")},
            "scores": s,
            "metadata": {"scenario": case["scenario"], "category": lab["category"], "network": case["dispute"]["network"],
                         "amount": case["dispute"]["amount"], "source": case["source"],
                         "wrongful_auto_accept_usd": pc.get("decision", {}).get("wrongful_auto_accept_amount", 0.0),
                         "cost_usd": u.get("cost_usd"), "latency_s": u.get("latency_s"),
                         "served_models": u.get("served_models"), "error": res.get("error")},
            "metrics": {"prompt_tokens": (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0)
                        + (u.get("cache_creation_input_tokens") or 0),
                        "completion_tokens": u.get("output_tokens") or 0},
        })
    with _client() as c:
        p = _project(c)
        cost = scores.get("cost_latency", {})
        e = _experiment(c, p["id"], version, f"{version}: stored results from evals/results/{version} (synthetic data)",
                        {"version": version, "models": cost.get("served_models"), "n_cases": len(events),
                         "total_cost_usd": cost.get("total_usd"), "source": "evals/braintrust_sync.py"})
        _insert(c, e["id"], events)
    print(f"uploaded {len(events)} cases to experiment '{version}' (id {e['id']}) in project {PROJECT}")


# ---------------- judge calibration ----------------

def _cal_name(version: str) -> str:
    return f"{version}-judge-calibration"


def _sample(outs: dict, n: int) -> list[str]:
    return calibration_sample(outs, n, SEED)


GRADE_CATS = [{"name": f"{i}", "value": (i - 1) / 4} for i in range(1, 6)]
HUMAN_SCORES = {"human_pass": [{"name": "Pass", "value": 1.0}, {"name": "Fail", "value": 0.0}],
                **{f"human_{k}": GRADE_CATS for k in CRITERIA}}


def _ensure_review_scores(c, project_id: str):
    for name, cats in HUMAN_SCORES.items():
        crit = name.removeprefix("human_")
        desc = ("Would you send this letter after review? Pass = every criterion at least 4 and no unsupported claim."
                if name == "human_pass" else f"1-5. {CRITERIA[crit]}")
        _post(c, "/v1/project_score", {"project_id": project_id, "name": name, "score_type": "categorical",
                                       "categories": cats, "description": desc})


def calibration_upload(version: str, n: int):
    cases, outs, _, _ = _load(version)
    pick = _sample(outs, n)
    events = []
    for cid in pick:
        case, res = cases[cid], outs[cid]
        out, d = res["output"], case["dispute"]
        cat = case["labels"]["category"]
        rule = lookup(d["network"], d["reason_code"], cat)
        events.append({
            "id": cid,
            "input": {"dispute": d, "category": cat,
                      "evidence_network_expects": rule.required_evidence,
                      "evidence_that_strengthens": rule.strong_evidence,
                      "records_the_agent_had": {t["tool"]: t["output"] for t in res["trace"]}},
            "output": {"letter": out["draft"]["narrative"], "exhibits": out["draft"]["evidence_list"],
                       "agent_action": out["decision"]["action"]},
            "metadata": {"category": cat, "scenario": case["scenario"],
                         "instructions": "Grade blind: judge scores are deliberately not shown here."},
        })
    with _client() as c:
        p = _project(c)
        _ensure_review_scores(c, p["id"])
        e = _experiment(c, p["id"], _cal_name(version),
                        f"Blind human grading of {len(events)} {version} letters, to calibrate the Opus judge.",
                        {"version": version, "seed": SEED, "n": len(events), "purpose": "judge calibration"})
        _insert(c, e["id"], events)
    print(f"uploaded {len(events)} letters to experiment '{_cal_name(version)}' (id {e['id']})")


def _fetch_all(c, exp_id: str) -> list[dict]:
    rows, cursor = [], None
    while True:
        body = {"limit": 200, **({"cursor": cursor} if cursor else {})}
        r = _post(c, f"/v1/experiment/{exp_id}/fetch", body)
        rows += r.get("events", [])
        cursor = r.get("cursor")
        if not cursor or not r.get("events"):
            return rows


def _review_scores(events: list[dict], prefix: str) -> dict[str, dict]:
    """Human review scores per case. Grading in the review screen writes the scores onto the case's
    row AND logs a child "review" span with its own id under the same root span, so every row is
    mapped to its case via root_span_id."""
    case_of_root = {ev["root_span_id"]: ev["id"] for ev in events if ev.get("input")}
    latest: dict[str, dict] = {cid: {} for cid in case_of_root.values()}
    for ev in events:
        cid = case_of_root.get(ev.get("root_span_id"))
        if cid is not None:
            latest[cid].update({k: v for k, v in (ev.get("scores") or {}).items()
                                if k.startswith(prefix) and v is not None})
    return latest


def calibration_pull(version: str):
    from_val = {round((i - 1) / 4, 2): i for i in range(1, 6)}
    with _client() as c:
        p = _project(c)
        e = _experiment(c, p["id"], _cal_name(version), "", {})
        events = _fetch_all(c, e["id"])
    latest = _review_scores(events, "human_")
    out = RESULTS_DIR / version / "judge_calibration.csv"
    graded = 0
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "human_pass"] + [f"human_{k}" for k in CRITERIA])
        for cid, s in sorted(latest.items()):
            hp = s.get("human_pass")
            crit = [from_val.get(round(s[f"human_{k}"], 2), "") if f"human_{k}" in s else "" for k in CRITERIA]
            w.writerow([cid, "" if hp is None else int(round(hp))] + crit)
            graded += hp is not None
    print(f"{graded} of {len(latest)} letters graded; wrote {out}")
    agree(version)


# ---------------- adjudication of human vs judge disagreements ----------------

ADJ_SCORE = "adjudication_who_is_right"
ADJ_CATS = [{"name": "Judge right", "value": 1.0}, {"name": "My original grade right", "value": 0.0},
            {"name": "Unsure", "value": 0.5}]


def _adj_name(version: str) -> str:
    return f"{version}-judge-adjudication"


def _human(version: str) -> dict[str, dict]:
    rows = csv.DictReader(open(RESULTS_DIR / version / "judge_calibration.csv"))
    return {r["case_id"]: r for r in rows if r["human_pass"] != ""}


def adjudication_upload(version: str, judge_file: str):
    cases, outs, _, _ = _load(version)
    judge = _latest(RESULTS_DIR / version / judge_file)
    human = _human(version)
    dis = sorted(cid for cid in human if cid in judge and int(human[cid]["human_pass"]) != int(judge[cid]["pass"]))
    pf = lambda x: "PASS" if x else "FAIL"
    events = []
    for cid in dis:
        h, j, case, res = human[cid], judge[cid], cases[cid], outs[cid]
        issues = j.get("issues") or [{"claim": c, "problem": "", "severity": "material"} for c in j.get("unsupported_claims", [])]
        events.append({
            "id": cid,
            "input": {
                "question": "The judge and your original grade disagree on this letter. Read the judge's points and "
                            "the records, then answer: who is right?",
                "your_original_grade": {"pass": pf(int(h["human_pass"])),
                                        **{k: int(h[f"human_{k}"]) for k in CRITERIA if h.get(f"human_{k}")}},
                "judge_verdict": {"pass": pf(j["pass"]), **j["scores"]},
                "judge_material_problems": [f"{i['claim']}  ->  {i['problem']}" for i in issues if i["severity"] == "material"],
                "judge_minor_problems": [f"{i['claim']}  ->  {i['problem']}" for i in issues if i["severity"] == "minor"],
                "judge_reasoning": j.get("reasoning"),
                "dispute": case["dispute"],
                "records_the_agent_had": {t["tool"]: t["output"] for t in res["trace"]},
            },
            "output": {"letter": res["output"]["draft"]["narrative"], "exhibits": res["output"]["draft"]["evidence_list"]},
            "metadata": {"order_id": case["dispute"]["order_id"], "judge_file": judge_file},
        })
    with _client() as c:
        p = _project(c)
        _post(c, "/v1/project_score", {"project_id": p["id"], "name": ADJ_SCORE, "score_type": "categorical",
                                       "categories": ADJ_CATS,
                                       "description": "Who is right about this letter: the judge or your original grade?"})
        e = _experiment(c, p["id"], _adj_name(version),
                        f"Settle the {len(events)} letters where the human grade and {judge_file} disagree.",
                        {"version": version, "judge_file": judge_file, "n": len(events), "purpose": "adjudication"})
        _insert(c, e["id"], events)
    print(f"uploaded {len(events)} disagreements to experiment '{_adj_name(version)}' (id {e['id']}): {dis}")


def _kappa(pairs: list[tuple[int, int]]) -> float:
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def adjudication_pull(version: str, judge_file: str):
    with _client() as c:
        p = _project(c)
        e = _experiment(c, p["id"], _adj_name(version), "", {})
        verdicts = {cid: s.get(ADJ_SCORE) for cid, s in _review_scores(_fetch_all(c, e["id"]), "adjudication_").items()}
    judge = _latest(RESULTS_DIR / version / judge_file)
    human = _human(version)
    gold, rows = {}, []
    for cid, h in human.items():
        hp, jp = int(h["human_pass"]), int(judge[cid]["pass"])
        if hp == jp:
            g, how = hp, "agreed"
        else:
            v = verdicts.get(cid)
            g, how = {1.0: (jp, "judge right"), 0.0: (hp, "original grade right")}.get(v, (None, "unsure" if v == 0.5 else "not answered"))
        rows.append([cid, hp, jp, how, "" if g is None else g])
        if g is not None:
            gold[cid] = g
    # Owner rulings made after adjudication (judge_gold_overrides.csv) take precedence.
    ov_path = RESULTS_DIR / version / "judge_gold_overrides.csv"
    if ov_path.exists():
        ov = {r["case_id"]: int(r["gold_pass"]) for r in csv.DictReader(open(ov_path))}
        for r in rows:
            if r[0] in ov:
                r[3], r[4] = "owner ruling (override)", ov[r[0]]
                gold[r[0]] = ov[r[0]]
    out = RESULTS_DIR / version / "judge_gold_labels.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "human_pass", f"judge_pass({judge_file})", "how_settled", "gold_pass"])
        w.writerows(sorted(rows))
    summary = {"n_gold": len(gold), "settled": dict(sorted({r[3]: sum(1 for x in rows if x[3] == r[3]) for r in rows}.items())),
               "gold_pass_rate": round(sum(gold.values()) / len(gold), 3) if gold else None}
    for name, src in [("human", {c: int(h["human_pass"]) for c, h in human.items()})] + \
                     [(f.removesuffix(".jsonl"), {c: int(r["pass"]) for c, r in _latest(RESULTS_DIR / version / f).items() if r.get("scores")})
                      for f in ("judge_v1.jsonl", judge_file)]:
        pairs = [(gold[c], src[c]) for c in gold if c in src]
        if pairs:
            summary[f"{name}_vs_gold"] = {"n": len(pairs), "agreement": round(sum(a == b for a, b in pairs) / len(pairs), 3),
                                          "kappa": round(_kappa(pairs), 3),
                                          "missed_failures": sum(1 for g, x in pairs if g == 0 and x == 1),
                                          "false_failures": sum(1 for g, x in pairs if g == 1 and x == 0)}
    (RESULTS_DIR / version / "judge_gold_agreement.json").write_text(json.dumps(summary, indent=1))
    print(f"wrote {out}")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["upload", "calibration-upload", "calibration-pull",
                                    "adjudication-upload", "adjudication-pull"])
    ap.add_argument("--judge-file", default="judge_v2.jsonl")
    ap.add_argument("--version", required=True)
    ap.add_argument("--n", type=int, default=40)
    a = ap.parse_args()
    {"upload": lambda: upload(a.version),
     "calibration-upload": lambda: calibration_upload(a.version, a.n),
     "calibration-pull": lambda: calibration_pull(a.version),
     "adjudication-upload": lambda: adjudication_upload(a.version, a.judge_file),
     "adjudication-pull": lambda: adjudication_pull(a.version, a.judge_file)}[a.cmd]()
