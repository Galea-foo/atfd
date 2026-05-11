"""Convert ATBench safety trajectories to ATFD format.

ATBench: 1,000 agent trajectories (503 safe, 497 unsafe) with
failure mode and risk source annotations.
"""
from __future__ import annotations

import json
from pathlib import Path

from atfd.adapters.base import DatasetAdapter
from atfd.schema import Event, EventType, GroundTruth, Outcome, Trajectory

FAILURE_MODE_MAP = {
    "provide_inaccurate_misleading_or_unverified_information": "communication.hallucination",
    "execute_unauthorized_or_harmful_actions": "safety.policy_violation",
    "leak_sensitive_or_private_information": "safety.data_leakage",
    "facilitate_illegal_or_unethical_activities": "safety.policy_violation",
    "bypass_safety_mechanisms_or_restrictions": "safety.permission_escalation",
    "generate_harmful_or_inappropriate_content": "safety.policy_violation",
    "misrepresent_capabilities_or_identity": "communication.hallucination",
    "manipulate_or_deceive_users": "communication.wrong_response",
    "cause_financial_or_reputational_damage": "safety.policy_violation",
    "compromise_system_integrity_or_availability": "safety.permission_escalation",
    "violate_consent_or_autonomy": "safety.policy_violation",
    "enable_surveillance_or_tracking": "safety.data_leakage",
    "spread_misinformation_or_propaganda": "communication.hallucination",
    "exploit_vulnerable_populations": "safety.policy_violation",
}


class ATBenchAdapter(DatasetAdapter):

    def convert_simulation(self, sim: dict, task: dict | None = None) -> Trajectory:
        item_id = sim.get("id", 0)
        label = sim.get("label", 0)  # 1=unsafe, 0=safe
        failure_mode = sim.get("failure_mode", "")
        risk_source = sim.get("risk_source", "")
        reason = sim.get("reason", "")

        events: list[Event] = []
        contents = sim.get("contents", [])
        conversation = contents[0] if contents else []

        for i, msg in enumerate(conversation):
            role = msg.get("role", "")
            content = str(msg.get("content", ""))[:2000]
            tool_calls = msg.get("tool_calls")

            if role == "user":
                events.append(Event(
                    type=EventType.USER_MESSAGE,
                    timestamp=f"2026-01-01T00:00:{i:02d}Z",
                    content=content,
                ))
            elif role == "agent" or role == "assistant":
                events.append(Event(
                    type=EventType.ASSISTANT_MESSAGE,
                    timestamp=f"2026-01-01T00:00:{i:02d}Z",
                    content=content,
                    metadata={"tool_calls": tool_calls} if tool_calls else {},
                ))
                if tool_calls:
                    for tc in (tool_calls if isinstance(tool_calls, list) else []):
                        fn = tc.get("function", {})
                        events.append(Event(
                            type=EventType.TOOL_CALL,
                            timestamp=f"2026-01-01T00:00:{i:02d}Z",
                            content=fn.get("name", "unknown"),
                            metadata={"tool_name": fn.get("name", "unknown"), "args": fn.get("arguments", "")},
                        ))
            elif role == "environment" or role == "tool":
                events.append(Event(
                    type=EventType.TOOL_RESULT,
                    timestamp=f"2026-01-01T00:00:{i:02d}Z",
                    content=content[:1000],
                ))

        atfd_category = FAILURE_MODE_MAP.get(failure_mode, "safety.policy_violation")
        failure_categories = [atfd_category] if label == 1 else []

        return Trajectory(
            trajectory_id=f"atbench_{item_id:04d}",
            source="synthetic",
            domain="safety",
            events=events,
            ground_truth=GroundTruth(
                outcome=Outcome.FAIL if label == 1 else Outcome.PASS,
                failure_categories=failure_categories,
                quality_categories=[],
                source_labels={},
                consensus="gold",
            ),
            task_description=f"ATBench: {risk_source} / {failure_mode}",
        )

    def load_dataset(self, data_dir: Path, limit: int = 0) -> list[Trajectory]:
        json_file = data_dir / "test.json"
        if not json_file.exists():
            raise FileNotFoundError(f"ATBench data not found at {json_file}")
        data = json.loads(json_file.read_text())
        if limit > 0:
            data = data[:limit]
        return [self.convert_simulation(item) for item in data]
