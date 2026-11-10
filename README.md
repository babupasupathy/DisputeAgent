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
| 2. V0 baseline | built and harness-validated; **not yet run** (needs an Anthropic API key) |
| 3-7 | not started (V4 LangGraph port skipped) |

## Quickstart

```bash
pip install -r requirements.txt
python -m evals.labeling.build_cases            # builds data/synthetic/store.db + evals/cases/cases.jsonl
python -m pytest -q                             # 17 tests
uvicorn src.backend.api:app --reload            # mock store + processor API
python -m evals.labeling.handcheck_sheet --n 40 > docs/handcheck_sample.md
```

### Running an agent version

```bash
export ANTHROPIC_API_KEY=...            # never committed
export ANTHROPIC_MODEL=claude-sonnet-5-5 # agent
export JUDGE_MODEL=claude-opus-5-5       # draft-quality judge
python -m evals.run --version v0 --limit 5   # smoke test first
python -m evals.run --version v0             # all 162 cases (resumable)
python -m evals.judge --version v0
python -m evals.score --version v0           # writes evals/results/v0/{scores.json,report.md}
EVAL_VERSION=v0 python -m pytest evals/test_deepeval.py -q   # same checks as DeepEval metrics
```

`python -m evals.run --version oracle` runs a label-reading "oracle" that must score 100%; it
validates the harness without spending money.

## Showcase app (Streamlit)

`app/` is a read-only Streamlit site for the project: overview, architecture, V0 results, a case
explorer over all 162 disputes, the LLM-vs-code plan and the roadmap. It reads committed eval
results only, so it needs no API key and makes no model calls.

```bash
pip install -r app/requirements.txt
streamlit run app/streamlit_app.py
```

To host it on Streamlit Community Cloud: sign in at share.streamlit.io with GitHub, choose
**Create app**, pick this repository and branch, and set the main file path to
`app/streamlit_app.py`. No secrets are needed.

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
