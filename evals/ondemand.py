"""Eval for "brief now, letter later": simulate a reviewer choosing to contest every brief-only
escalation, draft the letter on demand, and store it so the frozen judge can grade it.

    ANTHROPIC_MODEL=claude-sonnet-5-5 python -m evals.ondemand --version v1
    JUDGE_MODEL=claude-opus-5-5 python -m evals.judge --version v1-ondemand
    python -m evals.ondemand --version v1 --summary

Writes evals/results/<version>-ondemand/outputs.jsonl (resumable)."""
from __future__ import annotations

import argparse
import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from src.agent.llm import agent_config, make_client, model_from_env
from src.agent.v1 import draft_letter
from src.backend.db import connect
from evals.metrics.fabrication import check as fabrication_check
from evals.metrics.letter_checks import check as letter_check
from evals.paths import CASES_DIR, RESULTS_DIR
from evals.score import _latest

# A generic reviewer direction: the eval tests the on-demand path, not a particular reviewer's judgment.
DIRECTION = ("Contest this dispute. Make the strongest honest case from the evidence on file. Do not argue any "
             "point that the records or the merchant's own support messages contradict, and do not claim or imply "
             "evidence that is missing.")


def run(version: str):
    src_dir, out_dir = RESULTS_DIR / version, RESULTS_DIR / f"{version}-ondemand"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "outputs.jsonl"
    results = _latest(src_dir / "outputs.jsonl")
    cases = {json.loads(l)["case_id"]: json.loads(l) for l in open(CASES_DIR / "cases.jsonl")}
    done = {c for c, r in _latest(out).items() if not r.get("error")} if out.exists() else set()
    todo = [cid for cid, r in sorted(results.items()) if r.get("output")
            and (r["output"].get("review") or {}).get("letter_status") == "brief_only" and cid not in done]
    model, client, lock = model_from_env(), make_client(), threading.Lock()

    def one(cid):
        conn = connect()
        base = results[cid]
        try:
            res = draft_letter(client, conn, cases[cid]["dispute"], model, DIRECTION)
            o = copy.deepcopy(base["output"])
            o["draft"] = res["draft"]
            o["review"].update(letter_status="on_demand", reviewer_direction=DIRECTION,
                               reviewer_notes=res["reviewer_notes"])
            row = {"case_id": cid, "output": o, "trace": res["trace"], "tool_calls": [], "usage": res["usage"],
                   "error": None, "version": f"{version}-ondemand", "model": model}
        except Exception as e:
            row = {"case_id": cid, "output": None, "trace": [], "usage": {}, "error": f"{type(e).__name__}: {e}"}
        finally:
            conn.close()
        with lock, open(out, "a") as f:
            f.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        print(cid, "ERR" if row["error"] else f"${row['usage'].get('cost_usd', 0):.4f}", flush=True)

    with ThreadPoolExecutor(agent_config()["agent"]["concurrency"]) as ex:
        list(ex.map(one, todo))


def summary(version: str) -> dict:
    d = RESULTS_DIR / f"{version}-ondemand"
    outs, judge = _latest(d / "outputs.jsonl"), _latest(d / "judge.jsonl")
    cases = {json.loads(l)["case_id"]: json.loads(l) for l in open(CASES_DIR / "cases.jsonl")}
    ok = [c for c, r in outs.items() if r.get("output")]
    judged = [c for c in ok if c in judge and judge[c].get("scores")]
    conc = {c for c in ok if letter_check(outs[c]["output"]["draft"]["narrative"])["concession"]}
    fab = [c for c in ok if fabrication_check(outs[c]["output"], cases[c]["dispute"], outs[c]["trace"])["fabricated"]]
    passed = [c for c in judged if judge[c]["pass"] and c not in conc]
    s = {"letters": len(ok), "judged": len(judged), "pass_rate": round(len(passed) / len(judged), 4) if judged else None,
         "failed": sorted(set(judged) - set(passed)), "fact_check_flags": fab,
         "letter_cost_usd": round(sum(outs[c]["usage"].get("cost_usd", 0) for c in ok), 4)}
    (d / "summary.json").write_text(json.dumps(s, indent=1))
    print(json.dumps(s, indent=1))
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    summary(a.version) if a.summary else run(a.version)
