"""Convert Toolathlon long-horizon tool-use trajectories to ATFD format.

Toolathlon: multi-model benchmark with 600+ tools, long-horizon tasks.
task_status.evaluation = true/false/null for pass/fail/crash.
"""
from __future__ import annotations

import json
from pathlib import Path

from atfd.adapters.base import DatasetAdapter
from atfd.schema import Event, EventType, GroundTruth, Outcome, Trajectory


class ToolathlonAdapter(DatasetAdapter):

    def convert_simulation(self, sim: dict, task: dict | None = None) -> Trajectory:
        request_id = sim.get("request_id", "unknown")
        task_name = sim.get("task_name", "unknown")
        model = sim.get("modelname_run", "unknown")

        status = sim.get("task_status", "{}")
        if isinstance(status, str):
            status = json.loads(status)
        evaluation = status.get("evaluation")
        running = status.get("running", "done")

        if evaluation is True:
            outcome = Outcome.PASS
            failure_cats: list[str] = []
        elif evaluation is False:
            outcome = Outcome.FAIL
            failure_cats = ["action.wrong_tool"]
        else:
            outcome = Outcome.FAIL
            failure_cats = ["infrastructure.max_steps"] if running == "max_turn_exceeded" else ["infrastructure.error"]

        messages = sim.get("messages", [])
        # Cap at 100 events (these trajectories can have 16k+ messages)
        events: list[Event] = []
        for i, msg in enumerate(messages[:100]):
            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = str(msg.get("content", ""))[:1000]
                tool_calls = msg.get("tool_calls")

                if role == "user":
                    etype = EventType.USER_MESSAGE
                elif role == "assistant":
                    etype = EventType.ASSISTANT_MESSAGE
                elif role == "tool":
                    etype = EventType.TOOL_RESULT
                else:
                    etype = EventType.SYSTEM

                events.append(Event(
                    type=etype,
                    timestamp=f"2026-01-01T00:{i//60:02d}:{i%60:02d}Z",
                    content=content,
                    metadata={"tool_calls": tool_calls} if tool_calls else {},
                ))

                if tool_calls and isinstance(tool_calls, list):
                    for tc in tool_calls:
                        fn = tc.get("function", {})
                        events.append(Event(
                            type=EventType.TOOL_CALL,
                            timestamp=f"2026-01-01T00:{i//60:02d}:{i%60:02d}Z",
                            content=fn.get("name", "unknown"),
                            metadata={"tool_name": fn.get("name", "unknown"), "args": fn.get("arguments", "")[:500]},
                        ))

        return Trajectory(
            trajectory_id=f"toolathlon_{request_id}",
            source="synthetic",
            domain="tool_use",
            events=events,
            ground_truth=GroundTruth(
                outcome=outcome,
                failure_categories=failure_cats,
                quality_categories=[],
                source_labels={},
                consensus="gold",
            ),
            task_description=f"Toolathlon: {task_name} ({model})",
        )

    def load_dataset(self, data_dir: Path, limit: int = 0) -> list[Trajectory]:
        files = sorted(data_dir.glob("traj_*.json"))
        if limit > 0:
            files = files[:limit]
        trajectories = []
        for f in files:
            data = json.loads(f.read_text())
            trajectories.append(self.convert_simulation(data))
        return trajectories
