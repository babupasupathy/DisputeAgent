"""Prompt text. Policy numbers are rendered from config/decision.toml so the prompt and the
thresholds cannot drift apart."""
from __future__ import annotations

from src.agent.schema import evidence_vocabulary
from src.config import decision_config


def policy_text() -> str:
    c = decision_config()
    cost = c["cost"]["representment_fee"] + c["cost"]["handling_cost"]
    e = c["escalation"]
    return f"""## Decision policy (the merchant's rules; follow them exactly)
- Cost to fight one dispute: ${cost:.2f} (representment fee ${c['cost']['representment_fee']:.2f} + handling ${c['cost']['handling_cost']:.2f}).
- expected_value = P(win) x disputed_amount - ${cost:.2f}. Estimate P(win) from how complete and how strong the evidence is.
- Apply these rules in order; the first that matches decides:
  1. Response deadline already passed -> accept.
  2. Disputed amount >= ${e['high_value_amount']:.2f} -> escalate (reason high_value).
  3. Customer has >= {e['repeat_disputer_min_prior']} other disputes in the 365 days before this one -> escalate (reason repeat_disputer).
  4. The records show the merchant is at fault (e.g. carrier lost the package or returned it to sender; a return was received but never refunded), unless the order was already fully refunded -> accept.
  5. expected_value <= 0 -> accept.
  6. Fewer than {e['deadline_buffer_hours']} hours remain, records conflict with each other, or required evidence is missing -> escalate (unless the order was already fully refunded before the dispute, in which case the refund itself is the defense).
  7. Otherwise -> fight.
- If you are not confident in your own assessment, escalate with reason low_confidence."""


GROUNDING = """## Grounding rules
- Use only facts present in the records provided. Never invent order IDs, amounts, dates, tracking numbers, signatures, photos, messages or any other evidence.
- If a piece of evidence is not in the records, list it as missing. Say it is missing; do not imply it exists.
- Personal and payment data is masked in the records. Keep it masked; never try to reconstruct it."""

DRAFT_RULES = """## Draft
- If the action is fight or escalate, write the representment narrative a reviewer would send to the issuer: a short, factual letter that addresses the dispute reason point by point and cites only evidence you found. evidence_list names each exhibit and the record it comes from.
- If the action is accept, the narrative is one sentence explaining why the merchant is accepting, and evidence_list is empty."""


def vocabulary_text() -> str:
    lines = [f"- {e['evidence_id']}: {e['description']}" for e in evidence_vocabulary()]
    return "## Evidence vocabulary (use these IDs)\n" + "\n".join(lines)


def v0_system() -> str:
    return "\n\n".join([
        "You are a chargeback analyst for an online store. You receive one card-network dispute "
        "plus every record the store has about the order. Classify the dispute, decide which evidence "
        "the network requires for that dispute type and whether each item is present, decide whether to "
        "fight, accept or escalate to a human, and draft the response. A human reviews everything before "
        "anything is submitted.",
        policy_text(), GROUNDING, vocabulary_text(), DRAFT_RULES,
        "Return only the JSON object described by the output schema.",
    ])


# ---------------- V1: the model reads text and writes letters; decisions are code ----------------

def v1_reader_system() -> str:
    return """You read the free text attached to one card chargeback for an online store: the issuer's note and \
the support messages about the order. Everything else (tracking, payment checks, refunds, deadlines) is \
handled by code, so report only what the text says.

1. Category. If you are given more than one candidate category, pick the one the issuer's note describes:
   - item_not_received: the cardholder says the goods never arrived
   - not_as_described: the goods arrived but were defective, damaged or different from the description
   - fraud: the cardholder says they did not make or authorize the purchase
   If only one candidate is given, return it.

2. Four facts. For each, say whether a support message clearly states it, and if so give that message's \
message_id and an exact quote (copied character for character from the message body) that shows it.
   - customer_ack_receipt: the CUSTOMER says the package or item arrived / was received.
   - merchant_offered_remedy: the MERCHANT'S AGENT offers a return, refund, replacement or exchange.
   - merchant_ack_nondelivery: the MERCHANT'S AGENT acknowledges the package was lost, not delivered or \
went missing.
   - merchant_admitted_defect: the MERCHANT'S AGENT admits the item was defective, faulty or not as described.
   Messages from "system" are automated notifications and never count. Expectation or worry is not \
acknowledgement ("I'm still waiting", "tracking says delivered but..."). When unsure, answer false.

Return only the JSON object described by the output schema."""


