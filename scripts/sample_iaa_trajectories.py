#!/usr/bin/env python3
"""Sample 50 trajectories for the IAA annotation study.

Distribution:
  - 25 fail  (5 retail, 5 airline, 5 SWE-bench, 5 synthetic, 5 Toolathlon)
  - 15 pass  (5 retail, 5 airline, 5 SWE-bench)
  - 10 degraded (from synthetic)

Uses the tau-bench adapter ground truth for retail/airline, the SWE-bench
`resolved` field, synthetic `ground_truth.outcome`, and Toolathlon
`task_status.evaluation`.

Writes results/annotations/sample_manifest.json with trajectory IDs,
source paths, and ground-truth labels.
"""

from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

TAU_RETAIL = ROOT / "datasets" / "tau_bench" / "results" / "final" / "gpt-4.1-2025-04-14_retail_default_gpt-4.1-2025-04-14_4trials.json"
TAU_AIRLINE = ROOT / "datasets" / "tau_bench" / "results" / "final" / "gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials.json"
SWE_BENCH_DIR = ROOT / "data" / "swe_bench" / "openhands"
SYNTHETIC_DIR = ROOT / "datasets" / "synthetic" / "trajectories"
TOOLATHLON_DIR = ROOT / "data" / "toolathlon"

OUTPUT = ROOT / "results" / "annotations" / "sample_manifest.json"

SEED = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_tau_sims(path: Path) -> list[dict]:
    with path.open() as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return data
    return data.get("simulations", data.get("results", []))


_ERROR_TERMS = {"AGENT_ERROR", "INFRASTRUCTURE_ERROR", "UNEXPECTED_ERROR", "TOO_MANY_ERRORS"}


def _tau_is_fail(sim: dict) -> bool:
    ri = sim.get("reward_info", {})
    reward = float(ri.get("reward", 1.0))
    term = sim.get("termination_reason", "AGENT_STOP")
    return reward < 1.0 or term in _ERROR_TERMS or term in {"MAX_STEPS", "TIMEOUT"}


def _make_tau_entry(sim: dict, domain: str, outcome: str) -> dict:
    sim_id = sim.get("id", "unknown")
    return {
        "trajectory_id": f"tau_{sim_id}",
        "source": "tau-bench",
        "domain": domain,
        "gt_outcome": outcome,
        "loader": "tau_bench",
        "loader_args": {"domain": domain, "sim_id": sim_id},
    }


def _make_swe_entry(filename: str, resolved: bool) -> dict:
    instance_id = filename.replace(".json", "")
    return {
        "trajectory_id": f"swe_{instance_id}",
        "source": "swe-bench",
        "domain": "coding",
        "gt_outcome": "pass" if resolved else "fail",
        "loader": "swe_bench",
        "loader_args": {"filename": filename},
    }


def _make_synthetic_entry(filename: str, outcome: str) -> dict:
    return {
        "trajectory_id": json.load(open(SYNTHETIC_DIR / filename))["trajectory_id"],
        "source": "synthetic",
        "domain": "mixed",
        "gt_outcome": outcome,
        "loader": "synthetic",
        "loader_args": {"filename": filename},
    }


def _make_toolathlon_entry(filename: str) -> dict:
    data = json.load(open(TOOLATHLON_DIR / filename))
    status = data.get("task_status", {})
    if isinstance(status, str):
        status = json.loads(status)
    evaluation = status.get("evaluation")
    outcome = "pass" if evaluation is True else "fail"
    request_id = data.get("request_id", "unknown")
    return {
        "trajectory_id": f"toolathlon_{request_id}",
        "source": "toolathlon",
        "domain": "tool_use",
        "gt_outcome": outcome,
        "loader": "toolathlon",
        "loader_args": {"filename": filename},
    }


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def sample() -> list[dict]:
    rng = random.Random(SEED)
    manifest: list[dict] = []

    # --- tau-bench retail ---
    retail_sims = _load_tau_sims(TAU_RETAIL)
    retail_fail = [s for s in retail_sims if _tau_is_fail(s)]
    retail_pass = [s for s in retail_sims if not _tau_is_fail(s)]
    for sim in rng.sample(retail_fail, min(5, len(retail_fail))):
        manifest.append(_make_tau_entry(sim, "retail", "fail"))
    for sim in rng.sample(retail_pass, min(5, len(retail_pass))):
        manifest.append(_make_tau_entry(sim, "retail", "pass"))

    # --- tau-bench airline ---
    airline_sims = _load_tau_sims(TAU_AIRLINE)
    airline_fail = [s for s in airline_sims if _tau_is_fail(s)]
    airline_pass = [s for s in airline_sims if not _tau_is_fail(s)]
    for sim in rng.sample(airline_fail, min(5, len(airline_fail))):
        manifest.append(_make_tau_entry(sim, "airline", "fail"))
    for sim in rng.sample(airline_pass, min(5, len(airline_pass))):
        manifest.append(_make_tau_entry(sim, "airline", "pass"))

    # --- SWE-bench ---
    swe_files = sorted([f for f in os.listdir(SWE_BENCH_DIR) if f.endswith(".json")])
    swe_pass = []
    swe_fail = []
    for f in swe_files:
        data = json.load(open(SWE_BENCH_DIR / f))
        if data.get("resolved", False):
            swe_pass.append(f)
        else:
            swe_fail.append(f)
    for f in rng.sample(swe_fail, min(5, len(swe_fail))):
        manifest.append(_make_swe_entry(f, resolved=False))
    for f in rng.sample(swe_pass, min(5, len(swe_pass))):
        manifest.append(_make_swe_entry(f, resolved=True))

    # --- Synthetic: 5 fail + 10 degraded ---
    synth_files = sorted([f for f in os.listdir(SYNTHETIC_DIR) if f.endswith(".json")])
    synth_fail = []
    synth_degraded = []
    for f in synth_files:
        data = json.load(open(SYNTHETIC_DIR / f))
        outcome = data["ground_truth"]["outcome"]
        if outcome == "fail":
            synth_fail.append(f)
        elif outcome == "degraded":
            synth_degraded.append(f)
    for f in rng.sample(synth_fail, min(5, len(synth_fail))):
        manifest.append(_make_synthetic_entry(f, "fail"))
    for f in rng.sample(synth_degraded, min(10, len(synth_degraded))):
        manifest.append(_make_synthetic_entry(f, "degraded"))

    # --- Toolathlon: 5 fail ---
    tool_files = sorted([f for f in os.listdir(TOOLATHLON_DIR) if f.endswith(".json")])
    tool_fail = []
    for f in tool_files:
        data = json.load(open(TOOLATHLON_DIR / f))
        status = data.get("task_status", {})
        if isinstance(status, str):
            status = json.loads(status)
        if status.get("evaluation") is not True:
            tool_fail.append(f)
    for f in rng.sample(tool_fail, min(5, len(tool_fail))):
        manifest.append(_make_toolathlon_entry(f))

    return manifest


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    manifest = sample()

    # Summary
    outcomes = {}
    sources = {}
    for entry in manifest:
        outcomes[entry["gt_outcome"]] = outcomes.get(entry["gt_outcome"], 0) + 1
        sources[entry["source"]] = sources.get(entry["source"], 0) + 1

    print(f"Sampled {len(manifest)} trajectories")
    print(f"  Outcomes: {outcomes}")
    print(f"  Sources:  {sources}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"  Written to: {OUTPUT}")


if __name__ == "__main__":
    main()
