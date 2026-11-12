"""LLM judge for draft quality (G-Eval style: explicit criteria and evaluation steps, reasoning
before each score). The judge is a different, stronger model than the agent (JUDGE_MODEL).
Scores are NOT trusted until calibrated against human labels (evals/judge_calibration.py)."""
from __future__ import annotations

import json

from src.agent.llm import Usage, agent_config, structured_call
from src.knowledge.rules import lookup

# v1 failed a letter on ANY unsupported claim; calibration (docs/evals.md) showed that fails
# letters on wording a human reviewer accepts. v2 grades each problem as material or minor and
# fails only on material problems. v3 (owner ruling during adjudication): describing a dispatch or
# delivery photo as showing the item's condition, when the records only show the photo exists, is minor.
RUBRIC_VERSION = "v3-material"

CRITERIA = {
    "addresses_requirements": "Does the draft respond to the dispute reason and cover each evidence type the "
                              "network expects for this category that is actually present in the records? "
                              "5 = every relevant present item is used and tied to the reason; 1 = ignores the reason.",
    "grounded": "Is every factual claim supported by the records, with nothing in the records contradicting it? "
                "Missing evidence must not be implied. 5 = no problems; 4 = only minor problems; "
                "3 or lower = at least one material problem; 1 = invents evidence or contradicts the records.",
    "clarity": "Is it clear, specific and easy for an issuer analyst to follow? 5 = concise and specific; 1 = vague or confusing.",
    "format": "Is it a professional representment narrative plus an exhibit list that names where each exhibit comes "
              "from, without masked data being unmasked? 5 = ready to submit after review; 1 = unusable.",
}
SEVERITY = """Every problem you find is either MATERIAL or MINOR.

MATERIAL (an issuer analyst could be misled, or the merchant could be embarrassed):
- contradicts the records (e.g. "the merchant had no chance to resolve it" when the support log shows an offer)
- invents a fact, event, document or process that no record mentions (e.g. "pending internal review")
- a wrong number, date, amount, ID or duration, including one computed for the wrong point in time
  (e.g. an age "at order time" that is really the age when the records were pulled)
- implies evidence exists that the records show is missing (e.g. "signed for" when signature_on_file is false)
- claims what an item or a document shows when the records only show that it exists
  (e.g. "the item matched the listing"; a photo is the exception, see MINOR)
- exposes masked data

MINOR (imprecise, but adds no new fact and would not change what an analyst concludes):
- harmless wording around a recorded fact (e.g. "accepted the return policy at checkout" when the order
  records the accepted policy; "filed on" for the dispute's received date)
- naming a reason code by its standard name or category (e.g. "F29, card-not-present fraud")
- a reasonable reading of an empty record (e.g. "no return was requested" when the returns list is empty)
- calling a recorded dispatch or delivery photo a photo "of the item's condition" or "of the package at the
  door" when the records only show that the photo exists (its usual purpose; the reviewer attaches the photo)

When unsure, ask: if the analyst checked this sentence against the records, would they find it false or
invented? Yes = material. Only loosely worded = minor."""

STEPS = """Evaluation steps:
1. Read the dispute and identify the cardholder's claim.
2. Read the category's expected evidence list, then check which of those items the records actually contain.
3. Read the draft. For each factual claim, find the supporting record, and check that nothing in the
   records contradicts it. Record every problem with its severity (material or minor).
4. For each criterion, write one or two sentences of reasoning, then give an integer score from 1 to 5."""


def _schema() -> dict:
    crit = {k: {"type": "object", "additionalProperties": False, "required": ["reasoning", "score"],
                "properties": {"reasoning": {"type": "string"}, "score": {"type": "integer", "enum": [1, 2, 3, 4, 5]}}}
            for k in CRITERIA}
    issue = {"type": "object", "additionalProperties": False, "required": ["claim", "problem", "severity"],
             "properties": {"claim": {"type": "string"}, "problem": {"type": "string"},
                            "severity": {"type": "string", "enum": ["material", "minor"]}}}
    return {"type": "object", "additionalProperties": False, "required": ["criteria", "issues"],
            "properties": {"criteria": {"type": "object", "additionalProperties": False,
                                        "required": list(CRITERIA), "properties": crit},
                           "issues": {"type": "array", "items": issue}}}


def passes(scores: dict, issues: list[dict]) -> bool:
    """A letter passes when every criterion is at least 4 and no problem is material."""
    return min(scores.values()) >= 4 and not any(i["severity"] == "material" for i in issues)


def system_prompt() -> str:
    crit = "\n".join(f"- {k}: {v}" for k, v in CRITERIA.items())
    return ("You grade chargeback representment drafts written by an AI agent for a merchant. "
            "Judge only against the records provided.\n\nCriteria:\n" + crit + "\n\n" + SEVERITY + "\n\n" + STEPS)


def judge_draft(client, model: str, dispute: dict, category: str, trace: list[dict], output: dict) -> dict:
    rule = lookup(dispute["network"], dispute["reason_code"], category)
    records = {t["tool"]: t["output"] for t in trace}
    user = (f"Dispute:\n{json.dumps(dispute, indent=1)}\n\nCategory: {category}\n"
            f"Evidence the network expects (required): {', '.join(rule.required_evidence)}\n"
            f"Evidence that strengthens the case: {', '.join(rule.strong_evidence)}\n\n"
            f"Records the agent had:\n{json.dumps(records, indent=1, sort_keys=True)}\n\n"
            f"Draft to grade:\n{json.dumps(output['draft'], indent=1)}")
    usage = Usage()
    cfg = agent_config()["judge"]
    res, _ = structured_call(client, model=model, system=system_prompt(),
                             messages=[{"role": "user", "content": user}], schema=_schema(),
                             effort=cfg["effort"], max_tokens=cfg["max_tokens"], usage=usage)
    scores = {k: v["score"] for k, v in res["criteria"].items()}
    issues = res["issues"]
    return {"scores": scores, "reasoning": {k: v["reasoning"] for k, v in res["criteria"].items()},
            "issues": issues,
            # material problems only, so score.py's "drafts with unsupported claims" keeps its meaning
            "unsupported_claims": [f"{i['claim']} ({i['problem']})" for i in issues if i["severity"] == "material"],
            "pass": passes(scores, issues), "rubric_version": RUBRIC_VERSION, "usage": usage.to_dict()}
