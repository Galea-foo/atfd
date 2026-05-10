"""Naive heuristic judge — zero-cost floor baseline.

Rules:
- Any tool_result event with metadata.error=True → Finding(severity=error, category="infrastructure.error")
- >5 tool_calls to the same tool (by tool_name in metadata, content as fallback) → Finding(severity=warning, category="process.tool_loop")
- No LLM calls. Zero dollar cost.
"""

import time
from collections import Counter

from atfd.judges.base import Judge
from atfd.schema import (
    CostReport,
    EventType,
    Finding,
    Infrastructure,
    JudgeOutput,
    Severity,
    Trajectory,
)

_TOOL_LOOP_THRESHOLD = 5  # more than this many calls to the same tool → loop


class NaiveHeuristicJudge(Judge):
    """Heuristic-only judge that uses no LLM and incurs zero cost."""

    @property
    def name(self) -> str:
        return "naive_heuristic"

    def evaluate(self, trajectory: Trajectory) -> JudgeOutput:
        start = time.monotonic()
        findings: list[Finding] = []

        # --- Rule 1: tool_result with error=True ---------------------------------
        for event in trajectory.events:
            if event.type == EventType.TOOL_RESULT and event.metadata.get("error"):
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        category="infrastructure.error",
                        description=(
                            f"tool_result event reported an error "
                            f"(content={event.content!r})"
                        ),
                    )
                )

        # --- Rule 2: >5 tool_calls to the same tool ------------------------------
        tool_call_counts: Counter = Counter()
        for event in trajectory.events:
            if event.type == EventType.TOOL_CALL:
                tool_key = event.metadata.get("tool_name") or event.content
                tool_call_counts[tool_key] += 1

        for tool_key, count in tool_call_counts.items():
            if count > _TOOL_LOOP_THRESHOLD:
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        category="process.tool_loop",
                        description=(
                            f"Tool '{tool_key}' called {count} times "
                            f"(threshold: {_TOOL_LOOP_THRESHOLD})"
                        ),
                    )
                )

        latency = time.monotonic() - start
        has_failure = any(
            f.severity in (Severity.ERROR, Severity.WARNING) for f in findings
        )

        return JudgeOutput(
            trajectory_id=trajectory.trajectory_id,
            has_failure=has_failure,
            findings=findings,
            cost=CostReport(
                dollar_cost=0.0,
                latency_seconds=latency,
                total_tokens=0,
                api_calls=0,
                infrastructure=Infrastructure.NONE,
            ),
        )
