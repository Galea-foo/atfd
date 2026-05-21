#!/usr/bin/env python3
"""LangSmith baseline evaluation for ATFD benchmark.

Measures: how many eval rules must be written, setup time, detection rate.
This script IS the configuration effort — every line here is what a user
must write to get LangSmith to detect agent trajectory failures.

Usage:
    LANGSMITH_API_KEY=lsv2_... python baselines/langsmith/run_langsmith_eval.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from langsmith import Client
from langsmith.evaluation import evaluate

from atfd.adapters.synthetic import SyntheticAdapter
from atfd.adapters.toolathlon import ToolathlonAdapter
from atfd.schema import Trajectory

# ── Timer starts here ── (measuring total setup + config time)
SETUP_START = time.monotonic()

client = Client()
ROOT = Path(__file__).parent.parent.parent


# ═══════════════════════════════════════════════════════════════════
# EVAL RULE 1: Tool Error Detection
# Checks if any tool_result event has error=True
# ═══════════════════════════════════════════════════════════════════
def tool_error_evaluator(outputs: dict, reference_outputs: dict | None = None) -> dict:
    """Flag trajectories containing tool errors."""
    events = outputs.get("events", [])
    errors = [e for e in events if e.get("type") == "tool_result" and e.get("metadata", {}).get("error")]
    has_error = len(errors) > 0
    return {
        "key": "tool_error",
        "score": 0 if has_error else 1,
        "comment": f"Found {len(errors)} tool error(s)" if has_error else "No tool errors",
    }


# ═══════════════════════════════════════════════════════════════════
# EVAL RULE 2: Tool Loop Detection
# Checks if any tool is called more than 5 times
# ═══════════════════════════════════════════════════════════════════
def tool_loop_evaluator(outputs: dict, reference_outputs: dict | None = None) -> dict:
    """Flag trajectories with repeated tool calls (loop pattern)."""
    events = outputs.get("events", [])
    tool_counts: dict[str, int] = {}
    for e in events:
        if e.get("type") == "tool_call":
            name = e.get("metadata", {}).get("tool_name", e.get("content", "unknown"))
            tool_counts[name] = tool_counts.get(name, 0) + 1
    loops = {k: v for k, v in tool_counts.items() if v > 5}
    has_loop = len(loops) > 0
    return {
        "key": "tool_loop",
        "score": 0 if has_loop else 1,
        "comment": f"Loop detected: {loops}" if has_loop else "No loops",
    }


# ═══════════════════════════════════════════════════════════════════
# EVAL RULE 3: Abnormal Termination Detection
# Checks for infrastructure-level failures
# ═══════════════════════════════════════════════════════════════════
def termination_evaluator(outputs: dict, reference_outputs: dict | None = None) -> dict:
    """Flag trajectories that ended abnormally."""
    events = outputs.get("events", [])
    has_failure_event = any(
        e.get("type") == "tool_result" and e.get("metadata", {}).get("error")
        for e in events
    )
    last_event = events[-1] if events else {}
    abnormal = has_failure_event or last_event.get("type") == "tool_result"
    return {
        "key": "abnormal_termination",
        "score": 0 if abnormal else 1,
        "comment": "Abnormal termination detected" if abnormal else "Normal termination",
    }


# ═══════════════════════════════════════════════════════════════════
# EVAL RULE 4: Excessive Event Count
# Flags trajectories with unusually many events (potential loop/delegation issue)
# ═══════════════════════════════════════════════════════════════════
def event_count_evaluator(outputs: dict, reference_outputs: dict | None = None) -> dict:
    """Flag trajectories with excessive events."""
    events = outputs.get("events", [])
    count = len(events)
    excessive = count > 20
    return {
        "key": "excessive_events",
        "score": 0 if excessive else 1,
        "comment": f"{count} events (threshold: 20)" if excessive else f"{count} events (normal)",
    }


# ═══════════════════════════════════════════════════════════════════
# COMBINED EVALUATOR: Overall failure detection
# A trajectory fails if ANY evaluator flags it
# ═══════════════════════════════════════════════════════════════════
ALL_EVALUATORS = [
    tool_error_evaluator,
    tool_loop_evaluator,
    termination_evaluator,
    event_count_evaluator,
]


def combined_failure_evaluator(outputs: dict, reference_outputs: dict | None = None) -> dict:
    """Overall: did any evaluator flag this trajectory?"""
    any_flagged = False
    details = []
    for ev_fn in ALL_EVALUATORS:
        result = ev_fn(outputs, reference_outputs)
        if result["score"] == 0:
            any_flagged = True
            details.append(result["key"])
    return {
        "key": "failure_detected",
        "score": 0 if any_flagged else 1,
        "comment": f"Flagged by: {details}" if any_flagged else "No failures detected",
    }


def load_and_upload_dataset():
    """Load synthetic trajectories and create LangSmith dataset."""
    adapter = SyntheticAdapter()
    trajectories = adapter.load_dataset(ROOT / "datasets" / "synthetic")

    dataset_name = "atfd-synthetic-v2"

    # Check if dataset exists
    try:
        existing = client.read_dataset(dataset_name=dataset_name)
        print(f"Dataset '{dataset_name}' already exists (id={existing.id})")
        return dataset_name, trajectories
    except Exception:
        pass

    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="ATFD synthetic agent trajectories — 50 hand-crafted failures across 7 categories",
    )

    for traj in trajectories:
        events_dicts = [
            {"type": e.type.value, "content": e.content, "metadata": e.metadata}
            for e in traj.events
        ]
        client.create_example(
            inputs={"trajectory_id": traj.trajectory_id, "domain": traj.domain},
            outputs={"events": events_dicts},
            metadata={
                "ground_truth_outcome": traj.ground_truth.outcome.value,
                "failure_categories": traj.ground_truth.failure_categories,
            },
            dataset_id=dataset.id,
        )

    print(f"Created dataset '{dataset_name}' with {len(trajectories)} examples")
    return dataset_name, trajectories


def run_evaluation(dataset_name: str, trajectories: list[Trajectory]):
    """Run all evaluators against the dataset."""

    def predict(inputs: dict) -> dict:
        """Pass-through — we're evaluating trajectories, not generating predictions."""
        tid = inputs["trajectory_id"]
        traj = next((t for t in trajectories if t.trajectory_id == tid), None)
        if traj is None:
            return {"events": []}
        return {
            "events": [
                {"type": e.type.value, "content": e.content, "metadata": e.metadata}
                for e in traj.events
            ]
        }

    print("\nRunning LangSmith evaluation...")
    results = evaluate(
        predict,
        data=dataset_name,
        evaluators=[combined_failure_evaluator] + ALL_EVALUATORS,
        experiment_prefix="atfd-langsmith-baseline",
    )

    return results


