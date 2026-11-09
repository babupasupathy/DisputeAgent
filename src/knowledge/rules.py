"""Rules table: exact lookup keyed by (network, reason_code[, category]).

The table is a simplified summary of public documentation. It is NOT authoritative;
see the `verification` column of data/rules/rules_table.csv.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache

from src.config import DATA_DIR

RULES_PATH = DATA_DIR / "rules" / "rules_table.csv"
CATEGORIES = ("item_not_received", "fraud", "not_as_described")


@dataclass(frozen=True)
class Rule:
    network: str
    reason_code: str
    reason_name: str
    category: str
    required_evidence: tuple[str, ...]
    strong_evidence: tuple[str, ...]
    response_deadline_days: int
    notes: str
    source: str
    source_date: str
    checked_on: str
    verification: str


@lru_cache(maxsize=1)
def load_rules() -> tuple[Rule, ...]:
    rows = []
    with open(RULES_PATH, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(
                Rule(
                    network=r["network"],
                    reason_code=r["reason_code"],
                    reason_name=r["reason_name"],
                    category=r["category"],
                    required_evidence=tuple(x for x in r["required_evidence"].split("|") if x),
                    strong_evidence=tuple(x for x in r["strong_evidence"].split("|") if x),
                    response_deadline_days=int(r["response_deadline_days"]),
                    notes=r["notes"],
                    source=r["source"],
                    source_date=r["source_date"],
                    checked_on=r["checked_on"],
                    verification=r["verification"],
                )
            )
    return tuple(rows)


def rules_for(network: str, reason_code: str) -> list[Rule]:
    """All rows for a network + reason code. Some codes (Mastercard 4853) map to >1 category."""
    return [r for r in load_rules() if r.network == network and r.reason_code == reason_code]


def lookup(network: str, reason_code: str, category: str | None = None) -> Rule:
    rows = rules_for(network, reason_code)
    if category is not None:
        rows = [r for r in rows if r.category == category]
    if len(rows) != 1:
        raise LookupError(
            f"expected exactly one rule for {network}/{reason_code}/{category}, found {len(rows)}"
        )
    return rows[0]


def codes_for(network: str, category: str) -> list[str]:
    return [r.reason_code for r in load_rules() if r.network == network and r.category == category]
