"""Tests for the AgentRx adapter."""
import json
import tempfile
from pathlib import Path

import pytest

from atfd.adapters.agentrx import AgentRxAdapter, CATEGORY_MAP
from atfd.schema import EventType, Outcome, Trajectory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _mock_agentrx_record():
    """Return a realistic mock AgentRx record."""
    return {
        "task_instruction": "Cancel order #W1234567 and process a full refund.",
        "trajectory_snippet": [
            {"content": "Cancel my order #W1234567 please.", "role": "human", "index": 1},
            {"content": "Let me look up your order.", "role": "Assistant", "index": 2},
            {"content": "I found order #W1234567. Processing cancellation.", "role": "Assistant", "index": 3},
            {"content": "I've cancelled the order but the refund was for $50 instead of $75.", "role": "Assistant", "index": 4},
            {"content": "That's not the right amount!", "role": "human", "index": 5},
            {"content": "Let me fix that for you.", "role": "Assistant", "index": 6},
            {"content": "I've now processed the full $75 refund.", "role": "Assistant", "index": 7},
        ],
        "failures": [
            {
                "failure_id": 1,
                "step_number": 4,
                "step_reason": "Refund amount was incorrect",
                "failure_category": "Invalid Invocation",
                "category_reason": "Wrong refund amount argument",
                "failed_agent": "Assistant",
            },
            {
                "failure_id": 2,
                "step_number": 3,
                "step_reason": "Did not verify order details before cancelling",
                "failure_category": "Instruction/Plan Adherence Failure",
                "category_reason": "Skipped verification step",
                "failed_agent": "Assistant",
            },
        ],
        "root_cause": {
            "failure_id": 2,
            "reason_for_root_cause": "Skipping order verification led to incorrect refund amount",
        },
        "failure_summary": "Agent cancelled order without verifying details, leading to wrong refund amount.",
    }


def _mock_magentic_record():
    """Return a mock multi-agent (Magentic-One) record."""
    return {
        "task_instruction": "Find the average temperature in Seattle last week.",
        "trajectory_snippet": [
            {"content": "Find average temperature in Seattle last week.", "role": "human", "index": 1},
            {"content": "I'll coordinate the search.", "role": "Orchestrator", "index": 2},
            {"content": "Searching for weather data...", "role": "WebSurfer", "index": 3},
            {"content": "Found data. Average was 58F.", "role": "WebSurfer", "index": 4},
            {"content": "The average temperature was 62F.", "role": "Orchestrator", "index": 5},
        ],
        "failures": [
            {
                "failure_id": 1,
                "step_number": 5,
                "step_reason": "Orchestrator reported 62F but WebSurfer found 58F",
                "failure_category": "Misinterpretation of Tool Output",
                "category_reason": "Orchestrator misread the WebSurfer's result",
                "failed_agent": "Orchestrator",
            },
        ],
        "root_cause": {
            "failure_id": 1,
            "reason_for_root_cause": "Single failure caused incorrect final answer",
        },
        "failure_summary": "Orchestrator misinterpreted WebSurfer output, reporting wrong temperature.",
    }


# ---------------------------------------------------------------------------
# Category mapping tests
# ---------------------------------------------------------------------------

class TestCategoryMapping:

    def test_all_agentrx_categories_mapped(self):
        """Every AgentRx category in the map produces a valid ATFD dotted key."""
        for rx_cat, atfd_cat in CATEGORY_MAP.items():
            parts = atfd_cat.split(".")
            assert len(parts) == 2, f"'{atfd_cat}' is not a dotted category"
            assert parts[0] in {
                "action", "state", "communication", "quality",
                "process", "safety", "infrastructure",
            }, f"Unknown top-level category: {parts[0]}"

    def test_instruction_adherence_maps_to_planning(self):
        assert CATEGORY_MAP["Instruction/Plan Adherence Failure"] == "process.planning_failure"

    def test_hallucination_mapping(self):
        assert CATEGORY_MAP["Invention of New Information"] == "communication.hallucination"

    def test_invalid_invocation_mapping(self):
        assert CATEGORY_MAP["Invalid Invocation"] == "action.wrong_args"

    def test_misinterpretation_mapping(self):
        assert CATEGORY_MAP["Misinterpretation of Tool Output"] == "communication.wrong_response"

    def test_guardrails_mapping(self):
        assert CATEGORY_MAP["Guardrails Triggered"] == "safety.policy_violation"

    def test_system_failure_mapping(self):
        assert CATEGORY_MAP["System Failure"] == "infrastructure.error"

    def test_underspecified_intent_mapping(self):
        assert CATEGORY_MAP["Underspecified User Intent"] == "communication.missing_info"

    def test_intent_not_supported_mapping(self):
        assert CATEGORY_MAP["Intent Not Supported"] == "action.missing_action"


