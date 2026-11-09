# Synthetic data: how it was made

**Everything in this repository is synthetic.** No real customers, card numbers, orders, or
employer data. Names come from small made-up lists ("Avery Testwood"), emails use
`example.com`, IPs come from the RFC 5737 documentation ranges, and cards are stored as
brand + random last 4 only. Tool outputs mask these further (see "Masking" below).

## Pipeline

```
src/backend/generator.py      scenario specs  ->  SQLite records (no labels)
evals/labeling/labeler.py     SQLite records + rules table + config/decision.toml  ->  labels
evals/labeling/build_cases.py runs both, writes evals/cases/cases.jsonl
```

Rebuild everything (deterministic, seed `20261109`, simulation clock pinned to
`2026-10-15T12:00:00Z`):

```bash
python -m evals.labeling.build_cases
```

`data/synthetic/store.db` is gitignored and rebuilt by that command. The test suite rebuilds
from scratch and asserts the result matches the committed `cases.jsonl` byte for byte.

### Why labels come from records, not from scenario intent

The generator is told "build a weak fraud case". It does **not** write down "this should be
escalated". The labeler then reads the stored records and applies the rules. Tests compare
scenario intent with the derived label, so a generator bug shows up as a mismatch and doesn't
quietly turn into a wrong label. This caught one real bug during the build: prior disputes were
placed up to 390 days back, outside the 365-day repeat-disputer window. The labeler correctly
said "not a repeat disputer", and the generator was fixed.

The one input that can't be re-derived from the DB is the true **category**. For Mastercard
4853 the processor only says `general`, and the category lives in the issuer's free text. The
generator supplies it.

## Store dataset

| Table | Rows |
|---|---|
| customers | 462 |
| orders / shipments | 1,101 |
| tracking_events | 5,457 |
| support_messages | 2,384 |
| refunds | 59 |
| returns | 19 |
| disputes (162 open eval cases + 32 closed historical) | 194 |

About 300 background customers with ordinary order history make the DB look like a store,
not a test fixture. Each eval dispute gets its **own fresh customer** with a controlled
history, so background noise can't change a label and two eval cases can't contaminate each
other's customer history (enforced by a test).

## Eval cases (`evals/cases/cases.jsonl`)

162 cases: 147 generated + 15 hand-written.

| Category | fight | accept | escalate | total |
|---|---|---|---|---|
| item_not_received | 18 | 13 | 25 | 56 |
| fraud | 16 | 13 | 24 | 53 |
| not_as_described | 17 | 10 | 26 | 53 |
| **total** | **51** | **36** | **75** | **162** |

Networks: Visa 64, Mastercard 55 (40 of them code 4853, which needs category inference from
text), Amex 43. 46 disputes have an empty issuer message.

Scenarios per category: strong (12), weak (12), conflicting (8), deadline near (2), deadline
passed (1), partial refund with full-amount dispute (2), partial refund with consistent amount
(1), full refund already issued (2), high value (3), repeat disputer (2-3), low amount (2), and
merchant at fault (3 INR: lost / returned to sender; 2 NAD: return received, no refund).

**This mix is deliberately harder than production.** 46% (75/162) of eval cases should escalate. Real
traffic would be dominated by clean cases. Escalation *rate* on this set is not a forecast.
Escalation *precision and recall* are what to read from it.

Each case holds:
- `dispute`: the webhook payload the agent receives
- `labels`: category, required/strong evidence present and missing, conflicts, merchant-fault
  flags, refund totals, hours remaining, P(win), EV, escalation triggers, decision + reason,
  required and unneeded tools

### Hand-written edge cases

`evals/labeling/handwritten.py` (records) and `evals/cases/handwritten_expectations.json`
(answers). The answers were written by hand **before** running the labeler. 15/15 match.
They cover: Mastercard 4853 in both categories, threshold boundaries ($749.99 vs $750.00;
exactly 72 h vs the "<72 h" rule), deadline passed by 1 h, a CE 3.0-style "AVS failed but
3 prior orders from the same device", full refund then lost package, high-value merchant
fault, a conflict too small to escalate, a repeat disputer too small to fight (escalated anyway, by owner decision), 50% refund
with a full-amount dispute, shipping to a non-billing address, and a return still in transit.

## Narrative text

Support messages and issuer messages are **template-based** (2-4 phrasings each), not
model-generated. That's cheaper, deterministic, and enough for step 1. Items that depend on
reading text (customer acknowledged receipt, merchant offered remedy, merchant admitted
defect or misdelivery) are labeled from hidden generator tags in `_gen_message_labels`. That
table is never read by the repository or API (enforced by tests). The agent has to read the
text.

Known limitation: with few templates, an agent could pattern-match phrasing. If the scores on
text-dependent items look suspiciously perfect, the next step is model-written message
variants (the brief allows this; labels would still come from the tags).

## Masking (tool outputs)

| Field | Stored | Returned by tools |
|---|---|---|
| Address | `1234 Maple St, Springfield, ST 01234` | `**** Maple St, Springfield, ST 0****` plus `shipping_matches_billing` |
| Email | `avery.testwood.0301@example.com` | `a***@example.com` |
| IP | `192.0.2.17` | `ip_` + 10-char SHA-256 token (comparable across orders) |
| Card | brand + last 4 | `****1234` |

## Hand-check

`docs/handcheck_sample.md` has 40 cases stratified by category x decision, rendered from
**tool outputs only**. That tests both label correctness and that a reader can reach the
label from what the agent will see.

**Status: model-reviewed, human pass still pending.** Claude reviewed all 40:
- 40/40 labels consistent with the rules as written.
- 1 data bug found and fixed: "where is my order" messages were dated after the delivery
  scan in delivered cases. The labels were unaffected, but the timeline was incoherent. Fixed,
  with a timeline test added.
- 1 rule observation (not a bug): GEN-116 escalates with EV = $1.25. See
  `docs/decisions.md`, open question 3.

The brief asks for a human hand-check. Tick the boxes in `docs/handcheck_sample.md` and record
the agreement rate here.
