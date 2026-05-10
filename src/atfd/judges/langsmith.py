"""LangSmith adapter — requires manual eval rule configuration."""
from __future__ import annotations
import time
from atfd.judges.base import Judge
from atfd.schema import CostReport, Finding, JudgeOutput, Severity, Trajectory


class LangSmithJudge(Judge):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "langsmith"

    def evaluate(self, trajectory: Trajectory) -> JudgeOutput:
        raise NotImplementedError(
            "LangSmith adapter requires account setup + eval rule configuration. "
            "See baselines/langsmith/setup_notes.md"
        )
