"""LLM-as-judge with two-stage evaluation (failure detection + quality assessment).

Supports GPT-4.1 (OpenAI), Claude Sonnet 4 (Anthropic), and Llama 4 Scout
(OpenAI-compatible endpoint).
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

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

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

MODEL_CONFIGS: dict[str, dict[str, Any]] = {
    "gpt-4.1": {
        "provider": "openai",
        "model_id": "gpt-4.1",
        "input_cost_per_m": 2.00,
        "output_cost_per_m": 8.00,
    },
    "claude-sonnet-4": {
        "provider": "anthropic",
        "model_id": "claude-sonnet-4-5",
        "input_cost_per_m": 3.00,
        "output_cost_per_m": 15.00,
    },
    "llama-4-scout": {
        "provider": "openai-compat",
        "model_id": "meta-llama/llama-4-scout",
        "input_cost_per_m": 0.18,
        "output_cost_per_m": 0.59,
    },
}

_DEFAULT_QUALITY_RUBRIC = """\
| Dimension      | 0 — Poor                    | 1 — Acceptable   | 2 — Excellent           |
|----------------|-----------------------------|------------------|-------------------------|
| completeness   | Request left unresolved     | Partially met    | Fully addressed         |
| clarity        | Confusing or vague response | Mostly clear     | Clear and precise       |
| efficiency     | Unnecessary steps           | Some inefficiency| Minimal, targeted steps |\
"""


class LLMJudge(Judge):
    """Two-stage LLM judge: Stage 1 detects failures, Stage 2 assesses quality."""

    def __init__(self, model_key: str, base_url: str | None = None) -> None:
        if model_key not in MODEL_CONFIGS:
            raise ValueError(
                f"Unknown model_key '{model_key}'. "
                f"Valid keys: {list(MODEL_CONFIGS.keys())}"
            )
        self._model_key = model_key
        self._config = MODEL_CONFIGS[model_key]
        self._base_url = base_url
        self._client: Any = None

    # ------------------------------------------------------------------
    # Judge interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return f"llm_judge_{self._model_key}"

    def evaluate(self, trajectory: Trajectory) -> JudgeOutput:
        start = time.monotonic()
        findings: list[Finding] = []
        total_input_tokens = 0
        total_output_tokens = 0
        api_calls = 0

        trajectory_text = format_trajectory_for_prompt(trajectory.events)
        rubric_table = QUALITY_RUBRICS.get(trajectory.domain, _DEFAULT_QUALITY_RUBRIC)

        # ---- Stage 1: failure detection ----------------------------------------
        stage1_prompt = STAGE1_PROMPT.format(
            taxonomy=FAILURE_TAXONOMY_TEXT,
            domain=trajectory.domain,
            task_description=trajectory.task_description or "(not provided)",
            trajectory_events=trajectory_text,
        )
        raw1, in1, out1 = self._call_model(stage1_prompt)
        api_calls += 1
        total_input_tokens += in1
        total_output_tokens += out1

        stage1 = self._parse_json(raw1)
        outcome = stage1.get("outcome", "pass")

        if outcome == "fail":
            failure_categories: list[str] = stage1.get("failure_categories", [])
            reasoning: str = stage1.get("reasoning", "")
            if not failure_categories:
                # Fallback: generic failure finding
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        category="process.planning_failure",
                        description=reasoning or "Stage 1 detected a failure.",
                    )
                )
            else:
                for cat in failure_categories:
                    findings.append(
                        Finding(
                            severity=Severity.ERROR,
                            category=cat,
                            description=reasoning or f"Failure detected: {cat}",
                        )
                    )
        else:
            # ---- Stage 2: quality assessment (only on pass) --------------------
            stage2_prompt = STAGE2_PROMPT.format(
                domain=trajectory.domain,
                task_description=trajectory.task_description or "(not provided)",
                trajectory_events=trajectory_text,
                rubric_table=rubric_table,
            )
            raw2, in2, out2 = self._call_model(stage2_prompt)
            api_calls += 1
            total_input_tokens += in2
            total_output_tokens += out2

            stage2 = self._parse_json(raw2)
            quality_categories: list[str] = stage2.get("quality_categories", [])
            stage2_reasoning: str = stage2.get("reasoning", "")
            for qcat in quality_categories:
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        category=qcat,
                        description=stage2_reasoning or f"Quality concern: {qcat}",
                    )
                )

        latency = time.monotonic() - start
        dollar_cost = self._compute_cost(total_input_tokens, total_output_tokens)
        has_failure = outcome == "fail" or any(
            f.severity == Severity.ERROR for f in findings
        )

        return JudgeOutput(
            trajectory_id=trajectory.trajectory_id,
            has_failure=has_failure,
            findings=findings,
            cost=CostReport(
                dollar_cost=dollar_cost,
                latency_seconds=latency,
                total_tokens=total_input_tokens + total_output_tokens,
                api_calls=api_calls,
                infrastructure=Infrastructure.API_KEY,
            ),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Lazy-init the API client for the configured provider."""
        if self._client is not None:
            return self._client

        provider = self._config["provider"]
        if provider == "openai":
            from openai import OpenAI  # type: ignore[import]

            self._client = OpenAI()
        elif provider == "anthropic":
            from anthropic import Anthropic  # type: ignore[import]

            self._client = Anthropic()
        elif provider == "openai-compat":
            from openai import OpenAI  # type: ignore[import]

            self._client = OpenAI(base_url=self._base_url or "https://api.together.xyz/v1")
        else:
            raise ValueError(f"Unknown provider: {provider}")

        return self._client

    def _call_model(self, prompt: str) -> tuple[str, int, int]:
        """Call the configured model and return (text, input_tokens, output_tokens)."""
        client = self._get_client()
        provider = self._config["provider"]
        model_id = self._config["model_id"]

        if provider in ("openai", "openai-compat"):
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            text = response.choices[0].message.content or ""
            usage = response.usage
            return text, usage.prompt_tokens, usage.completion_tokens

        elif provider == "anthropic":
            response = client.messages.create(
                model=model_id,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            text = response.content[0].text if response.content else ""
            return text, response.usage.input_tokens, response.usage.output_tokens

        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _parse_json(self, raw: str) -> dict[str, Any]:
        """Strip markdown code fences and parse JSON; return empty dict on error."""
        # Remove ```json ... ``` or ``` ... ``` fences
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {}

    def _compute_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Compute dollar cost from token counts."""
        cfg = self._config
        cost = (
            input_tokens / 1_000_000 * cfg["input_cost_per_m"]
            + output_tokens / 1_000_000 * cfg["output_cost_per_m"]
        )
        return round(cost, 8)
