"""Abstract base class for all ATFD judges."""

from abc import ABC, abstractmethod

from atfd.schema import JudgeOutput, Trajectory


class Judge(ABC):
    """Abstract base class that every judge must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the judge."""
        ...

    @abstractmethod
    def evaluate(self, trajectory: Trajectory) -> JudgeOutput:
        """Evaluate a single trajectory and return a JudgeOutput."""
        ...
