# Eval results: v1

Synthetic data. Labels are rule-derived (see docs/data.md).

| Metric | Value |
|---|---|
| cases scored / errors | 162 / 0 |
| category accuracy | 1.0 |
| reason code accuracy | 1.0 |
| tool use: required recall | n/a (no tools) |
| tool use: unneeded calls / case | n/a (no tools) |
| evidence: exact required lists | 1.0 |
| evidence: required set correct | 1.0 |
| evidence: false-missing rate | 0.0 |
| evidence: false-present rate | 0.0 |
| evidence: strong-evidence F1 | 1.0 |
| decision accuracy | 1.0 |
| wrongful auto-accepts (count / $) | 0 / $0.00 |
| fought when should escalate | 0 |
| escalation precision | 1.0 |
| escalation recall | 1.0 |
| escalation rate (pred / expected) | 0.463 / 0.463 |
| drafts with unsupported tokens | 36 (0.2222) |
| letters with a reviewer note / a concession | 0 / 0 |
| draft quality pass rate (judge calibrated, kappa 0.73) | 0.8492 |
| cost per case (USD) | 0.01825 |
| total cost (USD) | 2.9563 |
| latency p50 / p95 (s) | 11.01 / 15.38 |

## Decision confusion (expected -> predicted)

| pair | count |
|---|---|
| accept->accept | 36 |
| escalate->escalate | 75 |
| fight->fight | 51 |

## Decision accuracy by category

- fraud: 1.0
- item_not_received: 1.0
- not_as_described: 1.0

## Failure examples

### classification
- none

### false_missing
- none

### false_present
- none

### decision
- none

### fabrication
- `{"amounts": ["$35"], "case_id": "GEN-013"}`
- `{"amounts": ["$35"], "case_id": "GEN-014"}`
- `{"amounts": ["$35"], "case_id": "GEN-020"}`
- `{"amounts": ["$35"], "case_id": "GEN-021"}`
- `{"amounts": ["$35"], "case_id": "GEN-022"}`
- `{"amounts": ["$35"], "case_id": "GEN-024"}`
- `{"amounts": ["$35", "$349.30"], "case_id": "GEN-035"}`
- `{"amounts": ["$35"], "case_id": "GEN-046"}`

### errors
- none
