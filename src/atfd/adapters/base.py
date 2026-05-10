"""Abstract base class for dataset adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from atfd.schema import Trajectory


class DatasetAdapter(ABC):
    """Base class for converting dataset-specific formats into ATFD Trajectory objects."""

    @abstractmethod
    def convert_simulation(self, sim: dict, task: dict | None = None) -> Trajectory:
        """Convert a single simulation run dict into a Trajectory.

        Args:
            sim: Dataset-specific simulation/run dict.
            task: Optional task definition dict providing additional context.

        Returns:
            A fully populated Trajectory object.
        """

    @abstractmethod
    def load_dataset(self, data_dir: Path, limit: int = 0) -> list[Trajectory]:
        """Load all trajectories from a local data directory.

        Args:
            data_dir: Root directory containing the downloaded dataset files.
            limit: Maximum number of trajectories to return. 0 means no limit.

        Returns:
            List of Trajectory objects.
        """
