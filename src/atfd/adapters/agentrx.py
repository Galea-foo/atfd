"""Convert AgentRx diagnostic trajectories to ATFD format.

AgentRx (Microsoft Research): 115 failed agent trajectories across 3 domains
(tau-bench retail, Magentic-One multi-agent, Flash incident response) with
step-level failure annotations and root cause identification.

Dataset: microsoft/AgentRx on HuggingFace
Paper: Barke et al., arXiv:2602.02475
"""
from __future__ import annotations

import json
from pathlib import Path

from atfd.adapters.base import DatasetAdapter
from atfd.schema import Event, EventType, GroundTruth, Outcome, Trajectory

# AgentRx failure_category → ATFD taxonomy mapping
CATEGORY_MAP: dict[str, str] = {
    "Instruction/Plan Adherence Failure": "process.planning_failure",
    "Invention of New Information": "communication.hallucination",
    "Invalid Invocation": "action.wrong_args",
    "Misinterpretation of Tool Output": "communication.wrong_response",
    "Intent-Plan Misalignment": "process.planning_failure",
    "Underspecified User Intent": "communication.missing_info",
    "Intent Not Supported": "action.missing_action",
    "Guardrails Triggered": "safety.policy_violation",
    "System Failure": "infrastructure.error",
}

# Filename prefix → domain name for trajectory IDs and metadata
_DOMAIN_MAP: dict[str, str] = {
    "tau_retail": "retail",
    "magentic": "multi_agent",
    "flash": "incident_response",
}


def _domain_from_filename(filename: str) -> str:
    """Infer domain from the JSONL filename."""
    for prefix, domain in _DOMAIN_MAP.items():
        if filename.startswith(prefix):
            return domain
    return "unknown"


class AgentRxAdapter(DatasetAdapter):

    def convert_simulation(self, sim: dict, task: dict | None = None) -> Trajectory:
        """Convert a single AgentRx record to an ATFD Trajectory.

        Args:
            sim: A single record from an AgentRx JSONL file. Must contain
                ``trajectory_snippet``, ``failures``, and ``root_cause``.
            task: Optional dict with ``filename`` and ``index`` keys used to
                generate the trajectory_id. If not provided, defaults are used.

        Returns:
            A Trajectory with outcome=FAIL (all AgentRx records are failures).
        """
        filename = (task or {}).get("filename", "agentrx")
        index = (task or {}).get("index", 0)
        domain = _domain_from_filename(filename)

        trajectory_id = f"agentrx_{filename}_{index:04d}"

        # --- Build events from trajectory_snippet ---
        snippet = sim.get("trajectory_snippet", [])
        events: list[Event] = []
        # Cap at 100 events (trajectories can be very long)
        for i, msg in enumerate(snippet[:100]):
            role = msg.get("role", "")
            content = str(msg.get("content", ""))[:2000]

            if role == "human":
                etype = EventType.USER_MESSAGE
            else:
                # All agent roles (Assistant, Orchestrator, WebSurfer, Coder,
                # FileSurfer, ComputerTerminal, etc.) → ASSISTANT_MESSAGE
                etype = EventType.ASSISTANT_MESSAGE

            events.append(Event(
                type=etype,
                timestamp=f"2026-01-01T00:{i // 60:02d}:{i % 60:02d}Z",
                content=content,
                metadata={"role": role, "index": msg.get("index", i)},
            ))

        # --- Map failure categories ---
        failures = sim.get("failures", [])
        root_cause = sim.get("root_cause", {})
        failure_summary = sim.get("failure_summary", "")

        # Determine primary ATFD category from root_cause
        root_failure_id = root_cause.get("failure_id")
        primary_category: str | None = None

        if root_failure_id is not None:
            # Find the root cause failure and use its category
            for f in failures:
                if f.get("failure_id") == root_failure_id:
                    rx_cat = f.get("failure_category", "")
                    primary_category = CATEGORY_MAP.get(rx_cat)
                    break

        # Collect all unique ATFD categories from all failures
        all_categories: list[str] = []
        if primary_category:
            all_categories.append(primary_category)
        for f in failures:
            rx_cat = f.get("failure_category", "")
            atfd_cat = CATEGORY_MAP.get(rx_cat)
            if atfd_cat and atfd_cat not in all_categories:
                all_categories.append(atfd_cat)

        # Fallback: if no categories mapped, use a default
        if not all_categories:
            all_categories = ["process.planning_failure"]

        task_instruction = sim.get("task_instruction", "")
        task_desc = f"AgentRx ({domain}): {task_instruction[:200]}"

        return Trajectory(
            trajectory_id=trajectory_id,
            source="synthetic",
            domain=domain,
            events=events,
            ground_truth=GroundTruth(
                outcome=Outcome.FAIL,
                failure_categories=all_categories,
                quality_categories=[],
                source_labels={},
                consensus="gold",
            ),
            task_description=task_desc,
        )

    def load_dataset(self, data_dir: Path, limit: int = 0) -> list[Trajectory]:
        """Load AgentRx trajectories from JSONL files in *data_dir*.

        Reads all ``*.jsonl`` files, treating each line as a separate trajectory
        record. The trajectory_id includes the filename and line index for
        traceability.

        Args:
            data_dir: Directory containing AgentRx JSONL files.
            limit: Maximum total trajectories to return. 0 means no limit.

        Returns:
            List of Trajectory objects.
        """
        files = sorted(data_dir.glob("*.jsonl"))
        if not files:
            raise FileNotFoundError(
                f"No AgentRx JSONL files found in {data_dir}"
            )

        trajectories: list[Trajectory] = []
        for f in files:
            stem = f.stem  # e.g. "tau_retail_dataset"
            for i, line in enumerate(f.read_text().splitlines()):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                task_info = {"filename": stem, "index": i}
                trajectories.append(self.convert_simulation(record, task=task_info))
                if limit > 0 and len(trajectories) >= limit:
                    return trajectories

        return trajectories
