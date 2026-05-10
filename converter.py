from __future__ import annotations
"""Convert tau-bench SimulationRun → Galea TraceEvent[] format.

tau-bench structure (from data_model/simulation.py):
  SimulationRun.messages = list[Message]
  Message types: SystemMessage, AssistantMessage, UserMessage, ToolMessage, MultiToolMessage
  ToolCall: {id, name, arguments, requestor}
  ToolMessage: {id, role:"tool", content, requestor, error}

Galea trace event types we map to:
  run_started, run_completed, run_failed
  agent_started, agent_completed
  model_called
  tool_called, tool_completed, tool_failed
"""
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def convert_simulation(sim: dict, task: dict | None = None, domain: str = "retail") -> list[dict]:
    """Convert a single tau-bench simulation run to Galea trace events."""
    trace_id = f"trace_tau_{sim.get('id', uuid4().hex[:12])}"
    run_id = f"run_tau_{sim.get('id', uuid4().hex[:12])}"
    task_id = sim.get("task_id", "unknown")
    events: list[dict] = []
    seq = 0

    def ts(offset_ms: int = 0) -> str:
        nonlocal seq
        seq += 1
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t = base.timestamp() + (seq * 0.5) + (offset_ms / 1000)
        return datetime.fromtimestamp(t, tz=timezone.utc).isoformat()

    def evt(type_: str, **kwargs) -> dict:
        e = {
            "id": f"evt_{uuid4().hex[:10]}",
            "traceId": trace_id,
            "runId": run_id,
            "timestamp": ts(),
            "type": type_,
            "framework": "tau-bench",
        }
        e.update({k: v for k, v in kwargs.items() if v is not None})
        return e

    # run_started
    events.append(evt(
        "run_started",
        metadata={
            "domain": domain,
            "taskId": task_id,
            "input": task.get("user_scenario", {}).get("reason_for_call", "") if task else "",
        },
    ))

    # agent_started for the assistant agent
    events.append(evt("agent_started", agentId=f"{domain}_agent", metadata={"role": "primary assistant"}))

    messages = sim.get("messages") or []
    tool_call_map: dict[str, dict] = {}

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            continue

        if role == "user":
            # User turn = signal_received (user input to agent)
            events.append(evt(
                "signal_received",
                agentId=f"{domain}_agent",
                metadata={"signal": "user_message", "content": _truncate(content, 500)},
            ))

        elif role == "assistant":
            # Model call by assistant
            tool_calls = msg.get("tool_calls") or []
            events.append(evt(
                "model_called",
                agentId=f"{domain}_agent",
                metadata={
                    "model": "gpt-4.1",
                    "provider": "openai",
                    "outputTokens": len(content.split()) * 2 if content else 0,
                    "inputTokens": 150,
                    "latencyMs": 800,
                    "response": _truncate(content, 300) if content else None,
                    "toolCallCount": len(tool_calls),
                },
            ))

            # Tool calls initiated
            for tc in tool_calls:
                tc_id = tc.get("id", uuid4().hex[:8])
                tool_name = tc.get("name", "unknown_tool")
                tool_args = tc.get("arguments", {})
                if isinstance(tool_args, str):
                    import json
                    try:
                        tool_args = json.loads(tool_args)
                    except Exception:
                        tool_args = {"raw": tool_args}

                tool_event = evt(
                    "tool_called",
                    agentId=f"{domain}_agent",
                    toolId=tool_name,
                    metadata={
                        "callId": tc_id,
                        "args": tool_args,
                        "permission": _classify_tool_permission(tool_name, domain),
                    },
                )
                events.append(tool_event)
                tool_call_map[tc_id] = tool_event

        elif role == "tool":
            # Tool result
            tc_id = msg.get("id", "")
            is_error = msg.get("error", False)
            tool_name = _resolve_tool_name(tc_id, tool_call_map)

            if is_error:
                events.append(evt(
                    "tool_failed",
                    agentId=f"{domain}_agent",
                    toolId=tool_name,
                    metadata={
                        "callId": tc_id,
                        "error": _truncate(content, 300),
                    },
                ))
            else:
                events.append(evt(
                    "tool_completed",
                    agentId=f"{domain}_agent",
                    toolId=tool_name,
                    metadata={
                        "callId": tc_id,
                        "outputShape": _classify_output(content),
                        "latencyMs": 50,
                    },
                ))

    # agent_completed
    events.append(evt("agent_completed", agentId=f"{domain}_agent"))

    # run outcome
    termination = sim.get("termination_reason", "AGENT_STOP")
    reward_info = sim.get("reward_info") or {}
    reward = reward_info.get("reward", 1.0)

    if termination in ("AGENT_ERROR", "INFRASTRUCTURE_ERROR", "UNEXPECTED_ERROR", "TOO_MANY_ERRORS"):
        events.append(evt(
            "run_failed",
            metadata={
                "error": f"Terminated: {termination}",
                "reason": termination,
                "reward": reward,
            },
        ))
    else:
        events.append(evt(
            "run_completed",
            metadata={
                "terminationReason": termination,
                "reward": reward,
                "duration": sim.get("duration"),
                "agentCost": sim.get("agent_cost"),
            },
        ))

    return events


