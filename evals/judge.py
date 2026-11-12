"""Run the draft-quality judge over a version's outputs.

    JUDGE_MODEL=claude-opus-5-5 python -m evals.judge --version v0
    JUDGE_MODEL=claude-opus-5-5 python -m evals.judge --version v0 --calibration-set --out judge_v2.jsonl

Judges drafts where the agent chose fight or escalate (accept drafts are one sentence).
Writes evals/results/<version>/<out> (default judge.jsonl; resumable). --calibration-set limits it
to the 40 letters graded by a human (same sample as evals.judge_calibration)."""
from __future__ import annotations

import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from src.agent.llm import make_client, model_from_env
from evals.judge_calibration import calibration_sample
from evals.metrics.judge import judge_draft
from evals.paths import CASES_DIR, RESULTS_DIR
from evals.score import _latest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--out", default="judge.jsonl")
    ap.add_argument("--calibration-set", action="store_true")
    ap.add_argument("--n", type=int, default=40)
    args = ap.parse_args()
    model = model_from_env("JUDGE_MODEL")
    client = make_client()
    d = RESULTS_DIR / args.version
    cases = {json.loads(l)["case_id"]: json.loads(l) for l in open(CASES_DIR / "cases.jsonl")}
    results = _latest(d / "outputs.jsonl")
    out = d / args.out
    done = set(_latest(out)) if out.exists() else set()
    keep = set(calibration_sample(results, args.n)) if args.calibration_set else None
    todo = [r for cid, r in results.items() if r.get("output") and cid not in done
            and r["output"]["decision"]["action"] in ("fight", "escalate") and (keep is None or cid in keep)]
    lock = threading.Lock()

    def one(r):
        c = cases[r["case_id"]]
        try:
            j = judge_draft(client, model, c["dispute"], c["labels"]["category"], r["trace"], r["output"])
            j["error"] = None
        except Exception as e:
            j = {"error": f"{type(e).__name__}: {e}", "scores": None}
        j.update(case_id=r["case_id"], judge_model=model)
        with lock, open(out, "a") as f:
            f.write(json.dumps(j, sort_keys=True) + "\n")
        print(r["case_id"], "ERR" if j["error"] else ("pass" if j["pass"] else "fail"), flush=True)

    with ThreadPoolExecutor(args.concurrency) as ex:
        list(ex.map(one, todo))


if __name__ == "__main__":
    main()
