"""Read-only loaders for the showcase app. Everything comes from files committed to the repo:
no database, no API key, no model calls."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).resolve().parent / "assets"
RESULTS = ROOT / "evals" / "results"
CASES = ROOT / "evals" / "cases" / "cases.jsonl"


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _by_case(rows: list[dict]) -> dict[str, dict]:
    # Later rows win, matching evals/score.py (the runner appends on resume).
    return {r["case_id"]: r for r in rows}


@st.cache_data
def cases() -> dict[str, dict]:
    return _by_case(_jsonl(CASES))


@st.cache_data
def scores(version: str = "v0") -> dict:
    p = RESULTS / version / "scores.json"
    return json.loads(p.read_text()) if p.exists() else {}


@st.cache_data
def outputs(version: str = "v0") -> dict[str, dict]:
    return _by_case(_jsonl(RESULTS / version / "outputs.jsonl"))


@st.cache_data
def per_case(version: str = "v0") -> dict[str, dict]:
    return _by_case(_jsonl(RESULTS / version / "per_case.jsonl"))


@st.cache_data
def judge(version: str = "v0") -> dict[str, dict]:
    return _by_case(_jsonl(RESULTS / version / "judge.jsonl"))



ACTION_ICON = {"fight": "🟢 fight", "accept": "⚪ accept", "escalate": "🟠 escalate"}


def action_label(a: str | None) -> str:
    return ACTION_ICON.get(a or "", a or "n/a")