def score_results(trajectories: list[Trajectory], results):
    """Score LangSmith results against ATFD ground truth."""
    # Map trajectory_id -> ground truth
    gt_map = {t.trajectory_id: t.ground_truth for t in trajectories}

    detected = 0
    total_fail = 0
    false_positives = 0
    total_pass = 0

    for r in results:
        tid = r.get("run", {}).get("inputs", {}).get("trajectory_id", "")
        if not tid:
            continue

        gt = gt_map.get(tid)
        if gt is None:
            continue

        is_fail = gt.outcome.value == "fail"
        # Check if combined evaluator flagged it
        flagged = False
        for eval_result in r.get("evaluation_results", {}).get("results", []):
            if eval_result.get("key") == "failure_detected" and eval_result.get("score") == 0:
                flagged = True
                break

        if is_fail:
            total_fail += 1
            if flagged:
                detected += 1
        else:
            total_pass += 1
            if flagged:
                false_positives += 1

    dr = detected / total_fail if total_fail > 0 else 0
    fpr = false_positives / total_pass if total_pass > 0 else 0

    return {
        "total": total_fail + total_pass,
        "total_fail": total_fail,
        "total_pass": total_pass,
        "detected": detected,
        "false_positives": false_positives,
        "detection_rate": dr,
        "false_positive_rate": fpr,
        "num_rules": len(ALL_EVALUATORS),
    }


def run_toolathlon_local() -> dict:
    """Load Toolathlon data and run the same 4 evaluators locally (no API upload required)."""
    adapter = ToolathlonAdapter()
    trajectories = adapter.load_dataset(ROOT / "data" / "toolathlon")

    print(f"\n═══ LangSmith × toolathlon (local) ({len(trajectories)} trajectories) ═══")

    fails = sum(1 for t in trajectories if t.ground_truth.outcome.value == "fail")
    passes = len(trajectories) - fails
    print(f"Ground truth: {fails} failures, {passes} passes")

    detected = 0
    false_positives = 0
    results_detail = []

    for traj in trajectories:
        events_dicts = [
            {"type": e.type.value, "content": e.content, "metadata": e.metadata}
            for e in traj.events
        ]
        output = {"events": events_dicts}

        combined = combined_failure_evaluator(output)
        flagged = combined["score"] == 0
        is_fail = traj.ground_truth.outcome.value == "fail"

        if is_fail and flagged:
            detected += 1
        if not is_fail and flagged:
            false_positives += 1

        triggered = [
            ev_fn(output)["key"]
            for ev_fn in ALL_EVALUATORS
            if ev_fn(output)["score"] == 0
        ]
        results_detail.append({
            "tid": traj.trajectory_id,
            "is_fail": is_fail,
            "flagged": flagged,
            "triggered": triggered,
        })

    dr = detected / fails * 100 if fails > 0 else 0
    fpr = false_positives / passes * 100 if passes > 0 else 0

    print(f"Detection Rate: {dr:.1f}% ({detected}/{fails})")
    print(f"False Positive Rate: {fpr:.1f}% ({false_positives}/{passes})")

    result = {
        "dataset": "toolathlon",
        "platform": "langsmith",
        "n": len(trajectories),
        "fails": fails,
        "passes": passes,
        "detected": detected,
        "false_positives": false_positives,
        "detection_rate": dr,
        "false_positive_rate": fpr,
        "num_rules": len(ALL_EVALUATORS),
    }

    out = ROOT / "results" / "raw" / "langsmith_toolathlon.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    print(f"Results saved to {out}")

    return result


def main():
    print("═══ LangSmith ATFD Baseline ═══\n")

    # Upload dataset
    dataset_name, trajectories = load_and_upload_dataset()

    # Run evaluation
    eval_results = run_evaluation(dataset_name, trajectories)

    # Measure setup time
    setup_time = time.monotonic() - SETUP_START
    print(f"\nTotal setup + run time: {setup_time:.1f}s")
    print(f"Number of eval rules written: {len(ALL_EVALUATORS)}")
    print(f"Lines of evaluator code: ~{sum(1 for _ in open(__file__))}")

    # Run Toolathlon locally (no API upload needed)
    run_toolathlon_local()

    print("\n═══ Done ═══")
    print(f"Check LangSmith UI for detailed results: https://smith.langchain.com")
    print(f"Dataset: {dataset_name}")


if __name__ == "__main__":
    main()
