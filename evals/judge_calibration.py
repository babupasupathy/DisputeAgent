"""Judge calibration against human labels.

    python -m evals.judge_calibration sheet --version v0 --n 40   # writes a CSV for a human to fill in
    python -m evals.judge_calibration agree --version v0          # agreement once the CSV is filled

The human fills `human_pass` (1/0) and optionally per-criterion scores, WITHOUT looking at the
judge's verdict (the sheet does not contain it). Agreement = share of drafts where the judge's
pass/fail equals the human's, plus Cohen's kappa and mean absolute score difference."""
from __future__ import annotations

import argparse
import csv
import json
import random

from evals.metrics.judge import CRITERIA
from evals.paths import CASES_DIR, RESULTS_DIR
from evals.score import _latest


def sheet(version: str, n: int, seed: int = 11):
    d = RESULTS_DIR / version
    results = _latest(d / "outputs.jsonl")
    cases = {json.loads(l)["case_id"]: json.loads(l) for l in open(CASES_DIR / "cases.jsonl")}
    pool = sorted(cid for cid, r in results.items() if r.get("output")
                  and r["output"]["decision"]["action"] in ("fight", "escalate"))
    pick = sorted(random.Random(seed).sample(pool, min(n, len(pool))))
    with open(d / "judge_calibration.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "category", "issuer_message", "narrative", "evidence_list", "human_pass"]
                   + [f"human_{k}" for k in CRITERIA] + ["human_note"])
        for cid in pick:
            o, c = results[cid]["output"], cases[cid]
            w.writerow([cid, c["labels"]["category"], c["dispute"]["issuer_message"], o["draft"]["narrative"],
                        json.dumps(o["draft"]["evidence_list"])] + [""] * (len(CRITERIA) + 2))
    print(f"wrote {d / 'judge_calibration.csv'} ({len(pick)} drafts). Records for each case: "
          f"python -m evals.labeling.handcheck_sheet style view, or evals/results/{version}/outputs.jsonl trace.")


def agree(version: str):
    d = RESULTS_DIR / version
    judge = _latest(d / "judge.jsonl")
    rows = [r for r in csv.DictReader(open(d / "judge_calibration.csv")) if r["human_pass"].strip() != ""]
    pairs = [(int(r["human_pass"]), int(judge[r["case_id"]]["pass"])) for r in rows if r["case_id"] in judge]
    n = len(pairs)
    if not n:
        print("no labeled rows yet")
        return
    po = sum(h == j for h, j in pairs) / n
    ph, pj = sum(h for h, _ in pairs) / n, sum(j for _, j in pairs) / n
    pe = ph * pj + (1 - ph) * (1 - pj)
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    diffs = [abs(int(r[f"human_{k}"]) - judge[r["case_id"]]["scores"][k])
             for r in rows for k in CRITERIA if r.get(f"human_{k}", "").strip() and r["case_id"] in judge]
    out = {"n": n, "pass_agreement": round(po, 3), "cohens_kappa": round(kappa, 3),
           "mean_abs_score_diff": round(sum(diffs) / len(diffs), 3) if diffs else None}
    (d / "judge_agreement.json").write_text(json.dumps(out, indent=1))
    print(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sheet", "agree"])
    ap.add_argument("--version", required=True)
    ap.add_argument("--n", type=int, default=40)
    a = ap.parse_args()
    sheet(a.version, a.n) if a.cmd == "sheet" else agree(a.version)