# ---------------------------------------------------------------------------
# Event conversion tests
# ---------------------------------------------------------------------------

class TestEventConversion:

    def test_human_role_becomes_user_message(self):
        adapter = AgentRxAdapter()
        record = _mock_agentrx_record()
        traj = adapter.convert_simulation(record)
        user_events = [e for e in traj.events if e.type == EventType.USER_MESSAGE]
        assert len(user_events) == 2  # two "human" messages

    def test_agent_roles_become_assistant_message(self):
        adapter = AgentRxAdapter()
        record = _mock_magentic_record()
        traj = adapter.convert_simulation(record)
        assistant_events = [e for e in traj.events if e.type == EventType.ASSISTANT_MESSAGE]
        # Orchestrator + 2x WebSurfer + Orchestrator = 4 non-human messages
        assert len(assistant_events) == 4

    def test_diverse_agent_roles_all_assistant(self):
        """WebSurfer, Orchestrator, Coder etc. all map to ASSISTANT_MESSAGE."""
        adapter = AgentRxAdapter()
        record = _mock_magentic_record()
        traj = adapter.convert_simulation(record)
        for e in traj.events:
            if e.metadata.get("role") != "human":
                assert e.type == EventType.ASSISTANT_MESSAGE

    def test_events_preserve_role_in_metadata(self):
        adapter = AgentRxAdapter()
        record = _mock_magentic_record()
        traj = adapter.convert_simulation(record)
        roles = {e.metadata["role"] for e in traj.events}
        assert "Orchestrator" in roles
        assert "WebSurfer" in roles
        assert "human" in roles

    def test_events_capped_at_100(self):
        adapter = AgentRxAdapter()
        record = _mock_agentrx_record()
        # Inflate the trajectory to 150 messages
        record["trajectory_snippet"] = [
            {"content": f"Message {i}", "role": "Assistant", "index": i}
            for i in range(150)
        ]
        traj = adapter.convert_simulation(record)
        assert len(traj.events) == 100

    def test_content_truncated_at_2000(self):
        adapter = AgentRxAdapter()
        record = _mock_agentrx_record()
        record["trajectory_snippet"] = [
            {"content": "x" * 5000, "role": "human", "index": 1}
        ]
        traj = adapter.convert_simulation(record)
        assert len(traj.events[0].content) == 2000


# ---------------------------------------------------------------------------
# Full trajectory conversion tests
# ---------------------------------------------------------------------------

