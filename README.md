# Dispute Agent

A merchant-side AI agent prototype for card chargebacks: it classifies a dispute, gathers
evidence through tools, decides fight / accept / escalate, and drafts the representment for
human review. A portfolio project where the evals and product decisions are the point. See
[PROJECT_BRIEF.md](PROJECT_BRIEF.md).

**All data is synthetic.** See [docs/data.md](docs/data.md).

## Status

| Step | State |
|---|---|
| 1. Synthetic backend, data generator, rules table | done (human hand-check pending) |
| 2. V0 baseline | not started |
| 3-7 | not started |

## Quickstart

```bash
pip install -r requirements.txt
python -m evals.labeling.build_cases            # builds data/synthetic/store.db + evals/cases/cases.jsonl
python -m pytest -q                             # 17 tests
uvicorn src.backend.api:app --reload            # mock store + processor API
python -m evals.labeling.handcheck_sheet --n 40 > docs/handcheck_sample.md
```

Model name and API key will come from `ANTHROPIC_MODEL` and `ANTHROPIC_API_KEY` (from step 2 on).

## Layout

```
config/decision.toml        thresholds and cost assumptions (product decisions)
data/rules/                 rules table + evidence definitions (with sources; unverified)
src/backend/                schema, generator, repository (tool backend), FastAPI mock
src/knowledge/rules.py      rules-table lookup
evals/labeling/             rule-based labeler, hand-written cases, hand-check sheet
evals/cases/                ground-truth cases (never loaded by src/)
docs/                       data.md, decisions.md, handcheck_sample.md
```
