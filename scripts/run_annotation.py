#!/usr/bin/env python3
"""Interactive human annotation tool for the ATFD IAA study.

Loads the 50 sampled trajectories from the manifest, presents each one
in the terminal, and collects human labels via stdin.  Progress is saved
after every annotation so the session can be resumed.

Usage:
    python scripts/run_annotation.py [--annotator NAME]

Labels are saved to results/annotations/<annotator>.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "results" / "annotations" / "sample_manifest.json"
OUTPUT_DIR = ROOT / "results" / "annotations"

# Dataset roots
TAU_BENCH_ROOT = ROOT / "datasets" / "tau_bench"
SWE_BENCH_DIR = ROOT / "data" / "swe_bench" / "openhands"
SYNTHETIC_DIR = ROOT / "datasets" / "synthetic" / "trajectories"
TOOLATHLON_DIR = ROOT / "data" / "toolathlon"

# ---------------------------------------------------------------------------
# Valid labels
# ---------------------------------------------------------------------------

VALID_OUTCOMES = {"pass", "degraded", "fail"}
VALID_CATEGORIES = {
    "action", "state", "communication", "quality",
    "process", "safety", "infrastructure",
}
VALID_SUBCATEGORIES = {
    "action.wrong_tool", "action.wrong_args", "action.missing_action",
    "state.wrong_state", "state.partial_state",
    "communication.wrong_response", "communication.missing_info",
    "communication.hallucination",
    "quality.shallow_output", "quality.suboptimal_approach",
    "quality.poor_tone", "quality.incomplete_analysis",
    "quality.low_confidence_output",
    "process.tool_loop", "process.infinite_delegation",
    "process.context_overflow", "process.planning_failure",
    "safety.permission_escalation", "safety.data_leakage",
    "safety.policy_violation", "safety.prompt_injection",
    "infrastructure.timeout", "infrastructure.error",
    "infrastructure.max_steps",
}
VALID_QUALITY_CATEGORIES = {
    "quality.shallow_output", "quality.suboptimal_approach",
    "quality.poor_tone", "quality.incomplete_analysis",
    "quality.low_confidence_output",
}


# ---------------------------------------------------------------------------
# Trajectory loaders
# ---------------------------------------------------------------------------

_TAU_CACHE: dict[str, list[dict]] = {}

_ERROR_TERMS = {
    "AGENT_ERROR", "INFRASTRUCTURE_ERROR",
    "UNEXPECTED_ERROR", "TOO_MANY_ERRORS",
}


def _load_tau_sims(domain: str) -> list[dict]:
    if domain in _TAU_CACHE:
        return _TAU_CACHE[domain]
    results_dir = TAU_BENCH_ROOT / "results" / "final"
    candidates = list(results_dir.glob(f"*_{domain}_*.json"))
    preferred = [f for f in candidates if "gpt-4.1" in f.name]
    path = preferred[0] if preferred else sorted(candidates)[0]
    with path.open() as fh:
        data = json.load(fh)
    sims = data if isinstance(data, list) else data.get("simulations", data.get("results", []))
    _TAU_CACHE[domain] = sims
    return sims


def load_trajectory(entry: dict) -> dict:
    """Load the raw trajectory data given a manifest entry.

    Returns a dict with keys: trajectory_id, domain, task_description, events.
    """
    loader = entry["loader"]
    args = entry["loader_args"]

    if loader == "tau_bench":
        sims = _load_tau_sims(args["domain"])
        sim = next((s for s in sims if str(s.get("id", "")) == str(args["sim_id"])), None)
        if sim is None:
            return {"trajectory_id": entry["trajectory_id"], "domain": args["domain"],
                    "task_description": "(simulation not found)", "events": []}
        # Load task description
        tasks_file = TAU_BENCH_ROOT / "domains" / args["domain"] / "tasks.json"
        task_desc = ""
        if tasks_file.exists():
            with tasks_file.open() as fh:
                tasks = json.load(fh)
            if isinstance(tasks, list):
                tid = str(sim.get("task_id", ""))
                for t in tasks:
                    if str(t.get("id", "")) == tid:
                        task_desc = t.get("user_scenario", {}).get("reason_for_call", "")
                        break
        messages = sim.get("messages", [])
        return {
            "trajectory_id": entry["trajectory_id"],
            "domain": args["domain"],
            "task_description": task_desc,
            "events": messages,
            "event_format": "tau_bench",
        }

    elif loader == "swe_bench":
        path = SWE_BENCH_DIR / args["filename"]
        with path.open() as fh:
            data = json.load(fh)
        history = data.get("history", data.get("trajectory", []))
        return {
            "trajectory_id": entry["trajectory_id"],
            "domain": "coding",
            "task_description": data.get("problem_statement", "")[:2000],
            "events": history[:80],  # cap for display
            "event_format": "swe_bench",
        }

    elif loader == "synthetic":
        path = SYNTHETIC_DIR / args["filename"]
        with path.open() as fh:
            data = json.load(fh)
        return {
            "trajectory_id": entry["trajectory_id"],
            "domain": data.get("domain", "mixed"),
            "task_description": data.get("description", ""),
            "events": data.get("events", []),
            "event_format": "synthetic",
        }

    elif loader == "toolathlon":
        path = TOOLATHLON_DIR / args["filename"]
        with path.open() as fh:
            data = json.load(fh)
        messages = data.get("messages", [])
        if isinstance(messages, str):
            messages = json.loads(messages)
        return {
            "trajectory_id": entry["trajectory_id"],
            "domain": "tool_use",
            "task_description": f"Toolathlon: {data.get('task_name', 'unknown')} ({data.get('modelname_run', 'unknown')})",
            "events": messages[:80],  # cap for display
            "event_format": "toolathlon",
        }

    else:
        return {"trajectory_id": entry["trajectory_id"], "domain": "unknown",
                "task_description": "(unknown loader)", "events": []}


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _truncate(text: str, max_len: int = 500) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "... [truncated]"


def display_trajectory(traj: dict, index: int, total: int) -> None:
    """Print a trajectory to the terminal for annotation."""
    print("\n" + "=" * 80)
    print(f"  Trajectory {index + 1} / {total}")
    print(f"  ID:     {traj['trajectory_id']}")
    print(f"  Domain: {traj['domain']}")
    print(f"  Task:   {_truncate(traj.get('task_description', '(none)'), 300)}")
    print("=" * 80)

    events = traj.get("events", [])
    fmt = traj.get("event_format", "unknown")

    for i, evt in enumerate(events):
        if isinstance(evt, dict):
            if fmt in ("tau_bench", "toolathlon"):
                role = evt.get("role", "?")
                content = _truncate(str(evt.get("content", "")))
                tool_calls = evt.get("tool_calls")
                print(f"\n  [{i}] {role}: {content}")
                if tool_calls and isinstance(tool_calls, list):
                    for tc in tool_calls:
                        fn = tc.get("function", tc)
                        name = fn.get("name", tc.get("name", "?"))
                        tc_args = str(fn.get("arguments", tc.get("arguments", "")))[:200]
                        print(f"       -> tool_call: {name}({tc_args})")
            elif fmt == "swe_bench":
                action = evt.get("action", "")
                observation = evt.get("observation", "")
                if action:
                    args = evt.get("args", {})
                    content = str(args.get("content", args.get("command", str(args))))[:300]
                    print(f"\n  [{i}] ACTION ({action}): {_truncate(content, 300)}")
                if observation:
                    obs_type = evt.get("observation", "")
                    obs_content = evt.get("content", str(evt))[:300]
                    print(f"       OBSERVATION ({obs_type}): {_truncate(str(obs_content), 300)}")
            elif fmt == "synthetic":
                etype = evt.get("type", "?")
                content = _truncate(str(evt.get("content", "")))
                print(f"\n  [{i}] {etype}: {content}")
            else:
                print(f"\n  [{i}] {_truncate(json.dumps(evt), 400)}")

    print("\n" + "-" * 80)


# ---------------------------------------------------------------------------
# Annotation collection
# ---------------------------------------------------------------------------

def collect_annotation(traj_id: str) -> dict:
    """Interactively collect a label from the human annotator."""
    print("\n  ANNOTATION")
    print(f"  Valid outcomes: pass, degraded, fail")

    # Outcome
    while True:
        outcome = input("  Outcome [pass/degraded/fail]: ").strip().lower()
        if outcome in VALID_OUTCOMES:
            break
        print(f"    Invalid. Choose from: {VALID_OUTCOMES}")

    annotation: dict = {
        "trajectory_id": traj_id,
        "outcome": outcome,
        "category": None,
        "subcategory": None,
        "quality_categories": [],
        "reasoning": "",
    }

    if outcome == "fail":
        # Category
        print(f"\n  Categories: {', '.join(sorted(VALID_CATEGORIES))}")
        while True:
            cat = input("  Failure category: ").strip().lower()
            if cat in VALID_CATEGORIES:
                annotation["category"] = cat
                break
            print(f"    Invalid. Choose from: {VALID_CATEGORIES}")

        # Subcategory (optional)
        matching = sorted(s for s in VALID_SUBCATEGORIES if s.startswith(cat + "."))
        if matching:
            print(f"\n  Subcategories: {', '.join(matching)} (or press Enter to skip)")
            sub = input("  Subcategory: ").strip().lower()
            if sub and sub in VALID_SUBCATEGORIES:
                annotation["subcategory"] = sub
            elif sub:
                print(f"    '{sub}' not recognized; skipping subcategory.")

    elif outcome == "degraded":
        # Quality categories (optional)
        print(f"\n  Quality categories: {', '.join(sorted(VALID_QUALITY_CATEGORIES))} (comma-separated, or Enter to skip)")
        qc_raw = input("  Quality categories: ").strip()
        if qc_raw:
            qcs = [q.strip().lower() for q in qc_raw.split(",")]
            valid_qcs = [q for q in qcs if q in VALID_QUALITY_CATEGORIES]
            annotation["quality_categories"] = valid_qcs

    # Reasoning (optional)
    reasoning = input("\n  Reasoning (optional, press Enter to skip): ").strip()
    annotation["reasoning"] = reasoning

    return annotation


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="ATFD human annotation tool")
    parser.add_argument("--annotator", type=str, default="annotator_1",
                        help="Annotator name (used for output filename)")
    args = parser.parse_args()

    # Load manifest
    if not MANIFEST.exists():
        print(f"ERROR: Manifest not found at {MANIFEST}")
        print("Run scripts/sample_iaa_trajectories.py first.")
        sys.exit(1)

    with MANIFEST.open() as fh:
        manifest = json.load(fh)

    # Load or resume progress
    output_path = OUTPUT_DIR / f"{args.annotator}.json"
    annotations: list[dict] = []
    done_ids: set[str] = set()

    if output_path.exists():
        with output_path.open() as fh:
            annotations = json.load(fh)
        done_ids = {a["trajectory_id"] for a in annotations}
        print(f"Resuming: {len(done_ids)} / {len(manifest)} already annotated.")

    remaining = [e for e in manifest if e["trajectory_id"] not in done_ids]

    if not remaining:
        print("All trajectories already annotated. Nothing to do.")
        sys.exit(0)

    print(f"\n{'=' * 60}")
    print(f"  ATFD Annotation Session — Annotator: {args.annotator}")
    print(f"  {len(remaining)} trajectories remaining ({len(done_ids)} done)")
    print(f"  Type 'q' at any outcome prompt to quit and save.")
    print(f"{'=' * 60}")

    for i, entry in enumerate(remaining):
        traj_data = load_trajectory(entry)
        global_idx = done_ids.__len__() + i
        display_trajectory(traj_data, global_idx, len(manifest))

        # Allow quitting
        print(f"\n  Ground truth: {entry['gt_outcome']} (for reference — annotate independently)")

        # Check for quit
        outcome_input = input("\n  Outcome [pass/degraded/fail] (or 'q' to quit): ").strip().lower()
        if outcome_input == "q":
            print(f"\n  Saving progress ({len(annotations)} annotations)...")
            break

        # Push back the input for the collector
        # We need to re-collect since we already consumed the first input
        if outcome_input not in VALID_OUTCOMES:
            print(f"    Invalid outcome '{outcome_input}', skipping this trajectory.")
            continue

        annotation: dict = {
            "trajectory_id": entry["trajectory_id"],
            "outcome": outcome_input,
            "category": None,
            "subcategory": None,
            "quality_categories": [],
            "reasoning": "",
        }

        if outcome_input == "fail":
            print(f"\n  Categories: {', '.join(sorted(VALID_CATEGORIES))}")
            while True:
                cat = input("  Failure category: ").strip().lower()
                if cat in VALID_CATEGORIES:
                    annotation["category"] = cat
                    break
                if cat == "q":
                    break
                print(f"    Invalid. Choose from: {VALID_CATEGORIES}")

            if cat == "q":
                break

            matching = sorted(s for s in VALID_SUBCATEGORIES if s.startswith(cat + "."))
            if matching:
                print(f"\n  Subcategories: {', '.join(matching)} (Enter to skip)")
                sub = input("  Subcategory: ").strip().lower()
                if sub in VALID_SUBCATEGORIES:
                    annotation["subcategory"] = sub

        elif outcome_input == "degraded":
            print(f"\n  Quality categories: {', '.join(sorted(VALID_QUALITY_CATEGORIES))} (comma-sep, Enter to skip)")
            qc_raw = input("  Quality categories: ").strip()
            if qc_raw:
                qcs = [q.strip().lower() for q in qc_raw.split(",")]
                annotation["quality_categories"] = [q for q in qcs if q in VALID_QUALITY_CATEGORIES]

        reasoning = input("\n  Reasoning (optional): ").strip()
        annotation["reasoning"] = reasoning

        annotations.append(annotation)
        done_ids.add(entry["trajectory_id"])

        # Save after each annotation
        with output_path.open("w") as fh:
            json.dump(annotations, fh, indent=2)

    # Final save
    with output_path.open("w") as fh:
        json.dump(annotations, fh, indent=2)

    print(f"\n  Done. {len(annotations)} annotations saved to {output_path}")

    # Summary
    outcomes = {}
    for a in annotations:
        outcomes[a["outcome"]] = outcomes.get(a["outcome"], 0) + 1
    print(f"  Outcome distribution: {outcomes}")


if __name__ == "__main__":
    main()
