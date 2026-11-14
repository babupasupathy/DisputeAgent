"""Reading-step eval: V1's reader on hand-written, deliberately messy support threads.

    ANTHROPIC_MODEL=claude-sonnet-5-5 python -m evals.reading.run read --tag sonnet   # ~30 reader calls, about $0.20
    python -m evals.reading.run score --tag sonnet                                     # vs evals/reading/labels.csv

Cases: evals/reading/messy_cases.jsonl (written by hand, 2026-11-14). Labels: evals/reading/labels.csv, made
blind by the project owner (columns: id, category, customer_ack_receipt, merchant_offered_remedy,
merchant_ack_nondelivery, merchant_admitted_defect; facts 1/0). design_intent.json records what each thread
was written to test; it is reported alongside but the owner's labels are the reference.
Since V1's decisions are code, this is now the test that matters: decisions are only as good as this step.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from src.agent.decide import TEXT_FACTS
from src.agent.llm import Usage, make_client, model_from_env
from src.agent.v1 import _read, _verify
from src.knowledge.rules import rules_for
from evals.paths import RESULTS_DIR

HERE = Path(__file__).resolve().parent


def _cases() -> list[dict]:
    return [json.loads(l) for l in open(HERE / "messy_cases.jsonl")]


def read(tag: str):
    out_dir = RESULTS_DIR / f"reading-{tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    model, client = model_from_env(), make_client()
    rows = []
    for c in _cases():
        usage = Usage()
        cands = sorted({r.category for r in rules_for(c["dispute"]["network"], c["dispute"]["reason_code"])})
        d = {**c["dispute"], "dispute_id": c["id"]}
        try:
            res = _read(client, model, usage, d, cands, c["messages"])
            facts, warnings = _verify(res.get("facts") or {}, c["messages"])
            row = {"id": c["id"], "category": res["category"], "facts": facts, "raw": res, "warnings": warnings,
                   "usage": usage.to_dict(), "model": model, "error": None}
        except Exception as e:
            row = {"id": c["id"], "error": f"{type(e).__name__}: {e}", "usage": usage.to_dict(), "model": model}
        rows.append(row)
        print(c["id"], "ERR" if row["error"] else row["category"], flush=True)
    (out_dir / "outputs.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def score(tag: str, labels: str = "labels.csv") -> dict:
    outs = {json.loads(l)["id"]: json.loads(l) for l in open(RESULTS_DIR / f"reading-{tag}" / "outputs.jsonl")}
    gold = {r["id"]: r for r in csv.DictReader(open(HERE / labels))}
    intent = json.load(open(HERE / "design_intent.json"))
    res, misses = {}, []
    for k in ("category", *TEXT_FACTS):
        tp = fp = fn = agree = n = 0
        for cid, g in gold.items():
            o = outs.get(cid)
            if not o or o.get("error") or g.get(k, "") == "":
                continue
            n += 1
            if k == "category":
                ok = o["category"] == g["category"]
            else:
                want, got = g[k] == "1", bool(o["facts"][k]["present"])
                ok = want == got
                tp += want and got; fp += got and not want; fn += want and not got
            agree += ok
            if not ok:
                misses.append({"id": cid, "field": k, "label": g[k], "reader": o["category"] if k == "category"
                               else o["facts"][k], "design_intent": intent[cid][k]})
        res[k] = {"n": n, "agreement": round(agree / n, 3) if n else None}
        if k != "category":
            res[k].update(false_positives=fp, false_negatives=fn)
    ok_rows = [o for o in outs.values() if not o.get("error")]
    res["all_fields_right"] = round(sum(all(m["id"] != cid for m in misses) for cid in gold) / len(gold), 3)
    res["cost_usd"] = round(sum(o["usage"].get("cost_usd", 0) for o in outs.values()), 4)
    res["errors"] = len(outs) - len(ok_rows)
    res["misses"] = misses
    res["label_vs_design_intent_disagreements"] = [
        {"id": cid, "field": k, "label": g[k], "design_intent": intent[cid][k]}
        for cid, g in gold.items() for k in ("category", *TEXT_FACTS)
        if g.get(k, "") != "" and (g[k] if k == "category" else g[k] == "1") != intent[cid][k]]
    (RESULTS_DIR / f"reading-{tag}" / "scores.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["read", "score"])
    ap.add_argument("--tag", required=True, help="e.g. sonnet, haiku")
    ap.add_argument("--labels", default="labels.csv")
    a = ap.parse_args()
    read(a.tag) if a.cmd == "read" else score(a.tag, a.labels)
