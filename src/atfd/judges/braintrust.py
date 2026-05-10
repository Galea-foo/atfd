"""Braintrust adapter — requires manual scorer configuration."""
from __future__ import annotations
import time
from atfd.judges.base import Judge
from atfd.schema import CostReport, Finding, JudgeOutput, Severity, Trajectory


class BraintrustJudge(Judge):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "braintrust"

    def evaluate(self, trajectory: Trajectory) -> JudgeOutput:
        raise NotImplementedError(
            "Braintrust adapter requires account setup + scorer configuration. "
            "See baselines/braintrust/setup_notes.md"
        )
