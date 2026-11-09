"""Deterministic fabrication check: every ID, tracking number, dollar amount, date and card
fragment in the draft must appear in what the agent actually saw (its trace)."""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from itertools import combinations

ID_RE = re.compile(r"\b(?:ORD|DSP|CUS|PRD|SHP|MSG|RFD|RET|LST)-\d+\b")
TRACK_RE = re.compile(r"\bSYN[0-9A-Z]{8,}\b")
MONEY_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d{1,2})?)")
ISO_DATE_RE = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
NAMED_DATE_RE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b", re.I)
SLASH_DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
LAST4_RE = re.compile(r"(?:\*{2,}\s?|ending (?:in )?)(\d{4})\b", re.I)


def _numbers(obj, out: set):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.add(round(float(obj), 2))
    elif isinstance(obj, dict):
        for v in obj.values():
            _numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _numbers(v, out)
    elif isinstance(obj, str):
        for m in MONEY_RE.finditer(obj):
            out.add(round(float(m.group(1).replace(",", "")), 2))


def context_facts(dispute: dict, trace: list[dict]) -> dict:
    blob = json.dumps([dispute] + [t["output"] for t in trace])
    nums: set[float] = set()
    _numbers([dispute] + [t["output"] for t in trace], nums)
    money = {n for n in nums if n >= 1}
    derived = {round(a + b, 2) for a, b in combinations(money, 2)} | \
              {round(abs(a - b), 2) for a, b in combinations(money, 2)}
    dates = {date(int(y), int(m), int(d)) for y, m, d in ISO_DATE_RE.findall(blob)}
    last4 = set(re.findall(r'"\*\*\*\*(\d{4})"', blob))
    return {"blob": blob, "money": money, "derived_money": derived, "dates": dates, "last4": last4}


def draft_text(output: dict) -> str:
    d = (output or {}).get("draft") or {}
    items = " ".join(f"{e.get('item', '')} {e.get('source', '')}" for e in d.get("evidence_list") or [])
    return f"{d.get('narrative', '')}\n{items}"


def _dates_in(text: str) -> list[tuple[str, date | None]]:
    out = []
    for y, m, d in ISO_DATE_RE.findall(text):
        out.append((f"{y}-{m}-{d}", _safe_date(int(y), int(m), int(d))))
    for mon, d, y in NAMED_DATE_RE.findall(text):
        out.append((f"{mon} {d}, {y}", _safe_date(int(y), MONTHS[mon[:3].lower()], int(d))))
    for m, d, y in SLASH_DATE_RE.findall(text):
        out.append((f"{m}/{d}/{y}", _safe_date(int(y), int(m), int(d))))
    return out


def _safe_date(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


def check(output: dict, dispute: dict, trace: list[dict]) -> dict:
    """Return unsupported tokens by type. `derived` amounts (sum/difference of two amounts the
    agent saw, e.g. an unrefunded balance) are allowed but reported separately."""
    text = draft_text(output)
    f = context_facts(dispute, trace)
    bad: dict[str, list[str]] = {"ids": [], "tracking": [], "amounts": [], "dates": [], "card": []}
    derived_used = []
    for tok in set(ID_RE.findall(text)):
        if tok not in f["blob"]:
            bad["ids"].append(tok)
    for tok in set(TRACK_RE.findall(text)):
        if tok not in f["blob"]:
            bad["tracking"].append(tok)
    for raw in set(MONEY_RE.findall(text)):
        v = round(float(raw.replace(",", "")), 2)
        if v in f["money"]:
            continue
        if v in f["derived_money"]:
            derived_used.append(raw)
        else:
            bad["amounts"].append("$" + raw)
    for raw, d in _dates_in(text):
        if d is None or d not in f["dates"]:
            bad["dates"].append(raw)
    for tok in set(LAST4_RE.findall(text)):
        if tok not in f["last4"]:
            bad["card"].append(tok)
    n = sum(len(v) for v in bad.values())
    return {"fabricated": n > 0, "n_unsupported": n, "unsupported": {k: v for k, v in bad.items() if v},
            "derived_amounts": derived_used}
