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
| representment_fee | $15 | PROVISIONAL |
| handling_cost | $20 (~20 min analyst time at ~$60/h) | PROVISIONAL |
| high_value_amount | $750 (>=) | PROVISIONAL |
| deadline_buffer_hours | 72 (<) | PROVISIONAL |
| repeat_disputer_min_prior | 2 disputes in 365 days | PROVISIONAL |
| processor_buffer_days | 7 (merchant window = network window - 7) | assumption |

**Precedence** (first match wins):
1. Deadline passed -> **accept** (nothing can be submitted)
2. Amount >= high-value threshold -> **escalate** (even when the merchant is at fault: a human
   should sign off on any large loss)
3. Merchant at fault (shipment lost or returned to sender; return received but not refunded),
   unless already fully refunded -> **accept**
4. EV <= 0 -> **accept** (not worth fighting, and not worth a human's time)
5. Any trigger (deadline near, repeat disputer, conflicting evidence, missing required
   evidence) -> **escalate**
6. Otherwise -> **fight**

When a full refund was issued before the dispute, the defense is the credit itself, so missing
evidence and conflicts don't trigger escalation for that case.

**Interpretation of the brief.** The brief says to escalate when "required evidence is missing".
Applied literally, every weak case would escalate and nothing would ever be accepted. Rule 4
puts EV first: a $40 dispute with no tracking is accepted, not sent to a person. Rule 2 is the
deliberate exception, because high-value losses always get human eyes.

"Confidence below a threshold" is **not** in the ground truth, because confidence belongs to the
agent, not to the case. It will be an agent-side trigger in step 4, and its effect will be
measured as escalation precision.

## Open questions for the project owner

1. Cost assumptions: $15 fee + $20 handling. Many processors charge the dispute fee whether or
   not you respond, which would make the fee sunk and lower cost_to_fight to the handling cost.
2. Should a repeat disputer with negative EV escalate anyway, to flag the customer for blocking?
   Currently it is accepted (HW-12).
3. Should escalation require a minimum EV margin? GEN-116 sends a human a case worth $1.25 in
   expected value.
4. Judge model and whether to build V4 (LangGraph). Not needed until step 2.