def v1_reader_schema(candidates: list[str]) -> dict:
    fact = {"type": "object", "additionalProperties": False, "required": ["present", "message_id", "quote"],
            "properties": {"present": {"type": "boolean"}, "message_id": {"type": "string"},
                           "quote": {"type": "string"}}}
    return {"type": "object", "additionalProperties": False, "required": ["category", "category_rationale", "facts"],
            "properties": {
                "category": {"type": "string", "enum": candidates},
                "category_rationale": {"type": "string"},
                "facts": {"type": "object", "additionalProperties": False,
                          "required": ["customer_ack_receipt", "merchant_offered_remedy",
                                       "merchant_ack_nondelivery", "merchant_admitted_defect"],
                          "properties": {k: fact for k in ["customer_ack_receipt", "merchant_offered_remedy",
                                                           "merchant_ack_nondelivery", "merchant_admitted_defect"]}}}}


def v1_writer_system() -> str:
    return """You write the representment letter an online store sends to a card issuer to contest a chargeback, \
plus short notes for the store's internal reviewer. The decision to contest has already been made by the \
store's rules. You receive a fact sheet (verified evidence with the record each item comes from) and the \
raw records.

The letter (narrative) goes to the issuer:
- Address the dispute reason point by point, using the evidence marked present. Lead with the evidence the \
network expects for this reason code, then the evidence that strengthens the case.
- Use only facts in the fact sheet or the records. Copy numbers, dates, IDs and amounts exactly. Do not \
compute new figures except simple sums or differences of recorded amounts.
- Account age: use only customer_account_age_days_at_order (the age when this order was placed).
- Say only what a record shows. A photo or archived listing being on file does not tell you what it shows: \
say it is on file and is attached. Never write that the item was "as listed", "as described", "listed \
accurately", in good condition, or that it matched the listing. Do not add details no record states (for \
example that a return label was prepaid, that no signature was required, or why something happened).
- Never contradict a record. If the merchant's own agent conceded a point in a support message (for \
example a misdelivery, a lost package or a defect), do not argue the opposite: leave that point out of \
the letter and explain it in reviewer_notes. Do not describe a tracking history selectively: if the \
tracking ends in an exception (lost, returned, could not be located), do not present the shipment as \
delivered or complete.
- If the fact sheet shows a refund issued before the dispute, that refund is the merchant's main defense: \
state the refund (amount, date, refund ID) first and explain that the cardholder has already been credited.
- Do not mention evidence that is missing, internal processes, reviews, or doubts, and never concede or \
recommend accepting the dispute. The letter argues the merchant's case from what is on file.
- Write for a person at the card issuer, in plain English. Never use internal field names or code-style terms \
(for example delivered_address_match, signature_on_file, customer_account_age_days_at_order, avs_result) and \
never quote raw device IDs or IP tokens: say "the same device and network (IP) as order ORD-...". Write dates \
as YYYY-MM-DD; add a time only when it matters.
- Keep personal and payment data masked exactly as in the records.
- Professional, concise, factual. End by asking the issuer to resolve the dispute in the merchant's favor.

evidence_list: one entry per exhibit the letter relies on, naming the record it comes from.

reviewer_notes: everything the reviewer must know that does not belong in the letter: missing evidence, \
conflicts, why the case was escalated, anything to check before submitting. Plain sentences.

Return only the JSON object described by the output schema."""


def v1_writer_schema() -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["narrative", "evidence_list", "reviewer_notes"],
            "properties": {
                "narrative": {"type": "string"},
                "evidence_list": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False, "required": ["item", "source"],
                    "properties": {"item": {"type": "string"}, "source": {"type": "string"}}}},
                "reviewer_notes": {"type": "array", "items": {"type": "string"}}}}
