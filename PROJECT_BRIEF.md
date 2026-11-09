# Dispute Agent: Project Brief

A merchant-side AI agent that handles card chargebacks for an e-commerce store. It receives an issuer dispute, gathers evidence, decides whether to fight or accept, drafts the representment, and routes weak or high-value cases to a human reviewer.

This is a portfolio project for an AI product manager. The goal is not a production system. The goal is a working, measured prototype where the evals, trade-offs, and product decisions are the story.

## How Claude Code should work on this

- Build in the order given under "Build order". Finish each step, run its checks, and report the numbers before moving on.
- Keep every earlier version runnable (baseline, tools version, full version). They are compared in the final writeup.
- Write tests and eval cases before or alongside each component.
- Read the model name and API key from environment variables. Never hardcode either.
- Log token usage, cost, and latency for every case. Store them with the results.
- Do not add frameworks or features beyond this brief without asking. Start with plain Python and the Anthropic SDK.
- When something in this brief is ambiguous or conflicts with what you find, stop and ask.
- All data is synthetic. Never include real card numbers, real customer data, or any confidential employer information.

## Scope

In scope:
- Merchant-side response to issuer-initiated chargebacks (representment)
- Three or four common e-commerce dispute categories (see below)
- Synthetic backend (orders, shipping, support logs, processor dispute API)
- Human review step with escalation rules
- Eval suite and a comparison of agent versions

Out of scope:
- Real payment processor or card network integration
- Pre-dispute alerts, fraud scoring, chargeback prevention
- Production security, multi-tenancy, scaling
- Business model, pricing, go-to-market

## Architecture

```
Chargeback intake (mock processor webhook)
        |
        v
+-------------------------------------------------------+
| Agent workflow (Claude with tool use)                 |
|  Classify -> Gather evidence -> Decide -> Draft       |
+-------------------------------------------------------+
        |  queries                          |
        v                                   v
+--------------------------+   +--------------------------------+
| Tools (exact lookups)    |   | Knowledge (rules and memory)   |
| - Order DB               |   | - Rules table (exact lookup)   |
| - Shipping API           |   | - RAG store (fuzzy text)       |
| - Support logs, refunds  |   | - Case history (reviewed)      |
| - Processor dispute API  |   +--------------------------------+
+--------------------------+
        |
        v
Human review (approve, edit, escalate)
        |
        v
Submit (mock) and outcome record -> reviewed outcomes -> case history
```

### Design rules

1. Exact data is retrieved by tool or table lookup, never by similarity search. This covers order data, deadlines, and reason code to evidence requirements.
2. RAG holds only unstructured text: rulebook excerpts, merchant policies, reviewed past case narratives.
3. Only human-reviewed outcomes enter case history. Outcomes are noisy and arrive late.
4. The agent never submits directly in v1. Everything passes the review gate. Auto-submit for low-risk cases is a later experiment, enabled only if measured accuracy supports it.
5. Eval cases are stored separately from case history so the agent cannot memorize test answers.
6. The agent must never state evidence that is not present in tool outputs.

## Components

### 1. Intake
Mock a processor webhook that delivers a dispute object:
- dispute_id, network (visa, mastercard, amex), reason_code, reason_category
- order_id (or transaction reference), amount, currency
- received_at, response_due_at
- issuer_message (free text, may be empty)

### 2. Agent steps
Implement as one agent with a fixed pipeline first. Do not split into multiple agents until measured.

- Classify: confirm network and reason category from the dispute object. Look up requirements in the rules table.
- Gather: call tools to collect evidence required for that category. Record which required items were found and which are missing.
- Decide: fight, accept, or escalate. See decision logic.
- Draft: produce the representment narrative and an evidence list. Output structured JSON plus the narrative text.

### 3. Tools (all backed by the synthetic backend)

