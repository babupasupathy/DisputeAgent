"""Deterministic checks on the issuer-facing letter (draft.narrative).

Owner ruling (2026-11-12, docs/evals.md): a note addressed to the internal reviewer that flags a gap
("Note for reviewer: no signature is on file") is acceptable, because every draft is reviewed by a
person before submission. A note that concedes or undercuts the letter ("recommend accepting this
dispute") is a material defect: if submitted as written it argues against the merchant.
Reviewer notes are counted either way; only concessions fail a letter.
"""
from __future__ import annotations

import re

_SENT = re.compile(r"[^.!?\n]+[.!?]?")
REVIEWER_NOTE = re.compile(
    r"\b(note (for|to) (the )?reviewer|reviewer note|internal (reviewer|review) note|for reviewer assessment"
    r"|(requires|needs) human review|before (any )?submission)\b", re.I)
CONCESSION = re.compile(
    r"\b(recommend(s|ed)? (accepting|that we accept|we accept|conceding|not contesting|issuing (a|the) refund)"
    r"|(we )?should (accept|not contest|not fight|concede)"
    r"|instead of (contesting|fighting|disputing)"
    r"|not worth (contesting|fighting))\b", re.I)


# Internal field names (snake_case) and raw device / IP tokens do not belong in an issuer letter.
FIELD_NAME = re.compile(r"\b(?:[a-z]+(?:_[a-z0-9]+)+|dev_[0-9a-f]{6,}|ip_[0-9a-f]{6,})\b")


def _sentences(text: str, pattern: re.Pattern) -> list[str]:
    return [s.strip() for s in _SENT.findall(text or "") if pattern.search(s)]


def check(narrative: str) -> dict:
    notes = _sentences(narrative, REVIEWER_NOTE)
    conc = _sentences(narrative, CONCESSION)
    fields = sorted(set(FIELD_NAME.findall(narrative or "")))
    return {"reviewer_note": bool(notes), "concession": bool(conc), "notes": notes, "concessions": conc,
            "field_names": fields}
