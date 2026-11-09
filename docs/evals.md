# Eval harness

## Flow

```
evals/run.py      agent version x 162 cases -> evals/results/<v>/outputs.jsonl
                  (output JSON, full trace of what the agent saw, tool calls, tokens, cost, latency)
evals/judge.py    Opus judge on fight/escalate drafts -> judge.jsonl
evals/score.py    deterministic checks + judge -> scores.json, report.md, per_case.jsonl
evals/test_deepeval.py   the same per-case checks as DeepEval metrics (pytest)
```

Results are stored, not recomputed, so scoring is free and repeatable, and versions are compared
on identical cases. All versions share one output schema (`src/agent/schema.py`).

## Dimensions

| Dimension | Metric | Method |
|---|---|---|
| Classification | category accuracy; network + reason code accuracy | deterministic |
| Tool use | required-tool recall, unneeded calls per case (n/a for V0) | deterministic, from the call trace |
| Evidence completeness | exact match of required present/missing lists; **false-missing rate** (present items the agent marked missing); false-present rate (items claimed that aren't there); strong-evidence F1 | deterministic vs labels |
| Decision | accuracy, confusion matrix, by category; **wrongful auto-accepts** (count and $) | deterministic |
| Escalation | precision, recall, predicted vs expected rate | deterministic |
| No fabrication | every order/dispute/customer ID, tracking number, $ amount, date and card fragment in the draft must appear in the agent's trace. Sums/differences of two seen amounts (e.g. unrefunded balance) are allowed and reported. | deterministic regex trace check |
| Draft quality + soft claims | 4 criteria scored 1-5 (addresses requirements, grounded, clarity, format), list of unsupported claims; pass = all >= 4 and no unsupported claims | LLM judge (Opus 5.5), G-Eval-style rubric |
| Cost and latency | USD per case (from token usage x `config/pricing.toml`), p50/p95 latency, served model | logged per call |

Wrongful auto-accepts get their own line because of the EV-first rule (docs/decisions.md): a
wrongly "missing" item can push EV below zero and the case is accepted with no human review.

## How the harness itself was validated

- An **oracle** answering from the labels scores 100% on every deterministic dimension with zero
  fabrications (162/162 DeepEval cases pass).
- Sabotaging 10% of oracle decisions makes exactly those 17 cases fail in DeepEval.
- Unit tests inject invented tracking numbers, dates, amounts, card digits and IDs (all caught)
  and real/derived facts (none flagged). This caught a real bug in the date regex.

## Judge calibration (pending)

The judge is not trusted until calibrated. After a run:
```bash
python -m evals.judge_calibration sheet --version v0 --n 40   # CSV without the judge's verdicts
# a human fills human_pass (1/0) and per-criterion scores
python -m evals.judge_calibration agree --version v0          # pass agreement, Cohen's kappa
```
Draft-quality numbers are reported as "uncalibrated" until this is done.

## V0 (baseline)

One structured-output call. No tools, no rules table: every record the tools would return is
pasted into the prompt. The prompt carries the merchant policy (rendered from
`config/decision.toml`), grounding rules, and the evidence vocabulary (IDs and descriptions,
but not which items each network/category requires). V0 must infer the requirements itself.
That gap is what V1's rules table is meant to close, so the V0 to V1 delta on evidence
completeness is the clearest test of the rules table.

Settings: `config/agent.toml` (effort `medium`, 16k max tokens). Server-side refusal fallback is
enabled; the served model is logged per case, so a fallback would show up in `served_models`.