| Tool | Returns |
|---|---|
| get_order_details(order_id) | Items, amounts, dates, billing and shipping address, payment metadata (synthetic, masked) |
| get_shipping_tracking(order_id) | Carrier, tracking events, delivery date, signature or photo proof flag, address match |
| get_customer_history(customer_id) | Prior orders, prior disputes, account age |
| get_support_communications(order_id) | Emails and chat logs about the order |
| get_refund_status(order_id) | Refunds issued, dates, amounts |
| get_dispute_details(dispute_id) | Deadline, required fields and forms (mock processor API) |
| check_deadline(dispute_id) | Days and hours remaining |
| escalate_to_human(dispute_id, summary, reason) | Queues for review |
| submit_response(dispute_id, payload) | Mock submission, v1 gated behind human approval |

### 4. Knowledge layer

Rules table (exact lookup), keyed by network plus reason code. Starter schema:

```
network, reason_code, category, required_evidence[], strong_evidence[],
response_deadline_days, notes, source, source_date
```

Fill it from public processor documentation and network summaries. Record the source and date for every row. Do not present the table as authoritative. Real rules change and are partly proprietary. Verify before relying on any row.

Starter categories and typical evidence types (to be confirmed against current documentation):

| Category | Typical evidence |
|---|---|
| Item not received | Carrier tracking, delivery confirmation, proof of delivery, address match, customer communications |
| Fraud or unauthorized | Order and payment metadata, customer history, device or IP data, delivery to verified address, prior undisputed orders |
| Not as described or defective | Product listing, return policy, customer communications, return and refund records |
| Credit not processed or refund issue | Refund records, refund policy, communications |

RAG store: chunked text with metadata (network, category, source, date). Use for rulebook explanations, merchant policy text, and reviewed past case narratives. Never use it for order facts.

Case history: reviewed outcomes (case summary, evidence used, decision, outcome, human notes). Used to calibrate decisions, for example win rate by category, not as free-text advice.

### 5. Decision logic

Fight only when expected value is positive:

```
expected_value = P(win) * disputed_amount - cost_to_fight
```

- P(win) starts as a rule-based estimate from evidence completeness and category, later calibrated from case history.
- cost_to_fight includes any representment fee plus an assumed handling cost. Make these configurable.
- Escalate to a human when any of the following is true: amount above a threshold, required evidence missing, signs of conflicting evidence, response deadline near, or confidence below a threshold.
- Thresholds are configuration, not code. They are product decisions to document and tune.

### 6. Human review
Simple UI (Streamlit or Gradio) showing: dispute summary, what evidence was found and missing, the decision and rationale, the drafted response. Reviewer actions: approve, edit, escalate, or accept loss. Capture the reviewer's change as data (override rate is a key metric).

### 7. Outcome loop
After review and (simulated) submission, record the outcome. Only reviewed records enter case history. Simulated outcomes should be generated from rules (documented), not from model opinion.

## Synthetic data

Generate a store dataset: customers, products, orders, shipping events, support logs, refunds. Then generate disputes with known ground truth.

Requirements:
- Derive correct answers from explicit rules (evidence present or absent), not from a model's judgment.
- Cover each category with strong-evidence, weak-evidence, and conflicting-evidence cases, plus edge cases (late deadline, partial refund already issued, high value, repeat disputer).
- A stronger model may help generate narrative text (emails, chat logs), but labels come from the rule-based generator.
- Hand-check a sample of 30-50 cases. Hand-write a set of tricky edge cases.
- Document how the data was made. Disclose that it is synthetic.

## Evals

### Dimensions

| Dimension | Check | Method |
|---|---|---|
| Reason code and category classification | Matches ground truth | Deterministic assertion |
| Tool use | Called the needed tools, avoided unneeded ones | Deterministic or DeepEval tool correctness |
| Evidence completeness | Correct lists of present and missing items | Deterministic comparison to labels |
| Fight / accept / escalate decision | Matches expected decision | Deterministic assertion |
| No fabrication | Every order ID, amount, date, tracking number, and quoted fact in the draft appears in tool outputs | Deterministic trace check, plus LLM judge for softer claims |
| Draft quality | Addresses the category's requirements, clear, within format | Custom LLM-judge rubric (G-Eval style) |
| Escalation | Weak and high-value cases flagged | Deterministic |
| Cost and latency | Per case | Logged |

