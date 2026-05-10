import json
from atfd.adapters.base import DatasetAdapter
from atfd.adapters.tau_bench import TauBenchAdapter
from atfd.schema import Trajectory, Outcome


def _mock_tau_simulation():
    return {
        "id": "sim_001", "task_id": "42",
        "messages": [
            {"role": "system", "content": "You are a retail agent."},
            {"role": "user", "content": "I want to exchange my order."},
            {"role": "assistant", "content": "Let me look that up.", "tool_calls": [{"id": "tc_1", "name": "get_order_details", "arguments": {"order_id": "12345"}}]},
            {"role": "tool", "id": "tc_1", "content": '{"order_id": "12345", "status": "delivered"}', "error": False},
            {"role": "assistant", "content": "I found your order. Processing exchange.", "tool_calls": []},
        ],
        "termination_reason": "AGENT_STOP",
        "reward_info": {"reward": 0.0, "reward_breakdown": {"DB": 0.0, "ACTION": 1.0, "COMMUNICATE": 1.0}},
    }

def _mock_tau_task():
    return {"id": 42, "user_scenario": {"reason_for_call": "Exchange shoes for different size"}}

def test_adapter_is_abstract():
    try:
        DatasetAdapter()
        assert False, "Should not instantiate"
    except TypeError:
        pass

def test_tau_bench_converts_single_sim():
    adapter = TauBenchAdapter(domain="retail")
    trajectory = adapter.convert_simulation(_mock_tau_simulation(), _mock_tau_task())
    assert isinstance(trajectory, Trajectory)
    assert trajectory.trajectory_id.startswith("tau_")
    assert trajectory.source.value == "tau-bench"
    assert trajectory.domain == "retail"
    assert len(trajectory.events) > 0

def test_tau_bench_extracts_ground_truth():
    adapter = TauBenchAdapter(domain="retail")
    trajectory = adapter.convert_simulation(_mock_tau_simulation(), _mock_tau_task())
    assert trajectory.ground_truth.outcome == Outcome.FAIL
    assert "state.wrong_state" in trajectory.ground_truth.failure_categories

def test_tau_bench_pass_trajectory():
    adapter = TauBenchAdapter(domain="retail")
    sim = _mock_tau_simulation()
    sim["reward_info"]["reward"] = 1.0
    sim["reward_info"]["reward_breakdown"] = {"DB": 1.0, "ACTION": 1.0, "COMMUNICATE": 1.0}
    trajectory = adapter.convert_simulation(sim, _mock_tau_task())
    assert trajectory.ground_truth.outcome == Outcome.PASS

def test_tau_bench_events_have_correct_types():
    adapter = TauBenchAdapter(domain="retail")
    trajectory = adapter.convert_simulation(_mock_tau_simulation(), _mock_tau_task())
    event_types = [e.type.value for e in trajectory.events]
    assert "user_message" in event_types
    assert "tool_call" in event_types
    assert "tool_result" in event_types

def test_tau_bench_tool_failed_event():
    adapter = TauBenchAdapter(domain="retail")
    sim = _mock_tau_simulation()
    sim["messages"][3]["error"] = True
    trajectory = adapter.convert_simulation(sim, _mock_tau_task())
    tool_results = [e for e in trajectory.events if e.type.value == "tool_result"]
    assert any(e.metadata.get("error") for e in tool_results)
