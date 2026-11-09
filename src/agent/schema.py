"""Structured output schema shared by every agent version (V0-V3), so results are comparable."""
from __future__ import annotations

import csv

from src.config import DATA_DIR

CATEGORIES = ["item_not_received", "fraud", "not_as_described"]
DECISIONS = ["fight", "accept", "escalate"]
ESCALATION_REASONS = ["high_value", "deadline_near", "repeat_disputer", "conflicting_evidence",
                      "missing_required_evidence", "low_confidence", "other"]


def evidence_vocabulary() -> list[dict]:
    """Evidence IDs and plain descriptions (no category mapping: that is the rules table's job)."""
    with open(DATA_DIR / "rules" / "evidence_definitions.csv") as f:
        return [{"evidence_id": r["evidence_id"], "description": r["description"]} for r in csv.DictReader(f)]


def output_schema() -> dict:
    ids = [e["evidence_id"] for e in evidence_vocabulary()]
    id_list = {"type": "array", "items": {"type": "string", "enum": ids}}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["classification", "evidence", "assessment", "decision", "draft"],
        "properties": {
            "classification": {
                "type": "object", "additionalProperties": False,
                "required": ["network", "reason_code", "category", "rationale"],
                "properties": {
                    "network": {"type": "string", "enum": ["visa", "mastercard", "amex"]},
                    "reason_code": {"type": "string"},
                    "category": {"type": "string", "enum": CATEGORIES},
                    "rationale": {"type": "string"},
                },
            },
            "evidence": {
                "type": "object", "additionalProperties": False,
                "required": ["required_present", "required_missing", "strong_present", "findings"],
                "properties": {
                    "required_present": id_list,
                    "required_missing": id_list,
                    "strong_present": id_list,
                    "findings": {
                        "type": "array",
                        "items": {
                            "type": "object", "additionalProperties": False,
                            "required": ["evidence_id", "status", "basis"],
                            "properties": {
                                "evidence_id": {"type": "string", "enum": ids},
                                "status": {"type": "string", "enum": ["present", "missing"]},
                                "basis": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "assessment": {
                "type": "object", "additionalProperties": False,
                "required": ["conflicts", "merchant_at_fault", "refund_already_issued", "hours_remaining",
                             "prior_disputes", "p_win", "expected_value", "confidence"],
                "properties": {
                    "conflicts": {"type": "array", "items": {"type": "string"}},
                    "merchant_at_fault": {"type": "boolean"},
                    "refund_already_issued": {"type": "number"},
                    "hours_remaining": {"type": "number"},
                    "prior_disputes": {"type": "integer"},
                    "p_win": {"type": "number"},
                    "expected_value": {"type": "number"},
                    "confidence": {"type": "number"},
                },
            },
            "decision": {
                "type": "object", "additionalProperties": False,
                "required": ["action", "escalation_reasons", "rationale"],
                "properties": {
                    "action": {"type": "string", "enum": DECISIONS},
                    "escalation_reasons": {"type": "array", "items": {"type": "string", "enum": ESCALATION_REASONS}},
                    "rationale": {"type": "string"},
                },
            },
            "draft": {
                "type": "object", "additionalProperties": False,
                "required": ["narrative", "evidence_list"],
                "properties": {
                    "narrative": {"type": "string"},
                    "evidence_list": {
                        "type": "array",
                        "items": {
                            "type": "object", "additionalProperties": False,
                            "required": ["item", "source"],
                            "properties": {"item": {"type": "string"}, "source": {"type": "string"}},
                        },
                    },
                },
            },
        },
    }
