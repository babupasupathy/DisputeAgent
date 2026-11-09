"""Thin wrapper around the Anthropic SDK: structured-output calls with usage, cost and
latency logging. Model names come from the environment only."""
from __future__ import annotations

import json
import os
import time
import tomllib
from dataclasses import asdict, dataclass, field
from functools import lru_cache

import anthropic

from src.config import CONFIG_DIR


def model_from_env(var: str = "ANTHROPIC_MODEL") -> str:
    m = os.environ.get(var)
    if not m:
        raise RuntimeError(f"set {var} (model name is read from the environment, never hardcoded)")
    return m


@lru_cache(maxsize=None)
def agent_config() -> dict:
    with open(CONFIG_DIR / "agent.toml", "rb") as f:
        return tomllib.load(f)


@lru_cache(maxsize=None)
def pricing() -> dict:
    with open(CONFIG_DIR / "pricing.toml", "rb") as f:
        return tomllib.load(f)


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    calls: int = 0
    latency_s: float = 0.0
    cost_usd: float = 0.0
    served_models: list = field(default_factory=list)

    def add(self, resp, model: str, latency: float):
        u = resp.usage
        self.input_tokens += u.input_tokens or 0
        self.output_tokens += u.output_tokens or 0
        self.cache_read_input_tokens += getattr(u, "cache_read_input_tokens", 0) or 0
        self.cache_creation_input_tokens += getattr(u, "cache_creation_input_tokens", 0) or 0
        self.calls += 1
        self.latency_s = round(self.latency_s + latency, 3)
        served = getattr(resp, "model", model) or model
        if served not in self.served_models:
            self.served_models.append(served)
        self.cost_usd = round(self.cost_usd + cost_of(u, served), 6)

    def to_dict(self):
        return asdict(self)


def cost_of(u, model: str) -> float:
    p = pricing().get(model)
    if p is None:
        return float("nan")
    cr = getattr(u, "cache_read_input_tokens", 0) or 0
    cw = getattr(u, "cache_creation_input_tokens", 0) or 0
    return ((u.input_tokens or 0) * p["input"] + cw * p["input"] * 1.25 + cr * p["cache_read"]
            + (u.output_tokens or 0) * p["output"]) / 1e6


class LLMError(RuntimeError):
    pass


def api_key_from_env() -> str | None:
    """ANTHROPIC_API_KEY, else DISPUTE_AGENT_ANTHROPIC_KEY (some hosted runtimes reserve the
    standard name and do not pass it through)."""
    return os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("DISPUTE_AGENT_ANTHROPIC_KEY")


def make_client() -> anthropic.Anthropic:
    key = api_key_from_env()
    if not key:
        raise RuntimeError("set ANTHROPIC_API_KEY or DISPUTE_AGENT_ANTHROPIC_KEY")
    return anthropic.Anthropic(api_key=key, max_retries=agent_config()["agent"]["max_retries"])


def structured_call(client, *, model: str, system: str, messages: list, schema: dict, effort: str,
                    max_tokens: int, usage: Usage, tools: list | None = None) -> tuple[dict | None, object]:
    """One Messages call constrained to `schema`. Refusal fallback is enabled server-side;
    the served model is recorded in usage.served_models so a fallback is visible in results."""
    kw = dict(
        model=model, max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
    )
    if tools:
        kw["tools"] = tools
    t0 = time.perf_counter()
    resp = client.beta.messages.create(**kw)
    usage.add(resp, model, time.perf_counter() - t0)
    if resp.stop_reason == "refusal":
        raise LLMError(f"refusal: {getattr(resp, 'stop_details', None)}")
    if resp.stop_reason == "max_tokens":
        raise LLMError("hit max_tokens; output incomplete")
    text = next((b.text for b in resp.content if b.type == "text"), None)
    return (json.loads(text) if text else None), resp
