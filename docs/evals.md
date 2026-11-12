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

## Judge calibration

### V0 result (40 letters, graded blind by the project owner in Braintrust, 2026-11-12)

| | Judge pass | Judge fail |
|---|---|---|
| Human pass | 18 | 20 |
| Human fail | 0 | 2 |

Pass agreement 0.50, Cohen's kappa 0.08, mean absolute per-criterion difference 0.56.
Human pass rate 95%, judge 45%. **The judge is not calibrated; V0 draft-quality numbers stay
labelled "uncalibrated".**

All 20 disagreements go one way (human pass, judge fail). Checked against the records they
split in two:
- **Judge too strict on wording** (e.g. GEN-105, GEN-109, GEN-110, GEN-137, HW-06, HW-09):
  "accepted the return policy *at checkout*", "dispatch photo *of item condition*", "F29,
  card-not-present fraud". The pass rule fails a letter on any unsupported claim, however minor.
- **Real errors the human grade missed** (HW-02, HW-03, HW-14, HW-15, GEN-075, GEN-083,
  GEN-086, GEN-104, GEN-115): a letter that contradicts the support log, an invented "pending
  internal review", account ages stated "at order time" that are really ages at lookup time.
  Claim-by-claim checking ("can I find it?") misses these; the check that catches them is "does
  anything in the records contradict it?"

So neither grader alone is the reference.

### Judge rubric v2: fail only on material problems (2026-11-12)

`evals/metrics/judge.py` (`RUBRIC_VERSION = "v2-material"`) now records every problem with a
severity. Material: contradicts the records, invents a fact or process, a wrong number/date/ID
(including an age computed for the wrong point in time), implies missing evidence exists, claims
what a photo or document shows, exposes masked data. Minor: harmless wording around a recorded
fact, a reason code's standard name, a reasonable reading of an empty record. A letter passes when
every criterion is at least 4 and no problem is material. Re-run on the same 40 letters
(`judge_v2.jsonl`, $1.42):

| | v1 judge | v2 judge |
|---|---|---|
| Letters passed | 18 / 40 | 25 / 40 |
| Agreement with human pass/fail | 0.50 | 0.625 |
| Cohen's kappa vs human | 0.08 | 0.03 |

Kappa stays near zero because the human passed 38 of 40 letters, including letters with verified
errors, so agreement with the human labels is not a usable target on its own. Against the errors
verified in the records, v2 behaves as intended: it still fails 8 of the 9 letters with
contradictions, invented processes or wrong numbers (misses HW-15), and now passes letters failed
only on wording (GEN-015, GEN-025, GEN-105, GEN-118, GEN-137). It also found real problems
missed earlier: an internal reviewer note left in the issuer letter (HW-06) and a fifth
account-age error (HW-09).

### Adjudicated labels (2026-11-12)

The 15 letters where the human grade and the v2 judge disagreed were settled by the project owner
in Braintrust (`v0-judge-adjudication`), with both views and the records shown. Combined with the
25 letters where they already agreed, that gives gold labels for all 40 letters
(`evals/results/v0/judge_gold_labels.csv`).

Settled: judge right 12, original human grade right 3 (GEN-104, GEN-110, GEN-115).
Gold pass rate 70%.

| Grader vs gold (n = 40) | Agreement | Kappa | Errors missed (passed a bad letter) | Good letters failed |
|---|---|---|---|---|
| Human, first pass | 0.70 | 0.06 | 11 | 1 |
| Judge v1 (any unsupported claim fails) | 0.75 | 0.52 | 0 | 10 |
| **Judge v2 (material problems only)** | **0.925** | **0.83** | **0** | **3** |

Judge v2 clears the 0.6 kappa bar and misses no failing letter; its 3 errors are over-strict
(two "dispatch photo of item condition" descriptions the owner ruled minor, and one letter failed
on a 3 for addresses_requirements). **Status: provisionally calibrated.** Two biases make this
optimistic: the rubric examples were written after reading these letters, and the 25 agreed
letters count toward gold because the human and v2 agreed on them. Confirm on fresh V1 letters
graded blind.

Owner rulings recorded during adjudication: "prepaid return label" when the message only says
"return label attached" is **material** (adds a fact about who pays); describing a dispatch photo
as showing "item condition" when only its existence is recorded is **minor**.

### Judge rubric v3 (2026-11-12)

