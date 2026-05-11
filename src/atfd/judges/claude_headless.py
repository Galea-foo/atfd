"""Claude Code headless judge — uses `claude -p` CLI as LLM proxy.

No API key needed — uses the user's existing Claude Code auth.
"""
from __future__ import annotations

import json
import re
import subprocess
import time

from atfd.judges.base import Judge
from atfd.judges.prompts import (
    FAILURE_TAXONOMY_TEXT,
    QUALITY_RUBRICS,
    STAGE1_PROMPT,
    STAGE2_PROMPT,
    format_trajectory_for_prompt,
)
from atfd.schema import (
    CostReport,
    Finding,
    Infrastructure,
    JudgeOutput,
    Severity,
    Trajectory,
)

_DEFAULT_QUALITY_RUBRIC = """\
| Dimension      | 0 — Poor                    | 1 — Acceptable   | 2 — Excellent           |
|----------------|-----------------------------|------------------|-------------------------|
| completeness   | Request left unresolved     | Partially met    | Fully addressed         |
| clarity        | Confusing or vague response | Mostly clear     | Clear and precise       |
| efficiency     | Unnecessary steps           | Some inefficiency| Minimal, targeted steps |\
"""


class ClaudeHeadlessJudge(Judge):

    def __init__(self, model: str = "sonnet"):
        self._model = model

    @property
    def name(self) -> str:
        return f"claude_headless_{self._model}"

    def evaluate(self, trajectory: Trajectory) -> JudgeOutput:
        start = time.monotonic()
        findings: list[Finding] = []
        total_tokens = 0
        api_calls = 0

        traj_text = format_trajectory_for_prompt(trajectory.events)
        rubric_table = QUALITY_RUBRICS.get(trajectory.domain, _DEFAULT_QUALITY_RUBRIC)

        # Stage 1: failure detection
        prompt1 = STAGE1_PROMPT.format(
            taxonomy=FAILURE_TAXONOMY_TEXT,
            domain=trajectory.domain,
            task_description=trajectory.task_description or "(not provided)",
            trajectory_events=traj_text,
        )
        raw1, tokens1 = self._call_claude(prompt1)
        api_calls += 1
        total_tokens += tokens1

        stage1 = self._parse_json(raw1)
        outcome = stage1.get("outcome", "pass")

        if outcome == "fail":
            for cat in stage1.get("failure_categories", []):
                findings.append(Finding(
                    severity=Severity.ERROR,
                    category=cat,
                    description=stage1.get("reasoning", f"Failure: {cat}"),
                ))
            if not findings:
                findings.append(Finding(
                    severity=Severity.ERROR,
                    category="process.planning_failure",
                    description=stage1.get("reasoning", "Stage 1 detected failure"),
                ))
        else:
            # Stage 2: quality
            prompt2 = STAGE2_PROMPT.format(
                domain=trajectory.domain,
                task_description=trajectory.task_description or "(not provided)",
                trajectory_events=traj_text,
                rubric_table=rubric_table,
            )
            raw2, tokens2 = self._call_claude(prompt2)
            api_calls += 1
            total_tokens += tokens2

            stage2 = self._parse_json(raw2)
            for qcat in stage2.get("quality_categories", []):
                findings.append(Finding(
                    severity=Severity.WARNING,
                    category=qcat,
                    description=stage2.get("reasoning", f"Quality: {qcat}"),
                ))

        elapsed = time.monotonic() - start
        has_failure = outcome == "fail" or any(f.severity == Severity.ERROR for f in findings)

        return JudgeOutput(
            trajectory_id=trajectory.trajectory_id,
            has_failure=has_failure,
            findings=findings,
            cost=CostReport(
                dollar_cost=0.0,
                latency_seconds=elapsed,
                total_tokens=total_tokens,
                api_calls=api_calls,
                infrastructure=Infrastructure.API_KEY,
            ),
        )

    def _call_claude(self, prompt: str, max_retries: int = 3) -> tuple[str, int]:
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    ["claude", "-p", "--output-format", "json", "--model", self._model],
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode != 0:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return "", 0

                output = json.loads(result.stdout)
                text = output.get("result", "")
                tokens = output.get("usage", {}).get("input_tokens", 0) + output.get("usage", {}).get("output_tokens", 0)
                return text, tokens

            except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return "", 0

        return "", 0

    def _parse_json(self, raw: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {}
