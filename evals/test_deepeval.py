"""DeepEval harness over stored results (no model calls here).

    EVAL_VERSION=v0 DEEPEVAL_TELEMETRY_OPT_OUT=YES python -m pytest evals/test_deepeval.py -q

Each case becomes an LLMTestCase; each eval dimension is a DeepEval metric wrapping the same
deterministic check used by evals/score.py (one source of truth). A failing test = a case that
failed that dimension. evals/score.py remains the source of the aggregate numbers."""
from __future__ import annotations

import json
import os

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")

import pytest
from deepeval import assert_test
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase, ToolCall

from evals.metrics.deterministic import score_case
from evals.paths import CASES_DIR, RESULTS_DIR
from evals.score import _latest

VERSION = os.environ.get("EVAL_VERSION", "oracle")
CASES = [json.loads(l) for l in open(CASES_DIR / "cases.jsonl")]
RESULTS = _latest(RESULTS_DIR / VERSION / "outputs.jsonl")
JUDGE = _latest(RESULTS_DIR / VERSION / "judge.jsonl")


class Check(BaseMetric):
    """Binary DeepEval metric backed by a deterministic check on the per-case score dict."""
    def __init__(self, name, fn, threshold=1.0):
        self.name, self.fn, self.threshold = name, fn, threshold
        self.evaluation_model, self.include_reason, self.async_mode, self.strict_mode = None, True, False, True

    def measure(self, test_case: LLMTestCase, *a, **k) -> float:
        s = test_case.metadata["score"]
        if "error" in s:
            self.score, self.reason = 0.0, s["error"]
        else:
            ok, why = self.fn(s, test_case)
            self.score, self.reason = (1.0 if ok else 0.0), why
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case, *a, **k):
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return self.name


METRICS = [
    Check("classification", lambda s, t: (s["classification"]["category_correct"], "category")),
    Check("evidence_completeness", lambda s, t: (s["evidence"]["required_exact"],
          f"false_missing={s['evidence']['false_missing']} false_present={s['evidence']['false_present']}")),
    Check("decision", lambda s, t: (s["decision"]["correct"],
          f"expected {s['decision']['expected']} got {s['decision']['predicted']}")),
    Check("no_fabrication", lambda s, t: (not s["fabrication"]["fabricated"], json.dumps(s["fabrication"]["unsupported"]))),
    Check("tool_use", lambda s, t: ((not s["tool_use"]["applicable"]) or
          (s["tool_use"]["all_required_called"] and not s["tool_use"]["unneeded_called"]), json.dumps(s["tool_use"]))),
    Check("draft_quality_judge", lambda s, t: (t.metadata["judge"] is None or t.metadata["judge"]["pass"],
          json.dumps((t.metadata["judge"] or {}).get("scores")))),
]


def _test_case(case):
    r = RESULTS.get(case["case_id"], {"output": None, "error": "not run"})
    s = score_case(case, r)
    out = r.get("output") or {}
    return LLMTestCase(
        input=json.dumps(case["dispute"]), actual_output=json.dumps(out.get("draft", {})),
        expected_output=case["labels"]["decision"], name=case["case_id"],
        tools_called=[ToolCall(name=c["tool"]) for c in r.get("tool_calls") or []],
        expected_tools=[ToolCall(name=t) for t in case["labels"]["required_tools"]],
        token_cost=(r.get("usage") or {}).get("cost_usd"), completion_time=(r.get("usage") or {}).get("latency_s"),
        metadata={"score": s, "judge": JUDGE.get(case["case_id"]) if case["case_id"] in JUDGE and JUDGE[case["case_id"]].get("scores") else None})


@pytest.mark.skipif(not RESULTS, reason=f"no stored results for {VERSION}")
@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_case(case):
    assert_test(_test_case(case), METRICS, run_async=False)
