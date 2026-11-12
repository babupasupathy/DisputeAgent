"""Run an agent version over the eval cases and store raw results.

    ANTHROPIC_MODEL=claude-sonnet-5-5 python -m evals.run --version v0 [--limit 5] [--cases HW-01,GEN-002]

Writes evals/results/<version>/outputs.jsonl (one line per case; resumable: cases already
present are skipped). Each line: output, trace (everything the agent saw), tool_calls,
usage (tokens, cost_usd, latency_s, served model), error.
"""
from __future__ import annotations

import argparse
import importlib
import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.agent.llm import agent_config, make_client, model_from_env
from src.backend.db import connect
from evals.paths import CASES_DIR, RESULTS_DIR

# "v0-agefix": the unchanged V0 agent run against the fixed account-age tools (a one-change experiment).
VERSIONS = {"v0": "src.agent.v0", "v0-agefix": "src.agent.v0", "v1": "src.agent.v1", "oracle": "evals.oracle"}


def load_cases(ids: str | None = None, limit: int | None = None) -> list[dict]:
    cases = [json.loads(l) for l in open(CASES_DIR / "cases.jsonl")]
    if ids:
        want = set(ids.split(","))
        cases = [c for c in cases if c["case_id"] in want]
    return cases[:limit] if limit else cases


def run(version: str, cases: list[dict], out_path: Path, client=None, model: str | None = None,
        concurrency: int | None = None) -> None:
    mod = importlib.import_module(VERSIONS[version])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out_path.exists():
        done = {json.loads(l)["case_id"] for l in open(out_path) if json.loads(l).get("output") is not None}
    todo = [c for c in cases if c["case_id"] not in done]
    if version != "oracle":
        model = model or model_from_env()
        client = client or make_client()
    lock = threading.Lock()

    def one(case):
        conn = connect()  # sqlite connections are per-thread
        t0 = time.perf_counter()
        try:
            r = mod.run_case(client, conn, case["dispute"], model) if version != "oracle" else mod.run_case(conn, case)
            r["error"] = None
        except Exception as e:  # recorded, counted as a failure in scoring
            r = {"output": None, "trace": [], "tool_calls": [], "usage": {}, "error": f"{type(e).__name__}: {e}",
                 "traceback": traceback.format_exc(limit=3)}
        finally:
            conn.close()
        r.update(case_id=case["case_id"], version=version, model=model, wall_s=round(time.perf_counter() - t0, 3))
        with lock, open(out_path, "a") as f:
            f.write(json.dumps(r, sort_keys=True, default=str) + "\n")
        return r

    n = concurrency or agent_config()["agent"]["concurrency"]
    with ThreadPoolExecutor(max_workers=n) as ex:
        futs = [ex.submit(one, c) for c in todo]
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            status = "ERR " + r["error"][:80] if r["error"] else f"${r['usage'].get('cost_usd', 0):.4f}"
            print(f"[{i}/{len(todo)}] {r['case_id']} {status}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, choices=sorted(VERSIONS))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--cases")
    ap.add_argument("--concurrency", type=int)
    args = ap.parse_args()
    cases = load_cases(args.cases, args.limit)
    run(args.version, cases, RESULTS_DIR / args.version / "outputs.jsonl", concurrency=args.concurrency)


if __name__ == "__main__":
    main()
