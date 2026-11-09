import csv

import pytest

from src.config import DATA_DIR
from src.knowledge.rules import CATEGORIES, load_rules, lookup, rules_for


def test_every_row_has_provenance():
    for r in load_rules():
        assert r.source and r.source_date and r.checked_on and r.verification, r
        assert "VERIFY" in r.verification  # nothing is marked authoritative yet


def test_evidence_ids_are_defined():
    with open(DATA_DIR / "rules/evidence_definitions.csv") as f:
        defined = {row["evidence_id"] for row in csv.DictReader(f)}
    for r in load_rules():
        assert set(r.required_evidence) | set(r.strong_evidence) <= defined


def test_each_network_covers_each_category():
    for net in ("visa", "mastercard", "amex"):
        cats = {r.category for r in load_rules() if r.network == net}
        assert cats == set(CATEGORIES)


def test_mastercard_4853_is_ambiguous_without_category():
    assert len(rules_for("mastercard", "4853")) == 2
    with pytest.raises(LookupError):
        lookup("mastercard", "4853")
    assert lookup("mastercard", "4853", "not_as_described").category == "not_as_described"