Encodes the owner's ruling that calling a recorded dispatch photo a photo "of the item's condition"
is minor (`judge_v3.jsonl`, $1.41). Against the 40 gold labels: agreement 0.875, kappa 0.70,
3 failing letters passed, 2 good letters failed (v2: 0.925, 0.83, 0, 3). GEN-110 now passes as
intended, but three letters flipped the wrong way:
- **HW-09, GEN-029:** an account age measured at the records-pull date was rated *minor* when the
  letter does not say "at order time" (still *material* where it does: HW-03, GEN-075/083/086).
- **GEN-029, HW-06:** an internal "note for reviewer" inside the issuer letter was rated *minor*
  (v2 rated it material; the owner agreed in adjudication).
- **GEN-107:** passes under the photo ruling; the human failed it on clarity and format.

Lesson: rules the rubric only implies are applied inconsistently between runs. Rules that are
clear-cut belong in code or in the data, not in the judge's judgement.

### Concession check and judge rubric v4 (2026-11-12)

Owner ruling: a note to the internal reviewer that flags a gap is acceptable (every draft is
reviewed); a note that concedes or undercuts the letter is material. `evals/metrics/letter_checks.py`
detects both deterministically and `score.py` reports them: in V0, 14 of 162 letters contain a
reviewer note and 1 a concession (HW-06, "recommend accepting this dispute ... instead of contesting").

Rubric v4 states the owner's rulings outright (account age measured at any date other than the
order date is material, however worded; gap notes minor, concessions material). Two identical v4
runs on the 40 letters (`judge_v4.jsonl`, `judge_v4b.jsonl`, $2.79):
- **Run-to-run stability: 0 of 40 pass/fail flips; mean per-criterion score difference 0.14.**
- Against gold: agreement 0.825, kappa 0.61, 2 failing letters passed (GEN-107 photo ruling vs
  the human's clarity/format fail; GEN-109 "prepaid" rated minor, against the owner's ruling),
  5 good letters failed.
- 3 of those 5 (GEN-034, GEN-055, GEN-092) are account ages measured at the check date that both
  the human and v2 missed: v4 applies the ruling, the gold labels predate it. Pending owner review.

Account age measured at the wrong date now appears in 9 of the 40 letters. Fixing the tool so it
returns age at order time (V1) removes the whole class of error.

Caveats: the rubric's examples were written after reading these 40 letters, so these numbers are
optimistic. Two severity calls are product decisions still open: describing what a dispatch photo
shows when only its existence is recorded (GEN-107, GEN-110: rubric says material), and calling a
return label "prepaid" (GEN-109). A clean measurement needs fresh letters (V1) graded blind,
with disagreements adjudicated.

**Product finding from calibration:** `get_customer_history.account_age_days` is computed at
lookup time, not order time (`src/backend/repository.py`), and the agent reads it as age at
order time (4 of 40 letters). The "established account" evidence is defined at order time, so
the tool should return that value. Fix in V1.

### How to run it

The judge is not trusted until calibrated. After a run:
```bash
python -m evals.judge_calibration sheet --version v0 --n 40   # CSV without the judge's verdicts
# a human fills human_pass (1/0) and per-criterion scores
python -m evals.judge_calibration agree --version v0          # pass agreement, Cohen's kappa
```
Draft-quality numbers are reported as "uncalibrated" until this is done.

## Braintrust

`python -m evals.braintrust_sync upload --version <v>` pushes a version's stored results to the
Braintrust project `DisputeAgent` as experiment `<v>`, with every deterministic score (0-1) and the
judge's scores, so versions can be compared case by case. It uploads results only; no model calls.

Judge calibration runs through Braintrust's review screen:
```bash
python -m evals.braintrust_sync calibration-upload --version v0   # blind set: 40 letters, no judge grades
# a human grades human_pass and human_<criterion> (1-5) in the review screen
python -m evals.braintrust_sync calibration-pull --version v0     # grades -> judge_calibration.csv -> agreement
```
The sample is the same as `evals.judge_calibration sheet` (fight/escalate letters, seed 11).

## V0 (baseline)

One structured-output call. No tools, no rules table: every record the tools would return is
pasted into the prompt. The prompt carries the merchant policy (rendered from
`config/decision.toml`), grounding rules, and the evidence vocabulary (IDs and descriptions,
but not which items each network/category requires). V0 must infer the requirements itself.
That gap is what V1's rules table is meant to close, so the V0 to V1 delta on evidence
completeness is the clearest test of the rules table.

Settings: `config/agent.toml` (effort `medium`, 16k max tokens). Server-side refusal fallback is
enabled; the served model is logged per case, so a fallback would show up in `served_models`.