class TestTrajectoryConversion:

    def test_basic_conversion(self):
        adapter = AgentRxAdapter()
        traj = adapter.convert_simulation(_mock_agentrx_record())
        assert isinstance(traj, Trajectory)
        assert traj.source.value == "synthetic"
        assert traj.ground_truth.outcome == Outcome.FAIL

    def test_all_trajectories_are_failures(self):
        adapter = AgentRxAdapter()
        for record in [_mock_agentrx_record(), _mock_magentic_record()]:
            traj = adapter.convert_simulation(record)
            assert traj.ground_truth.outcome == Outcome.FAIL

    def test_trajectory_id_from_task_info(self):
        adapter = AgentRxAdapter()
        task = {"filename": "tau_retail_dataset", "index": 5}
        traj = adapter.convert_simulation(_mock_agentrx_record(), task=task)
        assert traj.trajectory_id == "agentrx_tau_retail_dataset_0005"

    def test_trajectory_id_default(self):
        adapter = AgentRxAdapter()
        traj = adapter.convert_simulation(_mock_agentrx_record())
        assert traj.trajectory_id == "agentrx_agentrx_0000"

    def test_domain_from_filename(self):
        adapter = AgentRxAdapter()
        task = {"filename": "tau_retail_dataset", "index": 0}
        traj = adapter.convert_simulation(_mock_agentrx_record(), task=task)
        assert traj.domain == "retail"

        task = {"filename": "magentic_dataset", "index": 0}
        traj = adapter.convert_simulation(_mock_magentic_record(), task=task)
        assert traj.domain == "multi_agent"

    def test_root_cause_determines_primary_category(self):
        """The root cause failure_category should be the first in the list."""
        adapter = AgentRxAdapter()
        traj = adapter.convert_simulation(_mock_agentrx_record())
        # Root cause is failure_id=2 which is "Instruction/Plan Adherence Failure"
        assert traj.ground_truth.failure_categories[0] == "process.planning_failure"

    def test_all_failure_categories_collected(self):
        adapter = AgentRxAdapter()
        traj = adapter.convert_simulation(_mock_agentrx_record())
        cats = traj.ground_truth.failure_categories
        assert "process.planning_failure" in cats
        assert "action.wrong_args" in cats

    def test_single_failure_category(self):
        adapter = AgentRxAdapter()
        traj = adapter.convert_simulation(_mock_magentic_record())
        cats = traj.ground_truth.failure_categories
        assert cats == ["communication.wrong_response"]

    def test_task_description_includes_instruction(self):
        adapter = AgentRxAdapter()
        traj = adapter.convert_simulation(_mock_agentrx_record())
        assert "Cancel order" in traj.task_description

    def test_consensus_is_gold(self):
        adapter = AgentRxAdapter()
        traj = adapter.convert_simulation(_mock_agentrx_record())
        assert traj.ground_truth.consensus.value == "gold"

    def test_fallback_category_when_no_mapping(self):
        """Unknown failure categories should fall back to process.planning_failure."""
        adapter = AgentRxAdapter()
        record = _mock_agentrx_record()
        record["failures"] = [
            {
                "failure_id": 1,
                "step_number": 1,
                "step_reason": "unknown",
                "failure_category": "Some Unknown Category",
                "category_reason": "unknown",
                "failed_agent": "Assistant",
            }
        ]
        record["root_cause"] = {"failure_id": 1, "reason_for_root_cause": "unknown"}
        traj = adapter.convert_simulation(record)
        assert traj.ground_truth.failure_categories == ["process.planning_failure"]


# ---------------------------------------------------------------------------
# load_dataset tests
# ---------------------------------------------------------------------------

class TestLoadDataset:

    def test_load_from_jsonl_files(self, tmp_path):
        adapter = AgentRxAdapter()
        # Write two records to a JSONL file
        records = [_mock_agentrx_record(), _mock_agentrx_record()]
        jsonl_file = tmp_path / "tau_retail_dataset.jsonl"
        jsonl_file.write_text("\n".join(json.dumps(r) for r in records))

        trajectories = adapter.load_dataset(tmp_path)
        assert len(trajectories) == 2
        assert trajectories[0].trajectory_id == "agentrx_tau_retail_dataset_0000"
        assert trajectories[1].trajectory_id == "agentrx_tau_retail_dataset_0001"

    def test_load_multiple_files(self, tmp_path):
        adapter = AgentRxAdapter()
        # Two different domain files
        (tmp_path / "magentic_dataset.jsonl").write_text(
            json.dumps(_mock_magentic_record())
        )
        (tmp_path / "tau_retail_dataset.jsonl").write_text(
            json.dumps(_mock_agentrx_record())
        )

        trajectories = adapter.load_dataset(tmp_path)
        assert len(trajectories) == 2
        domains = {t.domain for t in trajectories}
        assert "retail" in domains
        assert "multi_agent" in domains

    def test_load_with_limit(self, tmp_path):
        adapter = AgentRxAdapter()
        records = [_mock_agentrx_record() for _ in range(10)]
        jsonl_file = tmp_path / "tau_retail_dataset.jsonl"
        jsonl_file.write_text("\n".join(json.dumps(r) for r in records))

        trajectories = adapter.load_dataset(tmp_path, limit=3)
        assert len(trajectories) == 3

    def test_load_raises_on_missing_dir(self, tmp_path):
        adapter = AgentRxAdapter()
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="No AgentRx JSONL files"):
            adapter.load_dataset(empty_dir)

    def test_skips_blank_lines(self, tmp_path):
        adapter = AgentRxAdapter()
        content = (
            json.dumps(_mock_agentrx_record()) + "\n"
            "\n"
            + json.dumps(_mock_agentrx_record()) + "\n"
        )
        (tmp_path / "tau_retail_dataset.jsonl").write_text(content)
        trajectories = adapter.load_dataset(tmp_path)
        assert len(trajectories) == 2