### Tooling
Use DeepEval (pytest-style) as the harness. Use its agent metrics where they fit, and write custom deterministic checks for classification, decision, and fabrication. Do not rely on judge scores alone.

### Judge calibration
Hand-label 30-50 cases for draft quality. Report how often the judge agrees with the hand labels. Adjust rubrics until agreement is acceptable. Use a different or stronger model as judge than the agent uses. Report the agreement number in the writeup.

### Separation
Eval cases live in their own directory and are never loaded into case history or RAG.

## Versions to compare (ablations)

| Version | Description |
|---|---|
| V0 | Single prompt, no tools. All context pasted in. |
| V1 | Agent with tools and rules table |
| V2 | V1 plus RAG and case-history calibration |
| V3 | V2 plus a critic step that checks the draft against requirements before human review |
| V4 (optional) | Same workflow ported to LangGraph |

For each version report: scores on every eval dimension, cost per case, latency, and failure examples. A version that adds complexity without measurable gain should be reported as such.

## Metrics for the writeup

- Eval scores by dimension and version
- Simulated win rate by category
- Human override rate
- Escalation rate and escalation precision
- Estimated time saved per case (state the assumption)
- Cost per case and latency
- Top failure modes with examples

## Guardrails

- Never fabricate evidence. If something is missing, say it is missing.
- Flag any case with less than a configurable number of hours to the deadline.
- Redact or mask payment and personal data in prompts, logs, and drafts (even synthetic).
- Refuse to submit without review in v1.
- Log every tool call and decision for audit.

## Suggested stack

| Layer | Choice |
|---|---|
| Model | Anthropic API with tool use, model name from environment |
| Orchestration | Plain Python loop first |
| Backend mocks | FastAPI |
| Structured data | SQLite |
| RAG | Chroma (or pgvector) |
| Review UI | Streamlit or Gradio |
| Evals | pytest with DeepEval, custom checks |
| Tracing | JSON logs, or Langfuse |
| Hosting (demo) | Hugging Face Spaces, Replit, or similar |

## Suggested repo layout

```
dispute-agent/
  README.md
  PROJECT_BRIEF.md
  src/
    agent/           # pipeline, prompts, decision logic
    tools/           # tool functions wrapping the backend
    backend/         # FastAPI mock services and SQLite
    knowledge/       # rules table, RAG ingestion and retrieval
    review_ui/
  data/
    synthetic/       # generated store data
    rules/           # rules table source files
  evals/
    cases/           # ground-truth cases (kept separate)
    metrics/         # custom deterministic checks and judge rubrics
    results/         # per-version results with cost and latency
  docs/
    decisions.md     # product decisions and trade-offs
    writeup.md
```

## Build order

Each step ends with a measured result. Report numbers before continuing.

1. Synthetic backend and data generator, plus the rules table. Done when: dispute cases with rule-derived labels exist and a sample has been hand-checked.
2. V0 baseline (single prompt). Done when: scored on the full eval suite.
3. Add tools and the rules table (V1). Done when: re-scored, with deltas on every dimension.
4. Add decision logic and escalation rules. Done when: decision and escalation scores reported, thresholds documented.
5. Add the review UI and guardrails. Done when: fabrication check passes on all eval cases, or failures are documented.
6. Add RAG and case history (V2), then the critic step (V3). Done when: ablation table complete.
7. Writeup and demo. Done when: docs/writeup.md covers problem, users, approach, trade-offs, results, failures, and next steps.

## Writeup outline

1. Problem and user (who handles disputes, what it costs them)
2. What the agent does and does not do
3. Architecture and key design decisions (why order data is a tool, why RAG only for text, why human review)
4. Eval design and how scores were validated against human labels
5. Results by version, including cost and latency
6. Failure analysis
7. Product decisions: thresholds, escalation, review experience
8. What I would do next with real data

## Open decisions to confirm with the project owner

- Which dispute categories to include first (recommended: item not received, fraud, not as described)
- Whether to build the LangGraph port (V4)
- Judge model choice
- Cost and fee assumptions used in the decision logic
