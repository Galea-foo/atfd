"""Codex CLI headless judge — uses `codex exec` as LLM proxy for OpenAI models.

No API key needed — uses the user's existing Codex/ChatGPT auth.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import tempfile

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


class CodexHeadlessJudge(Judge):

    def __init__(self, model: str | None = None):
        self._model = model

    @property
    def name(self) -> str:
        return f"codex_headless_{self._model or 'default'}"

    def evaluate(self, trajectory: Trajectory) -> JudgeOutput:
        start = time.monotonic()
        findings: list[Finding] = []
        total_input_tokens = 0
        total_output_tokens = 0
        api_calls = 0

        traj_text = format_trajectory_for_prompt(trajectory.events)
        rubric_table = QUALITY_RUBRICS.get(trajectory.domain, _DEFAULT_QUALITY_RUBRIC)

        prompt1 = STAGE1_PROMPT.format(
            taxonomy=FAILURE_TAXONOMY_TEXT,
            domain=trajectory.domain,
            task_description=trajectory.task_description or "(not provided)",
            trajectory_events=traj_text,
        )
        raw1, in1, out1 = self._call_codex(prompt1)
        api_calls += 1
        total_input_tokens += in1
        total_output_tokens += out1

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
            prompt2 = STAGE2_PROMPT.format(
                domain=trajectory.domain,
                task_description=trajectory.task_description or "(not provided)",
                trajectory_events=traj_text,
                rubric_table=rubric_table,
            )
            raw2, in2, out2 = self._call_codex(prompt2)
            api_calls += 1
            total_input_tokens += in2
            total_output_tokens += out2

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
                total_tokens=total_input_tokens + total_output_tokens,
                api_calls=api_calls,
                infrastructure=Infrastructure.API_KEY,
            ),
        )

    def _call_codex(self, prompt: str, max_retries: int = 3) -> tuple[str, int, int]:
        for attempt in range(max_retries):
            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                    output_path = f.name

                cmd = [
                    "codex", "exec",
                    "--ephemeral",
                    "--skip-git-repo-check",
                    "--json",
                    "-o", output_path,
                    "-",
                ]
                if self._model:
                    cmd.insert(2, "--model")
                    cmd.insert(3, self._model)

                result = subprocess.run(
                    cmd,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )

                text = ""
                input_tokens = 0
                output_tokens = 0

                for line in result.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if event.get("type") == "item.completed":
                        item = event.get("item", {})
                        if item.get("type") == "agent_message":
                            text = item.get("text", "")

                    if event.get("type") == "turn.completed":
                        usage = event.get("usage", {})
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)

                if not text:
                    import pathlib
                    text = pathlib.Path(output_path).read_text().strip()

                return text, input_tokens, output_tokens

            except (subprocess.TimeoutExpired, Exception):
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return "", 0, 0

        return "", 0, 0

    def _parse_json(self, raw: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {}
