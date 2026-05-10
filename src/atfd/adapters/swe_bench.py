"""SWE-bench dataset adapter.

Converts SWE-bench trajectory dicts (OpenHands and SWE-agent formats) into
ATFD Trajectory objects.
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

# Actions in OpenHands format that map to tool_call events.
_OPENHANDS_TOOL_ACTIONS = {"run", "read", "edit", "write", "browse", "browse_interactive"}


class SweBenchAdapter(DatasetAdapter):
    """Adapter for SWE-bench trajectory datasets (OpenHands and SWE-agent formats)."""

    def __init__(self, submission: str = "openhands") -> None:
        """
        Args:
            submission: Submission name / agent system (e.g. "openhands", "swe-agent").
                        Used to determine trajectory format and for load_dataset path.
        """
        self.submission = submission

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert_trajectory(self, traj: dict) -> Trajectory:
        """Convert a single SWE-bench trajectory dict to a Trajectory.

        Automatically detects format (OpenHands vs SWE-agent) based on the
        structure of the history field.

        Args:
            traj: SWE-bench trajectory dict with at least ``instance_id`` and
                  ``history`` (or ``trajectory``) fields.

        Returns:
            A fully populated Trajectory object.
        """
        instance_id = traj.get("instance_id", uuid4().hex[:12])
        trajectory_id = f"swe_{instance_id}"

        history = traj.get("history") or traj.get("trajectory") or []

        # Detect format: OpenHands uses dicts with "action"/"observation" keys;
        # SWE-agent uses a list of dicts with both "action" and "observation" as top-level keys.
        if history and isinstance(history[0], dict) and "action" in history[0] and "observation" in history[0]:
            events = self._convert_swe_agent(history)
        else:
            events = self._convert_openhands(history)

        ground_truth = self._extract_ground_truth(traj)

        task_description = traj.get("problem_statement", "")

        return Trajectory(
            trajectory_id=trajectory_id,
            source=Source.SWE_BENCH,
            domain="coding",
            events=events,
            ground_truth=ground_truth,
            task_description=task_description,
        )

    def convert_simulation(self, sim: dict, task: dict | None = None) -> Trajectory:
        """Interface-compatibility wrapper around convert_trajectory.

        Args:
            sim: SWE-bench trajectory dict.
            task: Ignored (SWE-bench embeds task context within the trajectory).

        Returns:
            A fully populated Trajectory object.
        """
        return self.convert_trajectory(sim)

    def load_dataset(self, data_dir: Path, limit: int = 0) -> list[Trajectory]:
        """Load trajectories from JSON files under data_dir/submission_name/.

        Scans for all ``*.json`` files inside ``data_dir/<submission>/`` and
        converts each one.  Files may contain a single trajectory dict or a
        list of trajectory dicts.

        Args:
            data_dir: Root directory containing per-submission sub-directories.
            limit: Maximum number of trajectories to return. 0 means no limit.

        Returns:
            List of Trajectory objects.
        """
        submission_dir = data_dir / self.submission
        if not submission_dir.exists():
            return []

        trajectories: list[Trajectory] = []
        for json_file in sorted(submission_dir.glob("*.json")):
            with json_file.open() as fh:
                data = json.load(fh)

            raw_list: list[dict] = data if isinstance(data, list) else [data]
            for raw in raw_list:
                trajectories.append(self.convert_trajectory(raw))
                if limit and len(trajectories) >= limit:
                    return trajectories

        return trajectories

    # ------------------------------------------------------------------
    # Format converters
    # ------------------------------------------------------------------

    def _convert_openhands(self, history: list[dict]) -> list[Event]:
        """Convert OpenHands history format to ATFD events.

        OpenHands uses a flat list where each entry is either:
        - an action dict: ``{"action": "<type>", "args": {...}}``
        - an observation dict: ``{"observation": "<type>", "content": "..."}``
        """
        events: list[Event] = []
        seq = [0]

        for entry in history:
            if not isinstance(entry, dict):
                continue

            action = entry.get("action")
            observation = entry.get("observation")

            if action is not None:
                args = entry.get("args", {}) or {}
                content = str(args)

                if action == "message":
                    msg_content = args.get("content", content)
                    events.append(Event(
                        type=EventType.USER_MESSAGE,
                        timestamp=self._make_timestamp(seq),
                        content=str(msg_content),
                        metadata={"action": action},
                    ))
                elif action in _OPENHANDS_TOOL_ACTIONS:
                    events.append(Event(
                        type=EventType.TOOL_CALL,
                        timestamp=self._make_timestamp(seq),
                        content=action,
                        metadata={"action": action, "args": args},
                    ))
                else:
                    # Unknown action — emit as assistant message
                    events.append(Event(
                        type=EventType.ASSISTANT_MESSAGE,
                        timestamp=self._make_timestamp(seq),
                        content=content,
                        metadata={"action": action},
                    ))

            elif observation is not None:
                obs_content = entry.get("content", "")
                events.append(Event(
                    type=EventType.TOOL_RESULT,
                    timestamp=self._make_timestamp(seq),
                    content=str(obs_content),
                    metadata={"observation": observation},
                ))

        return events

    def _convert_swe_agent(self, trajectory: list[dict]) -> list[Event]:
        """Convert SWE-agent trajectory format to ATFD events.

        SWE-agent uses a list of step dicts, each with both ``action`` and
        ``observation`` as top-level string fields (the action that was taken
        and its output).
        """
        events: list[Event] = []
        seq = [0]

        for step in trajectory:
            if not isinstance(step, dict):
                continue

            action = step.get("action", "")
            observation = step.get("observation", "")

            if action:
                events.append(Event(
                    type=EventType.TOOL_CALL,
                    timestamp=self._make_timestamp(seq),
                    content=str(action),
                    metadata={"format": "swe-agent"},
                ))

            if observation:
                events.append(Event(
                    type=EventType.TOOL_RESULT,
                    timestamp=self._make_timestamp(seq),
                    content=str(observation),
                    metadata={"format": "swe-agent"},
                ))

        return events

    # ------------------------------------------------------------------
    # Ground truth
    # ------------------------------------------------------------------

    def _extract_ground_truth(self, traj: dict) -> GroundTruth:
        """Derive outcome and failure categories from the ``resolved`` field."""
        resolved: bool = bool(traj.get("resolved", False))

        if resolved:
            outcome = Outcome.PASS
            failure_categories: list[str] = []
        else:
            outcome = Outcome.FAIL
            failure_categories = ["action.wrong_args"]

        source_label = SourceLabel(
            outcome=outcome,
            failure_categories=list(failure_categories),
            quality_categories=[],
            reasoning=f"resolved={resolved}",
        )

        return GroundTruth(
            outcome=outcome,
            failure_categories=failure_categories,
            quality_categories=[],
            source_labels={"swe_bench": source_label},
            consensus=Consensus.GOLD,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_timestamp(self, seq: list[int]) -> str:
        """Return an ISO-8601 timestamp offset by seq[0] * 0.5 seconds from epoch."""
        seq[0] += 1
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t = base.timestamp() + seq[0] * 0.5
        return datetime.fromtimestamp(t, tz=timezone.utc).isoformat()
