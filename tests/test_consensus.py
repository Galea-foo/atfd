from atfd.consensus import compute_consensus, ConsensusResult
from atfd.schema import Outcome, SourceLabel


def _label(outcome, failure_cats=None, quality_cats=None):
    return SourceLabel(outcome=outcome, failure_categories=failure_cats or [], quality_categories=quality_cats or [])


def test_gold_consensus_all_agree_fail():
    labels = {"programmatic": _label("fail", ["action.wrong_tool"]), "gpt4": _label("fail", ["action.wrong_tool"]), "claude": _label("fail", ["action.wrong_tool"]), "llama": _label("fail", ["action.wrong_args"])}
    result = compute_consensus(labels)
    assert result.outcome == Outcome.FAIL
    assert result.consensus == "gold"

def test_gold_consensus_all_agree_pass():
    labels = {"programmatic": _label("pass"), "gpt4": _label("pass"), "claude": _label("pass"), "llama": _label("pass")}
    result = compute_consensus(labels)
    assert result.outcome == Outcome.PASS
    assert result.consensus == "gold"

def test_majority_consensus_3_of_4():
    labels = {"programmatic": _label("fail", ["action.wrong_tool"]), "gpt4": _label("fail", ["action.wrong_tool"]), "claude": _label("fail", ["action.wrong_tool"]), "llama": _label("pass")}
    result = compute_consensus(labels)
    assert result.outcome == Outcome.FAIL
    assert result.consensus == "majority"
    assert "llama" in result.disagreeing_sources

def test_disputed_consensus_2_2_split():
    labels = {"programmatic": _label("fail"), "gpt4": _label("fail"), "claude": _label("pass"), "llama": _label("pass")}
    result = compute_consensus(labels)
    assert result.consensus == "disputed"

def test_consensus_merges_failure_categories():
    labels = {"programmatic": _label("fail", ["action.wrong_tool"]), "gpt4": _label("fail", ["action.wrong_tool", "state.wrong_state"]), "claude": _label("fail", ["action.wrong_tool"]), "llama": _label("fail", ["process.tool_loop"])}
    result = compute_consensus(labels)
    assert "action.wrong_tool" in result.failure_categories
    assert "state.wrong_state" in result.failure_categories

def test_consensus_with_degraded():
    labels = {"programmatic": _label("pass"), "gpt4": _label("degraded", quality_cats=["quality.shallow_output"]), "claude": _label("degraded", quality_cats=["quality.shallow_output"]), "llama": _label("degraded", quality_cats=["quality.poor_tone"])}
    result = compute_consensus(labels)
    assert result.outcome == Outcome.DEGRADED
    assert result.consensus == "majority"

def test_consensus_with_3_sources():
    labels = {"gpt4": _label("fail", ["action.wrong_tool"]), "claude": _label("fail", ["action.wrong_tool"]), "llama": _label("pass")}
    result = compute_consensus(labels)
    assert result.outcome == Outcome.FAIL
    assert result.consensus == "majority"
