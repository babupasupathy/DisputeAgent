"""LLM judge for draft quality (G-Eval style: explicit criteria and evaluation steps, reasoning
before each score). The judge is a different, stronger model than the agent (JUDGE_MODEL).
Scores are NOT trusted until calibrated against human labels (evals/judge_calibration.py)."""
from __future__ import annotations

import json

from src.agent.llm import Usage, agent_config, structured_call
from src.knowledge.rules import lookup

CRITERIA = {
    "addresses_requirements": "Does the draft respond to the dispute reason and cover each evidence type the "
                              "network expects for this category that is actually present in the records? "
                              "5 = every relevant present item is used and tied to the reason; 1 = ignores the reason.",
    "grounded": "Is every factual claim supported by the records? Missing evidence must not be implied. "
                "5 = all claims supported; 3 = minor overstatement; 1 = invents or misstates evidence.",
    "clarity": "Is it clear, specific and easy for an issuer analyst to follow? 5 = concise and specific; 1 = vague or confusing.",
    "format": "Is it a professional representment narrative plus an exhibit list that names where each exhibit comes "
              "from, without masked data being unmasked? 5 = ready to submit after review; 1 = unusable.",
}
STEPS = """Evaluation steps:
1. Read the dispute and identify the cardholder's claim.
2. Read the category's expected evidence list, then check which of those items the records actually contain.
3. Read the draft. For each factual claim, find the supporting record. List any claim with no support.
4. For each criterion, write one or two sentences of reasoning, then give an integer score from 1 to 5."""


def _schema() -> dict:
    crit = {k: {"type": "object", "additionalProperties": False, "required": ["reasoning", "score"],
                "properties": {"reasoning": {"type": "string"}, "score": {"type": "integer", "enum": [1, 2, 3, 4, 5]}}}
            for k in CRITERIA}
    return {"type": "object", "additionalProperties": False, "required": ["criteria", "unsupported_claims"],
            "properties": {"criteria": {"type": "object", "additionalProperties": False,
                                        "required": list(CRITERIA), "properties": crit},
                           "unsupported_claims": {"type": "array", "items": {"type": "string"}}}}


def system_prompt() -> str:
    crit = "\n".join(f"- {k}: {v}" for k, v in CRITERIA.items())
    return ("You grade chargeback representment drafts written by an AI agent for a merchant. "
            "Be strict and literal: judge only against the records provided.\n\nCriteria:\n" + crit + "\n\n" + STEPS)


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
    return {"scores": scores, "reasoning": {k: v["reasoning"] for k, v in res["criteria"].items()},
            "unsupported_claims": res["unsupported_claims"],
            "pass": min(scores.values()) >= 4 and not res["unsupported_claims"], "usage": usage.to_dict()}
