# Product decisions and trade-offs

Thresholds live in `config/decision.toml`, not in code. Items marked **PROVISIONAL** await
project-owner sign-off.

## Scope

- **Categories: item not received, fraud (card-absent), not as described / defective.**
  These are the brief's recommendation. "Credit not processed" is left out for now, but the
  full-refund and partial-refund edge cases exercise refund handling inside the other three.
  Adding it means a rules row per network, evidence definitions, and a scenario plan.
- **Networks: Visa, Mastercard, Amex.** Mastercard 4853 covers both non-receipt and
  not-as-described, so the rules table allows two rows per code, and the category has to come
  from the issuer message. That's a real classification difficulty, not an invented one.

## Rules table (`data/rules/rules_table.csv`)

Every row has `source`, `source_date`, `checked_on`, and `verification`. All rows are
currently **"Secondary only ... VERIFY"**: reason codes, names, and response windows were
confirmed against search snippets of public Visa / Mastercard / Amex documents and processor
summaries. The evidence lists were not read from primary text, and they are simplified to one
canonical evidence vocabulary (`data/rules/evidence_definitions.csv`) shared across networks.
Treat the table as a plausible model, not as network rules.

## Decision logic (ground truth, `evals/labeling/labeler.py`)

```
P(win) = base[category] * 0.4^(missing required) + 0.07 * (strong present)
         x 0.6 if conflicting;  = 0.9 if a full refund was already issued
EV     = P(win) * disputed_amount - (representment_fee + handling_cost)
```

| Parameter | Value | Status |
|---|---|---|
| base P(win): INR / fraud / NAD | 0.70 / 0.50 / 0.45 | PROVISIONAL, to be calibrated from case history in V2 |
| representment_fee | $15 | confirmed 2026-11-09 |
| handling_cost | $20 (~20 min analyst time at ~$60/h) | confirmed 2026-11-09 |
| high_value_amount | $750 (>=) | confirmed 2026-11-09 |
| deadline_buffer_hours | 72 (<) | confirmed 2026-11-09 |
| repeat_disputer_min_prior | 2 disputes in 365 days | PROVISIONAL (count); always-escalate confirmed 2026-11-09 |
| processor_buffer_days | 7 (merchant window = network window - 7) | assumption |

**Precedence** (first match wins):
1. Deadline passed -> **accept** (nothing can be submitted)
2. Amount >= high-value threshold -> **escalate** (even when the merchant is at fault: a human
   should sign off on any large loss)
3. Repeat disputer (>= 2 prior disputes in 365 days) -> **escalate**, even when EV <= 0, so a
   human can flag the customer (owner decision 2026-11-09)
4. Merchant at fault (shipment lost or returned to sender; return received but not refunded),
   unless already fully refunded -> **accept**
5. EV <= 0 -> **accept** (not worth fighting, and not worth a human's time)
6. Any remaining trigger (deadline near, conflicting evidence, missing required evidence)
   -> **escalate**
7. Otherwise -> **fight**

When a full refund was issued before the dispute, the defense is the credit itself, so missing
evidence and conflicts don't trigger escalation for that case.

**Interpretation of the brief.** The brief says to escalate when "required evidence is missing".
Applied literally, every weak case would escalate and nothing would ever be accepted. Rule 5
puts EV first: a $40 dispute with no tracking is accepted, not sent to a person. Rule 2 is the
deliberate exception, because high-value losses always get human eyes.

"Confidence below a threshold" is **not** in the ground truth, because confidence belongs to the
agent, not to the case. It will be an agent-side trigger in step 4, and its effect will be
measured as escalation precision.

## V1 redefined: decisions in code, the model reads and writes (owner decision 2026-11-12)

The brief's V1 was "agent with tools and rules table": the model chooses which lookups to call and
still makes the decision. V0's evals argue against both halves:
- Decision errors came from the model applying the policy, not from missing data: 20 winnable
  cases escalated because it treated optional evidence as required (required-evidence lists exactly
  right in 2% of cases), and 13 conflicting cases accepted without review.
- 13 of the 15 evidence types are database fields, and P(win), expected value and the 7 rules are
  arithmetic and if-statements. Code does them exactly, for free, and can name the rule that fired.
- Fetching all seven records costs nothing and cannot miss one; letting the model choose adds cost
  and a new way to fail.

So V1 = records fetched in code; rules table, evidence checks, P(win), EV and the decision rules in
code (`src/agent/decide.py`, implementing this document's policy from `config/decision.toml`); the
model does only what needs language: (1) read the issuer note and support messages for the
category of ambiguous codes and four text facts (customer acknowledged receipt, merchant offered a
remedy, merchant acknowledged non-delivery, merchant admitted a defect), each backed by a quoted
message that code verifies; (2) write the letter, for fight and escalate only, from a verified fact
sheet, with notes for the reviewer kept out of the issuer letter. Same model (Sonnet 5.5) as V0, so
the change is the architecture, not the model; Haiku for reading is a later, separate experiment.

The brief's "model chooses the tools" stays an optional experiment, reported against V1 under the
brief's rule that complexity without measured gain is reported as such. V2 (calibration from
reviewed outcomes) and V3 (critic) build on this V1.

Eval caveat: the answer key (`evals/labeling/labeler.py`) implements the same written policy, so
with correct inputs V1's decision code should agree with it by construction. V1's decision accuracy
therefore measures the reading step and the code's fidelity to the policy, not judgment. The
meaningful tests become the text-reading accuracy and fresh, blind-graded letters.

## Open questions for the project owner

Resolved 2026-11-09: categories (3, no "credit not processed"), costs ($15 + $20),
thresholds ($750, 72 h), repeat disputers always escalate (HW-12 now escalates).

Resolved 2026-11-09: expected value comes first (rule 5 before rule 6). Fight only when
EV > 0; a case with EV <= 0 is accepted without review even if evidence is missing. No
minimum-EV margin on escalation: any EV > 0 case with a trigger goes to a person (GEN-116,
EV $1.25, still escalates).

**Consequence for evals.** Under this rule the costly agent error is reporting evidence as
missing when it exists: that lowers P(win), can push EV below zero, and the case is accepted
with no human ever seeing it. The eval suite must therefore report, separately from overall
evidence completeness:
- *false-missing rate*: required items present in the labels but marked missing by the agent
- *wrongful auto-accepts*: cases the agent accepted where the label is fight or escalate, and
  the dollar amount lost on them

Resolved 2026-11-09: agent model Claude Sonnet 5.5, judge model Claude Opus 5.5 (a stronger
model than the agent, as the brief requires). Set via ANTHROPIC_MODEL and JUDGE_MODEL; never in
code. V4 (LangGraph port) is skipped for now.

No open questions.
