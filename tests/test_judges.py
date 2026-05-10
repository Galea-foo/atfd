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
