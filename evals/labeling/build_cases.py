"""Build the synthetic DB and the ground-truth eval cases.

    python -m evals.labeling.build_cases

Writes data/synthetic/store.db (gitignored, deterministic) and evals/cases/cases.jsonl.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from src.backend.db import connect
from src.backend.generator import AS_OF, SEED, build, iso, scenario_specs
from src.config import DB_PATH
from evals.paths import CASES_DIR
from evals.labeling.handwritten import HANDWRITTEN
from evals.labeling.labeler import label_dispute


def build_all(db_path: Path = DB_PATH, seed: int = SEED) -> list[dict]:
    specs = scenario_specs(seed) + HANDWRITTEN
    built = build(db_path, specs, seed)
    conn = connect(db_path)
    cases = []
    for spec, webhook in built:
        labels = label_dispute(conn, webhook["dispute_id"], spec.category, AS_OF)
        cases.append({
            "case_id": spec.case_id,
            "source": spec.source,
            "scenario": spec.scenario,
            "scenario_note": spec.note,
            "as_of": iso(AS_OF),
            "dispute": webhook,
            "labels": labels,
        })
    conn.close()
    return cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--out", default=str(CASES_DIR / "cases.jsonl"))
    args = ap.parse_args()
    cases = build_all(Path(args.db))
    with open(args.out, "w") as f:
        for c in cases:
            f.write(json.dumps(c, sort_keys=True) + "\n")
    print(f"wrote {len(cases)} cases to {args.out}")
    print("by category x decision:")
    tab = Counter((c["labels"]["category"], c["labels"]["decision"]) for c in cases)
    for k in sorted(tab):
        print(f"  {k[0]:<20} {k[1]:<9} {tab[k]}")


if __name__ == "__main__":
    main()
