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


SEED = 11


def calibration_sample(results: dict, n: int = 40, seed: int = SEED) -> list[str]:
    """The letters a human grades: a fixed random sample of fight/escalate drafts."""
    pool = sorted(cid for cid, r in results.items() if r.get("output")
                  and r["output"]["decision"]["action"] in ("fight", "escalate"))
    return sorted(random.Random(seed).sample(pool, min(n, len(pool))))


def sheet(version: str, n: int, seed: int = SEED):
    d = RESULTS_DIR / version
    results = _latest(d / "outputs.jsonl")
    cases = {json.loads(l)["case_id"]: json.loads(l) for l in open(CASES_DIR / "cases.jsonl")}
    pick = calibration_sample(results, n, seed)
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


def agree(version: str, judge_file: str = "judge.jsonl"):
    d = RESULTS_DIR / version
    judge = _latest(d / judge_file)
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
    out["judge_file"] = judge_file
    name = "judge_agreement.json" if judge_file == "judge.jsonl" else f"judge_agreement_{judge_file.removesuffix('.jsonl')}.json"
    (d / name).write_text(json.dumps(out, indent=1))
    print(out)


def gold(version: str, judge_files: list[str]):
    """Compare judge runs with the adjudicated gold labels (judge_gold_labels.csv). Each run is also
    scored combined with the deterministic concession check (a letter fails if either fails)."""
    from evals.metrics.letter_checks import check as letter_check
    d = RESULTS_DIR / version
    outs = _latest(d / "outputs.jsonl")
    conceded = {c for c, r in outs.items()
                if letter_check(((r.get("output") or {}).get("draft") or {}).get("narrative", ""))["concession"]}
    g = {r["case_id"]: int(r["gold_pass"]) for r in csv.DictReader(open(d / "judge_gold_labels.csv")) if r["gold_pass"] != ""}
    out = {}
    runs = [(jf, False) for jf in judge_files] + [(jf, True) for jf in judge_files]
    for jf, with_check in runs:
        j = {c: int(r["pass"]) and not (with_check and c in conceded)
             for c, r in _latest(d / jf).items() if r.get("scores")}
        j = {c: int(v) for c, v in j.items()}
        pairs = [(g[c], j[c]) for c in g if c in j]
        n = len(pairs)
        po = sum(a == b for a, b in pairs) / n
        pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
        pe = pa * pb + (1 - pa) * (1 - pb)
        out[jf + (" + concession check" if with_check else "")] = {"n": n, "agreement": round(po, 3), "kappa": round((po - pe) / (1 - pe), 3),
                   "missed_failures": sum(1 for a, b in pairs if a == 0 and b == 1),
                   "false_failures": [c for c in g if c in j and g[c] == 1 and j[c] == 0]}
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sheet", "agree", "gold"])
    ap.add_argument("--version", required=True)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--judge-file", default="judge.jsonl", help="for gold: comma-separated list")
    a = ap.parse_args()
    if a.cmd == "sheet":
        sheet(a.version, a.n)
    elif a.cmd == "agree":
        agree(a.version, a.judge_file)
    else:
        gold(a.version, a.judge_file.split(","))
