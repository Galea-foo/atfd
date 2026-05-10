"""Tau-bench dataset adapter.

Converts tau2-bench SimulationRun dicts into ATFD Trajectory objects.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from atfd.adapters.base import DatasetAdapter
from atfd.schema import (
    Consensus,
    Event,
    EventType,
    GroundTruth,
    Outcome,
    Source,
    SourceLabel,
    Trajectory,
)

# Preferred result file prefix; used when selecting among multiple candidates.
_PREFERRED_MODEL_SLUG = "gpt-4.1"


class TauBenchAdapter(DatasetAdapter):
    """Adapter for the tau2-bench benchmark dataset."""

    def __init__(self, domain: str) -> None:
        self.domain = domain

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert_simulation(self, sim: dict, task: dict | None = None) -> Trajectory:
        """Convert a single tau-bench simulation run to a Trajectory."""
        sim_id = sim.get("id", uuid4().hex[:12])
        trajectory_id = f"tau_{sim_id}"

        events = self._extract_events(sim)
        ground_truth = self._extract_ground_truth(sim)
        task_description = ""
        if task:
            task_description = (
                task.get("user_scenario", {}).get("reason_for_call", "")
            )

        return Trajectory(
            trajectory_id=trajectory_id,
            source=Source.TAU_BENCH,
            domain=self.domain,
            events=events,
            ground_truth=ground_truth,
            task_description=task_description,
        )

    def load_dataset(self, data_dir: Path, limit: int = 0) -> list[Trajectory]:
        """Load trajectories from tau-bench result JSON files.

        Looks inside ``data_dir/results/final/`` for JSON files that match
        the current domain.  Prefers files whose name contains the
        ``gpt-4.1`` model slug when multiple candidates exist.

        A sibling tasks index (``data_dir/domains/<domain>/tasks.json``)
        is loaded when present and used to enrich task descriptions.
        """
        results_dir = data_dir / "results" / "final"
        candidates = list(results_dir.glob(f"*_{self.domain}_*.json")) if results_dir.exists() else []

        if not candidates:
            return []

        # Prefer gpt-4.1 results; otherwise fall back to first alphabetically.
        preferred = [f for f in candidates if _PREFERRED_MODEL_SLUG in f.name]
        result_file = preferred[0] if preferred else sorted(candidates)[0]

        with result_file.open() as fh:
            data = json.load(fh)

        # tau2-bench result files may be a list of sims or a dict with a key.
        simulations: list[dict] = []
        if isinstance(data, list):
            simulations = data
        elif isinstance(data, dict):
            simulations = data.get("simulations", data.get("results", []))

        # Load task index if available.
        tasks_by_id: dict[str, dict] = {}
        tasks_file = data_dir / "domains" / self.domain / "tasks.json"
        if tasks_file.exists():
            with tasks_file.open() as fh:
                tasks_raw = json.load(fh)
            if isinstance(tasks_raw, list):
                tasks_by_id = {str(t.get("id", i)): t for i, t in enumerate(tasks_raw)}
            elif isinstance(tasks_raw, dict):
                tasks_by_id = {str(k): v for k, v in tasks_raw.items()}

        trajectories: list[Trajectory] = []
        for sim in simulations:
            task_id = str(sim.get("task_id", ""))
            task = tasks_by_id.get(task_id)
            trajectories.append(self.convert_simulation(sim, task))
            if limit and len(trajectories) >= limit:
                break

        return trajectories

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_timestamp(self, seq: list[int]) -> str:
        """Return an ISO-8601 timestamp offset by seq[0] * 0.5 seconds from epoch."""
        seq[0] += 1
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t = base.timestamp() + seq[0] * 0.5
        return datetime.fromtimestamp(t, tz=timezone.utc).isoformat()

    def _extract_events(self, sim: dict) -> list[Event]:
        """Map tau-bench messages to ATFD Event objects."""
        messages: list[dict] = sim.get("messages") or []
        events: list[Event] = []
        seq = [0]  # mutable counter for timestamp generation
        # Map tool call id → tool name for resolving tool results
        tool_call_map: dict[str, str] = {}

        for msg in messages:
            role = msg.get("role", "")
            content = str(msg.get("content", "") or "")

            if role == "system":
                events.append(Event(
                    type=EventType.SYSTEM,
                    timestamp=self._make_timestamp(seq),
                    content=content,
                    metadata={},
                ))

            elif role == "user":
                events.append(Event(
                    type=EventType.USER_MESSAGE,
                    timestamp=self._make_timestamp(seq),
                    content=content,
                    metadata={},
                ))

            elif role == "assistant":
                tool_calls: list[dict] = msg.get("tool_calls") or []

                # Emit assistant message if there is textual content OR no tool calls.
                if content or not tool_calls:
                    events.append(Event(
                        type=EventType.ASSISTANT_MESSAGE,
                        timestamp=self._make_timestamp(seq),
                        content=content,
                        metadata={"tool_call_count": len(tool_calls)},
                    ))

                # Emit one tool_call event per tool call in this turn.
                for tc in tool_calls:
                    tc_id = tc.get("id", uuid4().hex[:8])
                    tool_name = tc.get("name", "unknown_tool")
                    tool_call_map[tc_id] = tool_name

                    args = tc.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {"raw": args}

                    events.append(Event(
                        type=EventType.TOOL_CALL,
                        timestamp=self._make_timestamp(seq),
                        content=tool_name,
                        metadata={"call_id": tc_id, "arguments": args},
                    ))

            elif role == "tool":
                tc_id = msg.get("id", "")
                is_error = bool(msg.get("error", False))
                tool_name = tool_call_map.get(tc_id, "unknown_tool")

                events.append(Event(
                    type=EventType.TOOL_RESULT,
                    timestamp=self._make_timestamp(seq),
                    content=content,
                    metadata={
                        "call_id": tc_id,
                        "tool_name": tool_name,
                        "error": is_error,
                    },
                ))

        return events

    def _extract_ground_truth(self, sim: dict) -> GroundTruth:
        """Derive outcome and failure categories from tau-bench reward_info."""
        reward_info: dict = sim.get("reward_info") or {}
        reward: float = float(reward_info.get("reward", 1.0))
        breakdown: dict = reward_info.get("reward_breakdown") or {}
        termination: str = sim.get("termination_reason", "AGENT_STOP")

        failure_categories: list[str] = []

        # Map reward_breakdown components to taxonomy categories.
        db_score = float(breakdown.get("DB", 1.0))
        action_score = float(breakdown.get("ACTION", 1.0))
        communicate_score = float(breakdown.get("COMMUNICATE", 1.0))

        if db_score < 1.0:
            failure_categories.append("state.wrong_state")
        if action_score < 1.0:
            failure_categories.append("action.wrong_tool")
        if communicate_score < 1.0:
            failure_categories.append("communication.missing_info")

        # Map termination reasons to infrastructure failures.
        _ERROR_TERMS = {"AGENT_ERROR", "INFRASTRUCTURE_ERROR", "UNEXPECTED_ERROR", "TOO_MANY_ERRORS"}
        if termination in _ERROR_TERMS:
            failure_categories.append("infrastructure.error")
        elif termination == "MAX_STEPS":
            failure_categories.append("infrastructure.max_steps")
        elif termination == "TIMEOUT":
            failure_categories.append("infrastructure.timeout")

        # Determine overall outcome.
        is_failure = (
            reward < 1.0
            or termination in _ERROR_TERMS
            or termination in {"MAX_STEPS", "TIMEOUT"}
        )
        outcome = Outcome.FAIL if is_failure else Outcome.PASS

        # Programmatic labels only — mark as gold consensus.
        source_label = SourceLabel(
            outcome=outcome,
            failure_categories=list(failure_categories),
            quality_categories=[],
            reasoning=f"reward={reward}, termination={termination}",
        )

        return GroundTruth(
            outcome=outcome,
            failure_categories=failure_categories,
            quality_categories=[],
            source_labels={"tau_bench": source_label},
            consensus=Consensus.GOLD,
        )
