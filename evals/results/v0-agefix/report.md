# Eval results: v0-agefix

Synthetic data. Labels are rule-derived (see docs/data.md).

| Metric | Value |
|---|---|
| cases scored / errors | 162 / 0 |
| category accuracy | 1.0 |
| reason code accuracy | 1.0 |
| tool use: required recall | n/a (no tools) |
| tool use: unneeded calls / case | n/a (no tools) |
| evidence: exact required lists | 0.0185 |
| evidence: required set correct | 0.0185 |
| evidence: false-missing rate | 0.0026 |
| evidence: false-present rate | 0.0408 |
| evidence: strong-evidence F1 | 0.4243 |
| decision accuracy | 0.7654 |
| wrongful auto-accepts (count / $) | 13 / $4828.00 |
| fought when should escalate | 1 |
| escalation precision | 0.7209 |
| escalation recall | 0.8267 |
| escalation rate (pred / expected) | 0.5309 / 0.463 |
| drafts with unsupported tokens | 7 (0.0432) |
| letters with a reviewer note / a concession | 8 / 0 |
| draft quality pass rate (judge calibrated, kappa 0.73) | 0.9145 |
| cost per case (USD) | 0.02372 |
| total cost (USD) | 3.8432 |
| latency p50 / p95 (s) | 10.88 / 17.41 |

## Decision confusion (expected -> predicted)

| pair | count |
|---|---|
| accept->accept | 32 |
| accept->escalate | 4 |
| escalate->accept | 12 |
| escalate->escalate | 62 |
| escalate->fight | 1 |
| fight->accept | 1 |
| fight->escalate | 20 |
| fight->fight | 30 |

## Decision accuracy by category

- fraud: 0.8491
- item_not_received: 0.8393
- not_as_described: 0.6038

## Failure examples

### classification
- none

### false_missing
- `{"case_id": "GEN-062", "items": ["delivery_confirmation"]}`

### false_present
- `{"case_id": "GEN-014", "items": ["address_match"]}`
- `{"case_id": "GEN-115", "items": ["return_policy_accepted"]}`
- `{"case_id": "GEN-121", "items": ["product_listing"]}`
- `{"case_id": "HW-05", "items": ["address_match"]}`

### decision
- `{"amount": 395.0, "case_id": "GEN-010", "expected": "fight", "predicted": "escalate", "scenario": "strong"}`
- `{"amount": 395.0, "case_id": "GEN-014", "expected": "accept", "predicted": "escalate", "scenario": "weak"}`
- `{"amount": 345.0, "case_id": "GEN-026", "expected": "escalate", "predicted": "accept", "scenario": "conflicting"}`
- `{"amount": 395.0, "case_id": "GEN-028", "expected": "escalate", "predicted": "accept", "scenario": "conflicting"}`
- `{"amount": 345.0, "case_id": "GEN-029", "expected": "escalate", "predicted": "accept", "scenario": "conflicting"}`
- `{"amount": 345.0, "case_id": "GEN-030", "expected": "escalate", "predicted": "accept", "scenario": "conflicting"}`
- `{"amount": 395.0, "case_id": "GEN-036", "expected": "escalate", "predicted": "fight", "scenario": "partial_refund_mismatch"}`
- `{"amount": 145.0, "case_id": "GEN-051", "expected": "fight", "predicted": "escalate", "scenario": "strong"}`
- `{"amount": 279.0, "case_id": "GEN-052", "expected": "fight", "predicted": "escalate", "scenario": "strong"}`
- `{"amount": 112.0, "case_id": "GEN-053", "expected": "fight", "predicted": "escalate", "scenario": "strong"}`
- `{"amount": 345.0, "case_id": "GEN-056", "expected": "fight", "predicted": "escalate", "scenario": "strong"}`
- `{"amount": 549.0, "case_id": "GEN-058", "expected": "fight", "predicted": "escalate", "scenario": "strong"}`

### fabrication
- `{"amounts": ["$35.00"], "case_id": "GEN-046"}`
- `{"amounts": ["$35.00"], "case_id": "GEN-047"}`
- `{"amounts": ["$35.00"], "case_id": "GEN-097"}`
- `{"amounts": ["$35.00"], "case_id": "GEN-098"}`
- `{"amounts": ["$35.00"], "case_id": "GEN-119"}`
- `{"amounts": ["$35.00"], "case_id": "GEN-144"}`
- `{"amounts": ["$35.00"], "case_id": "HW-11"}`

### errors
- none
