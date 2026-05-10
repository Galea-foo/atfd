from atfd.judges.base import Judge
from atfd.judges.naive import NaiveHeuristicJudge
from atfd.schema import Event, EventType, GroundTruth, Outcome, Trajectory


def _traj(events, tid="t_001"):
    return Trajectory(
        trajectory_id=tid, source="synthetic", domain="retail", events=events,
        ground_truth=GroundTruth(outcome="pass", failure_categories=[], quality_categories=[], source_labels={}, consensus="gold"),
    )

def _event(type_, content="", **meta):
    return Event(type=type_, timestamp="2026-01-01T00:00:00Z", content=content, metadata=meta)


def test_judge_is_abstract():
    try:
        Judge()
        assert False
    except TypeError:
        pass

def test_naive_detects_tool_error():
    events = [_event("user_message", "help"), _event("tool_call", "get_order"), _event("tool_result", "error", error=True)]
    judge = NaiveHeuristicJudge()
    output = judge.evaluate(_traj(events))
    assert output.has_failure
    assert any(f.category == "infrastructure.error" for f in output.findings)

def test_naive_detects_tool_loop():
    events = [_event("user_message", "help")]
    for _ in range(6):
        events.append(_event("tool_call", "get_order", tool_name="get_order"))
        events.append(_event("tool_result", "ok"))
    judge = NaiveHeuristicJudge()
    output = judge.evaluate(_traj(events))
    assert any(f.category == "process.tool_loop" for f in output.findings)

def test_naive_no_false_positive_on_clean():
    events = [_event("user_message", "help"), _event("tool_call", "get_order", tool_name="get_order"), _event("tool_result", "ok"), _event("assistant_message", "Here is your order.")]
    judge = NaiveHeuristicJudge()
    output = judge.evaluate(_traj(events))
    error_findings = [f for f in output.findings if f.severity.value == "error"]
    assert len(error_findings) == 0

def test_naive_reports_zero_cost():
    judge = NaiveHeuristicJudge()
    output = judge.evaluate(_traj([_event("user_message", "help")]))
    assert output.cost.dollar_cost == 0.0
    assert output.cost.total_tokens == 0
    assert output.cost.infrastructure.value == "none"

def test_naive_reports_latency():
    judge = NaiveHeuristicJudge()
    output = judge.evaluate(_traj([_event("user_message", "help")]))
    assert output.cost.latency_seconds >= 0.0


# ---------------------------------------------------------------------------
# LLMJudge tests
# ---------------------------------------------------------------------------

from unittest.mock import patch, MagicMock  # noqa: E402
from atfd.judges.llm_judge import LLMJudge  # noqa: E402


def test_llm_judge_name():
    judge = LLMJudge(model_key="gpt-4.1")
    assert judge.name == "llm_judge_gpt-4.1"

def test_llm_judge_parses_stage1_fail():
    judge = LLMJudge(model_key="gpt-4.1")
    mock_response = '{"outcome": "fail", "failure_categories": ["action.wrong_tool"], "failure_events": [], "reasoning": "Wrong tool called"}'
    with patch.object(judge, "_call_model", return_value=(mock_response, 1000, 200)):
        output = judge.evaluate(_traj([_event("user_message", "help")]))
    assert output.has_failure
    assert output.findings[0].category == "action.wrong_tool"
    assert output.cost.api_calls == 1

def test_llm_judge_runs_stage2_on_pass():
    judge = LLMJudge(model_key="gpt-4.1")
    stage1_resp = '{"outcome": "pass", "failure_categories": [], "failure_events": [], "reasoning": "OK"}'
    stage2_resp = '{"dimensions": {}, "quality_categories": ["quality.shallow_output"], "overall_quality": "degraded", "reasoning": "Shallow"}'
    call_count = 0
    def mock_call(prompt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return stage1_resp, 1000, 200
        return stage2_resp, 800, 150
    with patch.object(judge, "_call_model", side_effect=mock_call):
        output = judge.evaluate(_traj([_event("user_message", "help")]))
    assert output.cost.api_calls == 2
    assert any(f.category == "quality.shallow_output" for f in output.findings)
