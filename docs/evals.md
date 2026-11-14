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

### Frozen judge (2026-11-12)

Owner rulings applied to the gold labels (`judge_gold_overrides.csv`): GEN-034 and GEN-092 fail
(account age measured at the check date, stated with no date, reads as age at order time);
GEN-055 passes (it states "at dispute check", which is accurate). GEN-109 ("prepaid") is a known
judge miss, accepted.

| vs 40 gold labels | Agreement | Kappa | Bad letters passed | Good letters failed |
|---|---|---|---|---|
| Human, first pass | 0.65 | 0.04 | 13 | 1 |
| Judge v1 (any unsupported claim fails) | 0.70 | 0.42 | 2 | 10 |
| Judge v2 (material only) | 0.875 | 0.73 | 2 | 3 |
| **Judge v4 (rulings stated outright) + concession check** | **0.875** | **0.73** | **2** | **3** |

v2 and v4 score the same on this set; v4 is frozen because it encodes the owner's rulings
explicitly and is stable (two identical runs: 0/40 flips). Its known misses: GEN-107 (photo
ruling vs the human's clarity/format fail), GEN-109 ("prepaid"); over-strict on GEN-055,
GEN-104, GEN-115. No further tuning on these 40 letters: every rubric change so far was fitted
to them. Next measurement: fresh V1 letters, graded blind, then adjudicated.

### V0 re-scored with the frozen judge (2026-11-12)

All 115 V0 letters judged with rubric v4 (`judge.jsonl`; the original run is kept as
`judge_v1.jsonl`; $2.54 for the 75 letters not already judged). Calibrated letter pass rate
(judge pass and no concession): **61.7%** (was 55.7% uncalibrated). Grounded is the weakest
criterion (mean 3.91). Of the 44 failing letters, **35 fail only because of the account-age tool
problem**; fixing it would put the pass rate near 92% (estimate, to confirm in V1).

### Experiment: account-age tool fix only (`v0-agefix`, 2026-11-12)

The unchanged V0 agent re-run on all 162 cases with one change: the tools report account age at
order time (`customer_account_age_days_at_order`) and no longer return age measured to the
lookup date. Letters graded with the frozen judge. Agent $3.84, judge $4.02.

| | V0 | v0-agefix |
|---|---|---|
| **Letter pass rate (calibrated judge + concession check)** | **61.7%** (71/115) | **91.5%** (107/117) |
| Letters failing on account age | 38 | **0** |
| Grounded (mean, 1-5) | 3.91 | 4.34 |
| Decision accuracy | 75.9% | 76.5% |
| Wrongful auto-accepts | 14 ($5,377) | 13 ($4,828) |
| Real evidence marked missing | 1.3% | 0.3% |
| Cost per case | $0.0234 | $0.0237 |

A data fix, not a prompt change, removed the largest class of letter error; decisions are
unchanged, as expected, because the fix only changes what letters say about account age. The
pre-run estimate was "about 92%".

Remaining 10 failing letters: claiming the item matched its listing (GEN-104, GEN-132),
"prepaid" return label (GEN-099, GEN-136), asking the issuer to rely on an unconfirmed address
match (GEN-016, GEN-019), a prior order credited with a device/IP match it does not have
(GEN-081), gap disclosures written into the issuer letter (GEN-053), and two concessions inside
the letter (HW-06, HW-12). The deterministic concession check caught neither of those two
concessions ("not recommended", "does not support the merchant"): its phrase list is narrow, so
the judge remains the main defence there.

### V1: decisions in code, model reads and writes; brief now, letter later (2026-11-12)

Design in docs/decisions.md. Three runs, all on the same 162 cases, letters graded with the frozen judge:
- run 1 (`v1-run1`): decisions 162/162; letters 84.9%. Fixed: refund-before-dispute letters ignored the
  refund, letters argued against the merchant's own messages, "listed accurately" claims, accept template
  leaking internal figures, fact checker flagging "$0".
- run 2 (`v1-run2`): fight letters 51/51, escalation letters 60/75; failures were escalations with conflicts or
  missing evidence. Owner decision: brief now, letter later.
- run 3 (`v1`, final):

| | V0 | v0-agefix | **V1** |
|---|---|---|---|
| Decision accuracy | 75.9% | 76.5% | **100%** |
| Wrongful auto-accepts | 14 ($5,377) | 13 ($4,828) | **0** |
| Winnable cases escalated | 20 | 20 | **0** |
| Required evidence exactly right | 1.9% | 1.9% | **100%** |
| Letters proposed up front, passing | 61.7% (115) | 91.5% (117) | **97.4% (76)** |
| Letters flagged by the fact checker | 7 | 7 | **0** |
| Cost per case | $0.0234 | $0.0237 | **$0.0113** |
| Latency p50 / p95 | 10.6 / 16.9 s | 10.9 / 17.4 s | **2.5 / 11.5 s** |

All three Roadmap predictions held: winnable cases escalated 20 -> 0 (target < 5), wrongful auto-accepts
14 -> 0 (target < 3), cost per case -52% (target "roughly halves").

Letter status in V1: 76 drafted up front (51 fight, 25 high-value / deadline / repeat-disputer escalations),
50 brief-only escalations, 36 accepts (template, no model call). The model is not called at all for 16 cases.

On-demand letters (`v1-ondemand`, simulated reviewer contesting every brief-only case with a generic
direction): 38/50 pass (76%). The failures are cases where the merchant's own agent admitted a misdelivery
or defect, AVS failed, or the carrier did not confirm the address. No honest contest letter exists for most
of them; a real reviewer reading the brief would usually accept. So 76% is a stress test, not the expected
production rate, and it argues for a guardrail: warn the reviewer before drafting when the brief shows a
merchant admission.

Caveats: decision accuracy is 100% partly by construction (the decision code implements the same written
policy as the answer key; given the true facts it matches on all 162 cases), so it measures the reading
step, which was right on every case. Letter fixes were developed on these 162 cases. Next measurement:
fresh letters graded blind.

### Blind check of the frozen judge on V1 letters (2026-11-14)

20 V1 letters the rubric was never tuned on, graded blind by the project owner in Braintrust:
15 drafted up front (`v1-judge-calibration`) and 5 drafted on demand after a simulated reviewer chose
to contest (`v1-ondemand-judge-calibration`). Settled labels in `evals/results/v1*/judge_gold_labels.csv`.

| | Up front (15) | On demand (5) | All (20) |
|---|---|---|---|
| Pass/fail agreement, judge vs owner | 13 | 1 | **14 / 20** |
| Bad letters the judge passed | 2 | 4 | **6** |
| Good letters the judge failed | 0 | 0 | **0** |

All six disagreements have one cause, found by the owner: the letter says the carrier delivered to the
order's address (citing `delivered_address_match = true`) while the delivery scan is in a different city.
The judge trusted the flag and never compared it with the scan location. The cause was a data bug: the
generator picked the destination city at random, so 112 of 131 "matched" deliveries were scanned in
another city. Fixed in the generator (labels unchanged, regression test added). On every letter without
that contradiction, the judge and the owner agreed (14 of 14), and the judge failed no good letter.

Lessons: (1) a blind check on fresh letters found a failure mode the 40-letter calibration could not,
because every V0 letter had the same flaw and nobody noticed it then; (2) the judge checks claims against
fields but not fields against each other, so cross-field contradictions are a known judge blind spot;
(3) human grading found three data-quality bugs in this project (account age, reviewer notes in issuer
letters, scan location), all fixed at the source.

### V1 run 4: corrected data and plain-language letters (2026-11-14)

Same V1 code plus two fixes: the scan-location data bug (e1c13ac) and plain-language fact sheets with a
no-field-names rule (0f0542d). Previous runs archived as `v1-run3` / `v1-ondemand-run3` (the letters the
owner graded blind).

| | V1 run 3 | **V1 run 4** |
|---|---|---|
| Decisions correct / wrongful auto-accepts | 162/162 / 0 | **162/162 / 0** |
| Letters with internal field names | 26 | **0** |
| Up-front letters passing, as judged | 97.4% (74/76) | **89.5% (68/76)** |
| Up-front, after removing verified judge false failures | | **96.1% (73/76)** |
| On-demand letters passing, as judged | 76% (38/50) | **68% (34/50)** |
| On-demand, after removing verified judge false failures | | **72% (36/50)** |
| Cost per case | $0.0113 | **$0.0111** |

Judge false failures (7): the new basis line "N earlier delivered, undisputed orders placed 120 to 365
days before this order" was true in every case (verified: each cited order was 130-358 days earlier) but
the judge read it as a wrong claim about the spread of dates (GEN-054, -057, -088, -092, -095; on demand
GEN-076, -082). Fix (192a660): the fact sheet now lists each prior order with its date and exact day count.
Not yet measured: the next run (Haiku reading or messy messages experiment) measures it.

Real up-front failures: a year slip (GEN-056, "2025-09-25" for 2026) and two remedy claims that overstate
the record (HW-06: the customer returned the item and was never refunded; HW-15: implies the offer
conformed to a policy whose terms are not on file). On demand, the remaining failures are the same
categories as before: arguing against the merchant's own admission of misdelivery or defect, AVS failed,
one year slip.

### Admission guardrail for on-demand letters (2026-11-14)

`draft_letter()` no longer drafts a contest letter when the merchant's own agent acknowledged non-delivery
or admitted a defect (verified quote in the support log); it returns a warning instead, and the reviewer must
pass `override_admission=True` to draft anyway. The reviewer brief shows the same warning. Measured on the
stored run 4 on-demand letters (no new model calls; the eval's simulated reviewer overrides so every letter
is still graded): the guardrail would block 12 of 50 cases, 8 of which were failing letters; pass rate on
the letters it lets through is 78.9% (30/38), up from 68% overall. Two of the remaining 8 failures are the
verified "120 to 365 days" judge false failures.

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
Braintrust project `DisputeAgent` as experiment `<v>`, so versions can be compared case by case. It
uploads results only; no model calls. To stay within the free plan's 11,000 scores a month it sends four
scores per case (decision correct, no wrongful auto-accept, escalation correct, judge pass) and puts the
rest in each row's metadata (`other_scores`); `--all-scores` sends everything. The plan limit was hit on
2026-11-14 during the V1 run 4 upload, which left experiment `v1` mixed (86 rows run 4, 76 run 3);
re-upload scheduled for 2026-12-01.

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
