"""Synthetic trajectory dataset adapter.

Loads hand-crafted trajectory JSON files from datasets/synthetic/trajectories/
and converts them into ATFD Trajectory objects.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

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

# Base timestamp for auto-generated event timestamps (one per second from this epoch).
_BASE_DT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _make_timestamp(index: int) -> str:
    """Return an ISO-8601 timestamp offset by ``index`` seconds from the base date.

    Produces timestamps of the form ``2026-01-01T00:00:XXZ``.
    """
    offset = _BASE_DT.timestamp() + index
    return datetime.fromtimestamp(offset, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


class SyntheticAdapter(DatasetAdapter):
    """Adapter for hand-crafted synthetic trajectory JSON files."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert_simulation(self, sim: dict, task: dict | None = None) -> Trajectory:
        """Convert a single trajectory dict (loaded from JSON) into a Trajectory.

        Args:
            sim: The parsed JSON dict representing one synthetic trajectory.
            task: Unused for synthetic trajectories; accepted for interface compliance.

        Returns:
            A fully populated Trajectory with source=SYNTHETIC and consensus=GOLD.
        """
        trajectory_id: str = sim["trajectory_id"]
        domain: str = sim.get("domain", "unknown")
        description: str = sim.get("description", "")

        events = self._extract_events(sim.get("events", []))
        ground_truth = self._extract_ground_truth(sim["ground_truth"])

        return Trajectory(
            trajectory_id=trajectory_id,
            source=Source.SYNTHETIC,
            domain=domain,
            events=events,
            ground_truth=ground_truth,
            task_description=description,
        )

    def load_dataset(self, data_dir: Path, limit: int = 0) -> list[Trajectory]:
        """Load all *.json trajectory files from ``data_dir/trajectories/``.

        Args:
            data_dir: Root synthetic dataset directory (contains a ``trajectories/``
                      subdirectory).
            limit: Maximum number of trajectories to return. 0 means no limit.

        Returns:
            List of Trajectory objects, one per JSON file found.
        """
        trajectories_dir = data_dir / "trajectories"
        if not trajectories_dir.exists():
            return []

        json_files = sorted(trajectories_dir.glob("*.json"))
        trajectories: list[Trajectory] = []

        for json_file in json_files:
            with json_file.open() as fh:
                sim = json.load(fh)
            trajectories.append(self.convert_simulation(sim))
            if limit and len(trajectories) >= limit:
                break

        return trajectories

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_events(self, raw_events: list[dict]) -> list[Event]:
        """Map raw event dicts to ATFD Event objects with auto-generated timestamps."""
        events: list[Event] = []
        for index, raw in enumerate(raw_events):
            event_type = EventType(raw["type"])
            events.append(
                Event(
                    type=event_type,
                    timestamp=_make_timestamp(index),
                    content=raw.get("content", ""),
                    metadata=raw.get("metadata", {}),
                )
            )
        return events

    def _extract_ground_truth(self, gt_dict: dict) -> GroundTruth:
        """Build a GroundTruth from the trajectory's ``ground_truth`` block."""
        outcome = Outcome(gt_dict["outcome"])
        failure_categories: list[str] = gt_dict.get("failure_categories", [])
        quality_categories: list[str] = gt_dict.get("quality_categories", [])

        source_label = SourceLabel(
            outcome=outcome,
            failure_categories=list(failure_categories),
            quality_categories=list(quality_categories),
            reasoning="hand-crafted synthetic trajectory",
        )

        return GroundTruth(
            outcome=outcome,
            failure_categories=failure_categories,
            quality_categories=quality_categories,
            source_labels={"synthetic": source_label},
            consensus=Consensus.GOLD,
        )
