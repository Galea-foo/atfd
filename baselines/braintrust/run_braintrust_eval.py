#!/usr/bin/env python3
"""Braintrust baseline evaluation for ATFD benchmark.

Measures: how many scorers must be written, setup time, detection rate.

Usage:
    BRAINTRUST_API_KEY=sk-... python baselines/braintrust/run_braintrust_eval.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import braintrust

from atfd.adapters.synthetic import SyntheticAdapter
from atfd.adapters.tau_bench import TauBenchAdapter

SETUP_START = time.monotonic()
ROOT = Path(__file__).parent.parent.parent


# ═══════════════════════════════════════════════════════════════════
# SCORER 1: Tool Error Detection
# ═══════════════════════════════════════════════════════════════════
def tool_error_scorer(output, expected=None):
    events = output.get("events", [])
    errors = [e for e in events if e.get("type") == "tool_result" and e.get("metadata", {}).get("error")]
    return 0 if errors else 1


# ═══════════════════════════════════════════════════════════════════
# SCORER 2: Tool Loop Detection
# ═══════════════════════════════════════════════════════════════════
def tool_loop_scorer(output, expected=None):
    events = output.get("events", [])
    counts: dict[str, int] = {}
    for e in events:
        if e.get("type") == "tool_call":
            name = e.get("metadata", {}).get("tool_name", e.get("content", "unknown"))
            counts[name] = counts.get(name, 0) + 1
    loops = {k: v for k, v in counts.items() if v > 5}
    return 0 if loops else 1


# ═══════════════════════════════════════════════════════════════════
# SCORER 3: Abnormal Termination
# ═══════════════════════════════════════════════════════════════════
def termination_scorer(output, expected=None):
    events = output.get("events", [])
    has_error = any(
        e.get("type") == "tool_result" and e.get("metadata", {}).get("error")
        for e in events
    )
    return 0 if has_error else 1


# ═══════════════════════════════════════════════════════════════════
# SCORER 4: Excessive Event Count
# ═══════════════════════════════════════════════════════════════════
def event_count_scorer(output, expected=None):
    count = len(output.get("events", []))
    return 0 if count > 20 else 1


# ═══════════════════════════════════════════════════════════════════
# COMBINED: Overall failure detection
# ═══════════════════════════════════════════════════════════════════
ALL_SCORERS = [tool_error_scorer, tool_loop_scorer, termination_scorer, event_count_scorer]


def failure_detected_scorer(output, expected=None):
    return 0 if any(s(output) == 0 for s in ALL_SCORERS) else 1


def load_trajectories(dataset_type="synthetic", limit=0):
    if dataset_type == "synthetic":
        adapter = SyntheticAdapter()
        return adapter.load_dataset(ROOT / "datasets" / "synthetic", limit=limit)
    elif dataset_type == "retail":
        adapter = TauBenchAdapter(domain="retail")
        return adapter.load_dataset(ROOT / "data" / "tau_bench", limit=limit)
    return []


def run_eval(dataset_type, limit=0):
    trajectories = load_trajectories(dataset_type, limit)
    print(f"\n═══ Braintrust × {dataset_type} ({len(trajectories)} trajectories) ═══")

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

        flagged = failure_detected_scorer(output) == 0
        is_fail = traj.ground_truth.outcome.value == "fail"

        if is_fail and flagged:
            detected += 1
        if not is_fail and flagged:
            false_positives += 1

        triggered = [s.__name__ for s in ALL_SCORERS if s(output) == 0]
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

    # Also run through Braintrust Eval for the UI
    eval_data = []
    for traj in trajectories:
        events_dicts = [
            {"type": e.type.value, "content": e.content, "metadata": e.metadata}
            for e in traj.events
        ]
        eval_data.append({
            "input": {"trajectory_id": traj.trajectory_id, "domain": traj.domain},
            "expected": {"outcome": traj.ground_truth.outcome.value},
            "metadata": {"failure_categories": traj.ground_truth.failure_categories},
        })

    traj_map = {t.trajectory_id: t for t in trajectories}

    def task(input_data):
        tid = input_data["trajectory_id"]
        traj = traj_map.get(tid)
        if not traj:
            return {"events": []}
        return {
            "events": [
                {"type": e.type.value, "content": e.content, "metadata": e.metadata}
                for e in traj.events
            ]
        }

    try:
        braintrust.Eval(
            f"atfd-{dataset_type}",
            data=lambda: eval_data,
            task=task,
            scores=[
                braintrust.Score(name="tool_error", scorer=tool_error_scorer),
                braintrust.Score(name="tool_loop", scorer=tool_loop_scorer),
                braintrust.Score(name="event_count", scorer=event_count_scorer),
                braintrust.Score(name="failure_detected", scorer=failure_detected_scorer),
            ],
        )
        print("Results uploaded to Braintrust UI")
    except Exception as e:
        print(f"Braintrust UI upload failed (non-critical): {e}")

    return {
        "dataset": dataset_type,
        "n": len(trajectories),
        "fails": fails,
        "passes": passes,
        "detected": detected,
        "false_positives": false_positives,
        "detection_rate": dr,
        "false_positive_rate": fpr,
        "num_scorers": len(ALL_SCORERS),
    }


def main():
    print("═══ Braintrust ATFD Baseline ═══")

    r_synth = run_eval("synthetic")
    r_retail = run_eval("retail", limit=50)

    setup_time = time.monotonic() - SETUP_START
    print(f"\n═══ Summary ═══")
    print(f"Total time: {setup_time:.1f}s")
    print(f"Scorers written: {len(ALL_SCORERS)}")

    for r in [r_synth, r_retail]:
        print(f"  {r['dataset']:10s} DR={r['detection_rate']:.1f}% FPR={r['false_positive_rate']:.1f}%")

    out = ROOT / "results" / "raw" / "braintrust_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r_synth, r_retail], indent=2))


if __name__ == "__main__":
    main()
