"""Galea adapter — wraps Galea's investigation API.
Supports both heuristic and LLM-backed modes.
"""
from __future__ import annotations
import time
from uuid import uuid4
import httpx
from atfd.judges.base import Judge
from atfd.schema import CostReport, Finding, JudgeOutput, Severity, Trajectory


class GaleaJudge(Judge):

    DOMAIN_PRIORITIES = {
        "retail": ["correctness", "tool_safety", "audit"],
        "airline": ["correctness", "tool_safety", "audit", "regulatory_compliance"],
        "telecom": ["correctness", "tool_safety", "cost"],
        "coding": ["correctness", "tool_safety"],
        "synthetic": ["correctness", "tool_safety", "audit"],
    }

    def __init__(self, api_url: str = "http://localhost:8002", mode: str = "heuristic"):
        self.api_url = api_url.rstrip("/")
        self.mode = mode

    @property
    def name(self) -> str:
        return f"galea_{self.mode}"

    def evaluate(self, trajectory: Trajectory) -> JudgeOutput:
        start = time.monotonic()
        galea_events = self._to_galea_events(trajectory)
        project_id = f"atfd-{trajectory.domain}"

        with httpx.Client(timeout=60) as client:
            priorities = self.DOMAIN_PRIORITIES.get(trajectory.domain, ["correctness", "tool_safety"])
            client.post(f"{self.api_url}/v1/projects", json={
                "id": project_id, "name": f"ATFD {trajectory.domain}",
                "priorities": priorities,
            })
            # Ingest
            trace_id = galea_events[0]["traceId"] if galea_events else trajectory.trajectory_id
            client.post(
                f"{self.api_url}/v1/events",
                json={"events": galea_events},
                headers={"x-galea-project": project_id},
            )
            # Investigate
            resp = client.post(f"{self.api_url}/v1/traces/{trace_id}/summarize")

        elapsed = time.monotonic() - start
        findings: list[Finding] = []

        if resp.status_code == 200:
            result = resp.json()
            summary = result.get("summary") or {}
            for gf in summary.get("findings") or []:
                sev_map = {"error": Severity.ERROR, "warning": Severity.WARNING, "info": Severity.INFO}
                attr = gf.get("attribution")
                if attr is not None and not isinstance(attr, str):
                    attr = str(attr)
                findings.append(Finding(
                    severity=sev_map.get(gf.get("severity", "info"), Severity.INFO),
                    category=gf.get("category", "unknown"),
                    description=str(gf.get("description", "")),
                    attribution=attr if attr else None,
                ))

        return JudgeOutput(
            trajectory_id=trajectory.trajectory_id,
            has_failure=any(f.severity in (Severity.ERROR, Severity.WARNING) for f in findings),
            findings=findings,
            cost=CostReport(
                dollar_cost=0.0 if self.mode == "heuristic" else 0.02,
                latency_seconds=round(elapsed, 3),
                total_tokens=0, api_calls=2, infrastructure="api_key",
            ),
        )

    def _to_galea_events(self, trajectory: Trajectory) -> list[dict]:
        trace_id = f"trace_{trajectory.trajectory_id}"
        run_id = f"run_{trajectory.trajectory_id}"
        type_map = {
            "user_message": "signal_received", "assistant_message": "model_called",
            "tool_call": "tool_called", "tool_result": "tool_completed", "system": "signal_received",
        }
        events = []
        for event in trajectory.events:
            galea_type = type_map.get(event.type.value, "signal_received")
            if event.type.value == "tool_result" and event.metadata.get("error"):
                galea_type = "tool_failed"
            events.append({
                "id": f"evt_{uuid4().hex[:10]}", "traceId": trace_id, "runId": run_id,
                "timestamp": event.timestamp, "type": galea_type, "framework": "atfd-benchmark",
                "metadata": {"content": event.content[:300], **event.metadata},
            })
        return events
