import json
from atfd.schema import (
    CostReport,
    Event,
    EventType,
    Finding,
    GroundTruth,
    JudgeOutput,
    Outcome,
    QualityDimension,
    QualityAssessment,
    Severity,
    SourceLabel,
    Trajectory,
)


def _make_event(type_="user_message", content="hello"):
    return {"type": type_, "timestamp": "2026-01-01T00:00:00Z", "content": content, "metadata": {}}


def _make_trajectory(**overrides):
    base = {
        "trajectory_id": "t_001",
        "source": "tau-bench",
        "domain": "retail",
        "events": [_make_event()],
        "ground_truth": {
            "outcome": "fail",
            "failure_categories": ["action.wrong_tool"],
            "quality_categories": [],
            "source_labels": {},
            "consensus": "gold",
        },
    }
    base.update(overrides)
    return base


def test_trajectory_parses():
    t = Trajectory.model_validate(_make_trajectory())
    assert t.trajectory_id == "t_001"
    assert t.source == "tau-bench"
    assert len(t.events) == 1


def test_trajectory_rejects_invalid_source():
    import pydantic
    try:
        Trajectory.model_validate(_make_trajectory(source="invalid"))
        assert False, "Should have raised"
    except pydantic.ValidationError:
        pass


def test_outcome_enum():
    assert Outcome.PASS == "pass"
    assert Outcome.DEGRADED == "degraded"
    assert Outcome.FAIL == "fail"


def test_finding_with_cost():
    f = Finding(severity="error", category="action.wrong_tool", description="Called wrong tool")
    assert f.severity == Severity.ERROR
    assert f.attribution is None


def test_judge_output_validates():
    jo = JudgeOutput(
        trajectory_id="t_001",
        has_failure=True,
        findings=[Finding(severity="error", category="action.wrong_tool", description="wrong tool")],
        cost=CostReport(dollar_cost=0.04, latency_seconds=3.5, total_tokens=6200, api_calls=1, infrastructure="api_key"),
    )
    assert jo.cost.dollar_cost == 0.04
    assert len(jo.findings) == 1


def test_judge_output_serializes_to_json():
    jo = JudgeOutput(
        trajectory_id="t_001",
        has_failure=False,
        findings=[],
        cost=CostReport(dollar_cost=0.0, latency_seconds=0.01, total_tokens=0, api_calls=0, infrastructure="none"),
    )
    data = json.loads(jo.model_dump_json())
    assert data["trajectory_id"] == "t_001"
    assert data["cost"]["dollar_cost"] == 0.0


def test_quality_assessment():
    qa = QualityAssessment(
        dimensions={"completeness": QualityDimension(score=2, explanation="All done"), "efficiency": QualityDimension(score=1, explanation="Too many calls")},
        quality_categories=["quality.suboptimal_approach"],
        overall_quality="degraded",
        reasoning="Efficient but not great",
    )
    assert qa.overall_quality == Outcome.DEGRADED
    assert qa.dimensions["efficiency"].score == 1


def test_ground_truth_validates_categories():
    gt = GroundTruth(
        outcome="fail",
        failure_categories=["action.wrong_tool", "state.wrong_state"],
        quality_categories=[],
        source_labels={},
        consensus="gold",
    )
    assert len(gt.failure_categories) == 2


def test_event_types():
    for t in ["user_message", "assistant_message", "tool_call", "tool_result", "system"]:
        e = Event(type=t, timestamp="2026-01-01T00:00:00Z", content="test")
        assert e.type == t
