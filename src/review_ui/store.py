"""Human review records: what the agent proposed, what the reviewer did, and how much they changed the letter.

Every review is appended to a JSONL file (one line per decision; the latest line per case wins), so the
override rate and the letter edit rate are computed from data, not anecdotes (PROJECT_BRIEF.md: "capture the
reviewer's change as data; override rate is a key metric"). Only reviewed records may enter case history.
"""
from __future__ import annotations

import difflib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# What a reviewer can do with a case in the queue.
ACTIONS = {
    "approve": "Approve the letter as drafted and contest the dispute",
    "edit_and_approve": "Edit the letter, then contest the dispute",
    "accept_loss": "Accept the dispute (refund stands, no letter sent)",
    "escalate": "Send to a senior reviewer",
}
CONTESTS = {"approve", "edit_and_approve"}


@dataclass
class Review:
    case_id: str
    version: str
    agent_action: str            # fight / escalate / accept (what the agent proposed)
    letter_status: str           # drafted / brief_only / on_demand / accept_template
    reviewer_action: str         # one of ACTIONS
    letter_before: str = ""
    letter_after: str = ""
    note: str = ""
    reviewer: str = "owner"
    guardrail_override: bool = False
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    def __post_init__(self):
        if self.reviewer_action not in ACTIONS:
            raise ValueError(f"unknown reviewer action {self.reviewer_action!r}")

    @property
    def edit_ratio(self) -> float:
        """Share of the letter the reviewer changed (0 = untouched, 1 = rewritten)."""
        if not self.letter_before and not self.letter_after:
            return 0.0
        return round(1 - difflib.SequenceMatcher(None, self.letter_before, self.letter_after).ratio(), 4)

    @property
    def overrode_agent(self) -> bool:
        """The reviewer reversed the agent: a proposed fight was accepted, or a proposed accept was contested.
        Resolving an escalation either way is the reviewer doing their job, not an override."""
        return ((self.agent_action == "fight" and self.reviewer_action == "accept_loss")
                or (self.agent_action == "accept" and self.reviewer_action in CONTESTS))


class ReviewStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def add(self, review: Review) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as f:
            f.write(json.dumps({**asdict(review), "edit_ratio": review.edit_ratio,
                                "overrode_agent": review.overrode_agent}) + "\n")

    def latest(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        if self.path.exists():
            for line in open(self.path):
                if line.strip():
                    r = json.loads(line)
                    out[r["case_id"]] = r
        return out

    def metrics(self) -> dict:
        rs = list(self.latest().values())
        n = len(rs)
        if not n:
            return {"reviewed": 0}
        fights = [r for r in rs if r["agent_action"] == "fight"]
        letters = [r for r in rs if r["reviewer_action"] in CONTESTS]
        edited = [r for r in letters if r["edit_ratio"] > 0.02]
        esc = [r for r in rs if r["agent_action"] == "escalate"]
        return {
            "reviewed": n,
            "override_rate": round(sum(r["overrode_agent"] for r in rs) / n, 3),
            "fights_reversed": sum(r["reviewer_action"] == "accept_loss" for r in fights),
            "letters_sent": len(letters),
            "letter_edit_rate": round(len(edited) / len(letters), 3) if letters else None,
            "mean_edit_ratio": round(sum(r["edit_ratio"] for r in letters) / len(letters), 3) if letters else None,
            "escalations_contested": sum(r["reviewer_action"] in CONTESTS for r in esc),
            "escalations_accepted": sum(r["reviewer_action"] == "accept_loss" for r in esc),
            "guardrail_overrides": sum(bool(r.get("guardrail_override")) for r in rs),
        }
