# Dispute Agent

An AI agent that handles card chargebacks for an online store. It reads a dispute, pulls the order,
shipping, support and refund records, decides whether to **fight, accept or escalate** to a person,
and drafts the response letter for human review.

It's a portfolio project. The interesting part isn't the agent; it's the evals, the product
decisions, and what they showed.

**Try it live: [disputeagent.streamlit.app](https://disputeagent.streamlit.app)** · All data is synthetic.

## Results

Every version runs on the same 162 labelled test disputes (Visa, Mastercard, Amex).

| | V0 baseline | V1 |
|---|---|---|
| Decisions correct | 76% | **100%** |
| Wrongful auto-accepts (money given up without review) | 14 ($5,377) | **0** |
| Response letters passing review | 62% | **99%** |
| Cost per dispute | $0.023 | **$0.012** |
| Typical response time | 10.6 s | **2.4 s** |

## What I learned

- **The data was the problem, not the model.** Most failing letters stated the customer's account
  age wrongly, because the tool reported age *today*, not at the time of the order. Fixing that one
  field took letters from 62% to 92% with no prompt change.
- **Don't let the model apply the rules.** V0 escalated 20 winnable disputes because it didn't know
  which evidence each reason code requires. V1 does lookups, expected value and the escalation rules
  in code; the model only reads free text and writes letters.
- **Check the checker.** An AI judge grades every letter. I graded 60 letters blind in Braintrust
  and settled every disagreement, which raised the judge's agreement with me from κ 0.42 to 0.73 and
  found three data bugs no automated check caught.
- **Pick models on ROI, not price.** A cheaper model (Haiku) read support messages almost as well
  as Sonnet but missed more customer acknowledgements of receipt. One lost dispute ($200–500)
  outweighs about $0.002 saved per dispute, so Sonnet stayed.
- **Escalations get a brief, not a letter.** When records conflict or evidence is missing, the
  reviewer gets a short brief and decides; a letter is drafted only if they contest. A guardrail
  blocks letters that would argue against the merchant's own admission.

## How it works

```
dispute ─► fetch all records (code) ─► read issuer note + support messages (Claude Sonnet)
        ─► rules table, evidence checks, P(win), expected value, 7 decision rules (code)
        ─► fight: write letter (Sonnet) ─► human review queue ─► submit
        ─► escalate: reviewer brief, letter on demand
        ─► accept: one-line note, no model call
```

The reasoning behind each choice is in [docs/decisions.md](docs/decisions.md). Every measurement,
including what didn't work, is in [docs/evals.md](docs/evals.md).

## Built with

Python · Claude Sonnet 5.5 (agent) and Opus 5.5 (judge) via the Anthropic API · Braintrust (evals and
human grading) · Streamlit (demo and review queue) · SQLite · FastAPI (mock store and processor) ·
built hands-on with Claude Code

## Run it yourself

```bash
pip install -r requirements.txt
python -m evals.labeling.build_cases       # builds the synthetic store and the 162 labelled cases
python -m pytest -q                        # 32 tests
streamlit run app/streamlit_app.py         # demo + review queue (no API key needed to browse results)
```

To run the agent and evals you need an Anthropic API key (`ANTHROPIC_API_KEY` or
`DISPUTE_AGENT_ANTHROPIC_KEY`):

```bash
export ANTHROPIC_MODEL=claude-sonnet-5-5 JUDGE_MODEL=claude-opus-5-5
python -m evals.run --version v1             # agent on all 162 cases (resumable), about $2
python -m evals.judge --version v1           # grade the letters, about $3
python -m evals.score --version v1           # writes evals/results/v1/report.md
python -m evals.reading.run read --tag sonnet   # reading test on 30 messy support threads
python -m evals.braintrust_sync upload --version v1   # optional: compare versions in Braintrust
```

## Repository layout

```
app/                Streamlit demo: results, case explorer, review queue
src/agent/          v0 (one model call) and v1 (decide.py in code + reader and writer prompts)
src/backend/        synthetic store, data generator, tools the agent calls, mock API
src/review_ui/      review records and override metrics
evals/              runner, judge, scoring, calibration, reading test, Braintrust sync
evals/cases/        162 labelled test disputes (never read by the agent)
config/             decision thresholds and costs (product decisions, not code)
docs/               decisions.md, evals.md, data.md
```

All data is synthetic: a generated store, customers and disputes. No real card or customer data is used.