def extract_ground_truth(sim: dict) -> dict:
    """Extract ground-truth labels from tau-bench simulation for scoring."""
    reward_info = sim.get("reward_info") or {}
    reward = reward_info.get("reward", 1.0)
    termination = sim.get("termination_reason", "AGENT_STOP")

    failure_types: list[str] = []

    # db_check: {db_match: bool, db_reward: float}
    db_check = reward_info.get("db_check")
    if db_check and not db_check.get("db_match", True):
        failure_types.append("wrong_state_change")

    # action_checks: [{action: {...}, action_match: bool, action_reward: float}]
    action_checks = reward_info.get("action_checks") or []
    for ac in action_checks:
        if not ac.get("action_match", True):
            failure_types.append("wrong_action")

    # nl_assertions: [{assertion: str, passed: bool}] or similar
    nl_assertions = reward_info.get("nl_assertions") or []
    for nla in nl_assertions:
        if not nla.get("passed", True) and not nla.get("assertion_match", True):
            failure_types.append("wrong_communication")

    # communicate_checks
    communicate_checks = reward_info.get("communicate_checks") or []
    for cc in communicate_checks:
        if not cc.get("passed", True) and not cc.get("communicate_match", True):
            failure_types.append("missing_information")

    # reward_breakdown gives component-level signal
    breakdown = reward_info.get("reward_breakdown") or {}
    if breakdown.get("DB", 1.0) < 1.0 and "wrong_state_change" not in failure_types:
        failure_types.append("wrong_state_change")
    if breakdown.get("COMMUNICATE", 1.0) < 1.0 and "missing_information" not in failure_types:
        failure_types.append("missing_information")
    if breakdown.get("ACTION", 1.0) < 1.0 and "wrong_action" not in failure_types:
        failure_types.append("wrong_action")

    # env_assertions
    env_assertions = reward_info.get("env_assertions") or []
    for ea in env_assertions:
        if not ea.get("passed", True) and not ea.get("assertion_match", True):
            failure_types.append("env_violation")

    is_failure = reward < 1.0 or termination in (
        "AGENT_ERROR", "INFRASTRUCTURE_ERROR",
        "UNEXPECTED_ERROR", "TOO_MANY_ERRORS", "MAX_STEPS", "TIMEOUT"
    )

    # Hallucination check
    hall_check = sim.get("hallucination_check") or {}
    has_hallucination = bool(hall_check.get("hallucinations") or hall_check.get("has_hallucination"))

    return {
        "reward": reward,
        "is_failure": is_failure,
        "termination_reason": termination,
        "failure_types": failure_types,
        "has_hallucination": has_hallucination,
        "reward_breakdown": breakdown,
    }


def _truncate(s: str | None, max_len: int) -> str:
    if not s:
        return ""
    return s[:max_len] + "..." if len(s) > max_len else s


def _classify_tool_permission(tool_name: str, domain: str) -> str:
    """Heuristic: tools that modify state need approval."""
    write_tools = {
        "retail": ["exchange_delivered_order_items", "cancel_pending_order", "modify_pending_order_items",
                   "modify_pending_order_address", "modify_pending_order_payment"],
        "airline": ["cancel_reservation", "change_reservation", "book_reservation",
                    "update_reservation_passengers", "send_certificate"],
        "telecom": ["change_plan", "cancel_service", "add_service", "process_payment"],
    }
    if tool_name in write_tools.get(domain, []):
        return "approval_required"
    return "auto"


def _resolve_tool_name(call_id: str, call_map: dict) -> str:
    """Look up tool name from call map."""
    entry = call_map.get(call_id)
    if entry:
        return entry.get("toolId", "unknown_tool")
    return "unknown_tool"


def _classify_output(content: str | None) -> str:
    if not content:
        return "empty"
    if len(content) > 1000:
        return "large_json"
    if content.startswith("{") or content.startswith("["):
        return "json"
    return "text"
