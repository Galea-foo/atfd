#!/usr/bin/env python3
"""Run GPT-5 (Codex CLI) judge on ATBench and Toolathlon.

These are the two missing cells in the evaluation matrix.
Uses CodexHeadlessJudge which calls `codex exec` — no API key needed.

Usage:
    PYTHONPATH=src python3 scripts/run_gpt5_missing_domains.py --dataset atbench
    PYTHONPATH=src python3 scripts/run_gpt5_missing_domains.py --dataset toolathlon
    PYTHONPATH=src python3 scripts/run_gpt5_missing_domains.py --dataset both
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from atfd.judges.codex_headless import CodexHeadlessJudge
from atfd.adapters.atbench import ATBenchAdapter
from atfd.adapters.toolathlon import ToolathlonAdapter
from atfd.metrics import detection_rate, false_positive_rate, wilson_ci
from atfd.schema import Outcome


ROOT = Path(__file__).resolve().parent.parent


def run_domain(judge, trajectories, domain_name, output_dir):
    print(f"\n{'='*60}")
    print(f"Running GPT-5 on {domain_name} ({len(trajectories)} trajectories)")
    print(f"{'='*60}")

    results = []
    fails = sum(1 for t in trajectories if t.ground_truth.outcome == Outcome.FAIL)
    passes = sum(1 for t in trajectories if t.ground_truth.outcome == Outcome.PASS)
    print(f"Ground truth: {fails} fail, {passes} pass, {len(trajectories)-fails-passes} degraded")

    for i, traj in enumerate(trajectories):
        start = time.monotonic()
        try:
            output = judge.evaluate(traj)
            elapsed = time.monotonic() - start
            results.append({
                "trajectory_id": traj.trajectory_id,
                "domain": traj.domain,
                "ground_truth": traj.ground_truth.outcome.value,
                "has_failure": output.has_failure,
                "findings": [{"severity": f.severity.value, "category": f.category, "description": f.description[:200]} for f in output.findings],
                "tokens": output.cost.total_tokens,
                "latency": output.cost.latency_seconds,
            })
            status = "FLAGGED" if output.has_failure else "pass"
            gt = traj.ground_truth.outcome.value
            correct = (output.has_failure and gt == "fail") or (not output.has_failure and gt == "pass")
            mark = "✓" if correct else "✗"
            print(f"  [{i+1}/{len(trajectories)}] {traj.trajectory_id[:30]:30s} gt={gt:8s} judge={status:7s} {mark} ({elapsed:.1f}s, {output.cost.total_tokens} tok)")
        except Exception as e:
            elapsed = time.monotonic() - start
            print(f"  [{i+1}/{len(trajectories)}] {traj.trajectory_id[:30]:30s} ERROR: {e} ({elapsed:.1f}s)")
            results.append({
                "trajectory_id": traj.trajectory_id,
                "domain": traj.domain,
                "ground_truth": traj.ground_truth.outcome.value,
                "has_failure": False,
                "findings": [],
                "tokens": 0,
                "latency": elapsed,
                "error": str(e),
            })

        # Save incrementally every 10 trajectories
        if (i + 1) % 10 == 0:
            out_path = output_dir / f"gpt5_{domain_name}_partial.json"
            out_path.write_text(json.dumps(results, indent=2))
            print(f"  [saved checkpoint: {len(results)} results]")

    # Final save
    out_path = output_dir / f"gpt5_{domain_name}.json"
    out_path.write_text(json.dumps(results, indent=2))

    # Compute metrics
    detected = sum(1 for r in results if r["has_failure"] and r["ground_truth"] == "fail")
    false_pos = sum(1 for r in results if r["has_failure"] and r["ground_truth"] == "pass")
    total_fail = sum(1 for r in results if r["ground_truth"] == "fail")
    total_pass = sum(1 for r in results if r["ground_truth"] == "pass")

    dr = detected / total_fail * 100 if total_fail > 0 else 0
    fpr = false_pos / total_pass * 100 if total_pass > 0 else 0

    dr_ci = wilson_ci(detected, total_fail) if total_fail > 0 else (0, 0)
    fpr_ci = wilson_ci(false_pos, total_pass) if total_pass > 0 else (0, 0)

    mean_tokens = sum(r["tokens"] for r in results) / len(results)
    mean_latency = sum(r["latency"] for r in results) / len(results)

    print(f"\n{'='*60}")
    print(f"Results: GPT-5 on {domain_name}")
    print(f"{'='*60}")
    print(f"DR: {dr:.1f}% [{dr_ci[0]*100:.1f}, {dr_ci[1]*100:.1f}] ({detected}/{total_fail})")
    print(f"FPR: {fpr:.1f}% [{fpr_ci[0]*100:.1f}, {fpr_ci[1]*100:.1f}] ({false_pos}/{total_pass})")
    print(f"Mean tokens/traj: {mean_tokens:.0f}")
    print(f"Mean latency: {mean_latency:.1f}s")
    print(f"Saved to: {out_path}")

    return {"domain": domain_name, "dr": dr, "fpr": fpr, "dr_ci": [dr_ci[0]*100, dr_ci[1]*100], "fpr_ci": [fpr_ci[0]*100, fpr_ci[1]*100]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["atbench", "toolathlon", "both"], required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    judge = CodexHeadlessJudge()
    output_dir = ROOT / "results" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.dataset in ("atbench", "both"):
        adapter = ATBenchAdapter()
        trajs = adapter.load_dataset(ROOT / "data" / "atbench", limit=args.limit or 200)
        run_domain(judge, trajs, "atbench_200", output_dir)

    if args.dataset in ("toolathlon", "both"):
        adapter = ToolathlonAdapter()
        trajs = adapter.load_dataset(ROOT / "data" / "toolathlon", limit=args.limit or 100)
        run_domain(judge, trajs, "toolathlon_100", output_dir)


if __name__ == "__main__":
    main()
