# Eval results: v0

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
| evidence: false-missing rate | 0.0129 |
| evidence: false-present rate | 0.0714 |
| evidence: strong-evidence F1 | 0.4225 |
| decision accuracy | 0.7593 |
| wrongful auto-accepts (count / $) | 14 / $5377.00 |
| fought when should escalate | 2 |
| escalation precision | 0.7229 |
| escalation recall | 0.8 |
| escalation rate (pred / expected) | 0.5123 / 0.463 |
| drafts with unsupported tokens | 7 (0.0432) |
| letters with a reviewer note / a concession | 14 / 1 |
| draft quality pass rate (judge calibrated, kappa 0.73) | 0.6174 |
| cost per case (USD) | 0.02339 |
| total cost (USD) | 3.7884 |
| latency p50 / p95 (s) | 10.55 / 16.9 |

## Decision confusion (expected -> predicted)

| pair | count |
|---|---|
| accept->accept | 33 |
| accept->escalate | 3 |
| escalate->accept | 13 |
| escalate->escalate | 60 |
| escalate->fight | 2 |
| fight->accept | 1 |
| fight->escalate | 20 |
| fight->fight | 30 |

## Decision accuracy by category

- fraud: 0.8113
- item_not_received: 0.8571
- not_as_described: 0.6038

## Failure examples

### classification
- none

### false_missing
- `{"case_id": "GEN-061", "items": ["delivery_confirmation"]}`
- `{"case_id": "GEN-079", "items": ["delivery_confirmation"]}`
- `{"case_id": "GEN-080", "items": ["delivery_confirmation"]}`
- `{"case_id": "GEN-093", "items": ["delivery_confirmation"]}`
- `{"case_id": "GEN-094", "items": ["delivery_confirmation"]}`

### false_present
- `{"case_id": "GEN-013", "items": ["address_match"]}`
- `{"case_id": "GEN-014", "items": ["address_match"]}`
- `{"case_id": "GEN-022", "items": ["address_match"]}`
- `{"case_id": "GEN-049", "items": ["address_match"]}`
- `{"case_id": "GEN-069", "items": ["delivered_to_billing_address"]}`
- `{"case_id": "GEN-070", "items": ["delivered_to_billing_address"]}`
- `{"case_id": "HW-05", "items": ["address_match"]}`

### decision
- `{"amount": 145.0, "case_id": "GEN-005", "expected": "fight", "predicted": "escalate", "scenario": "strong"}`
- `{"amount": 345.0, "case_id": "GEN-006", "expected": "fight", "predicted": "escalate", "scenario": "strong"}`
- `{"amount": 345.0, "case_id": "GEN-026", "expected": "escalate", "predicted": "accept", "scenario": "conflicting"}`
- `{"amount": 395.0, "case_id": "GEN-028", "expected": "escalate", "predicted": "accept", "scenario": "conflicting"}`
- `{"amount": 345.0, "case_id": "GEN-030", "expected": "escalate", "predicted": "accept", "scenario": "conflicting"}`
- `{"amount": 345.0, "case_id": "GEN-032", "expected": "escalate", "predicted": "accept", "scenario": "conflicting"}`
- `{"amount": 345.0, "case_id": "GEN-037", "expected": "escalate", "predicted": "fight", "scenario": "partial_refund_mismatch"}`
- `{"amount": 145.0, "case_id": "GEN-051", "expected": "fight", "predicted": "escalate", "scenario": "strong"}`
- `{"amount": 279.0, "case_id": "GEN-052", "expected": "fight", "predicted": "escalate", "scenario": "strong"}`
- `{"amount": 112.0, "case_id": "GEN-053", "expected": "fight", "predicted": "escalate", "scenario": "strong"}`
- `{"amount": 345.0, "case_id": "GEN-056", "expected": "fight", "predicted": "escalate", "scenario": "strong"}`
- `{"amount": 549.0, "case_id": "GEN-058", "expected": "fight", "predicted": "escalate", "scenario": "strong"}`

### fabrication
- `{"amounts": ["$35.00"], "case_id": "GEN-046"}`
- `{"amounts": ["$35.00"], "case_id": "GEN-047"}`
- `{"amounts": ["$35.00"], "case_id": "GEN-064"}`
- `{"amounts": ["$35.00"], "case_id": "GEN-097"}`
- `{"amounts": ["$35.00"], "case_id": "GEN-098"}`
- `{"amounts": ["$35.00"], "case_id": "GEN-144"}`
- `{"amounts": ["$35.00"], "case_id": "HW-11"}`

### errors
- none
