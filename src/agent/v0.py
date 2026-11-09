"""V0 baseline: one prompt, no tools, no rules table. Every record is pasted into the prompt."""
from __future__ import annotations

import json

from src.agent.context import full_context
from src.agent.llm import Usage, agent_config, structured_call
from src.agent.prompts import v0_system
from src.agent.schema import output_schema

VERSION = "v0"


def run_case(client, conn, dispute: dict, model: str) -> dict:
    cfg = agent_config()["agent"]
    trace = full_context(conn, dispute)
    records = {t["tool"]: t["output"] for t in trace}
    user = ("Dispute webhook:\n" + json.dumps(dispute, indent=1, sort_keys=True)
            + "\n\nStore and processor records:\n" + json.dumps(records, indent=1, sort_keys=True))
    usage = Usage()
    output, _ = structured_call(
        client, model=model, system=v0_system(), messages=[{"role": "user", "content": user}],
        schema=output_schema(), effort=cfg["effort"], max_tokens=cfg["max_tokens"], usage=usage)
    return {"output": output, "trace": trace, "tool_calls": [], "usage": usage.to_dict()}
