"""Compute DR/FPR with Wilson CIs for all result directories.

Produces the exact LaTeX-ready numbers for the paper's main results table.
Matches ground truth from tau-bench adapter for tau_* trajectory IDs,
infers from trajectory ID naming for synthetic/swe-bench.

Usage:
    python scripts/compute_all_metrics.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from atfd.adapters.tau_bench import TauBenchAdapter
from atfd.adapters.swe_bench import SweBenchAdapter
from atfd.adapters.toolathlon import ToolathlonAdapter
from atfd.metrics import detection_rate, false_positive_rate, f1_score, _has_error_or_warning, _has_error
from atfd.schema import JudgeOutput, Outcome

REPO = Path(__file__).resolve().parents[1]
RAW_DIR = REPO / "results" / "raw"


def load_all_gt():
    gt = {}
    for domain in ["retail", "airline", "telecom"]:
        adapter = TauBenchAdapter(domain=domain)
        try:
            trajs = adapter.load_dataset(REPO / "data" / "tau_bench", limit=0)
            for t in trajs:
                gt[t.trajectory_id] = t.ground_truth.outcome
        except Exception:
            pass
    for sub in ["openhands", "swe-agent"]:
        try:
            adapter = SweBenchAdapter(submission=sub)
            trajs = adapter.load_dataset(REPO / "data" / "swe_bench", limit=0)
            for t in trajs:
                gt[t.trajectory_id] = t.ground_truth.outcome
        except Exception:
            pass
    try:
        adapter = ToolathlonAdapter()
        trajs = adapter.load_dataset(REPO / "data" / "toolathlon", limit=0)
        for t in trajs:
            gt[t.trajectory_id] = t.ground_truth.outcome
    except Exception:
        pass
    return gt


def infer_outcome(tid, all_gt):
    if tid in all_gt:
        return all_gt[tid]
    tl = tid.lower()
    if "pass" in tl:
        return Outcome.PASS
    if "degraded" in tl:
        return Outcome.DEGRADED
    return Outcome.FAIL


def process_dir(dirpath, tau_gt):
    for f in sorted(dirpath.glob("*_raw.json")):
        records = json.loads(f.read_text())
        outputs = [JudgeOutput.model_validate(r) for r in records]
        gt_outcomes = [infer_outcome(o.trajectory_id, tau_gt) for o in outputs]

        n = len(outputs)
        n_fail = sum(1 for g in gt_outcomes if g == Outcome.FAIL)
        n_pass = sum(1 for g in gt_outcomes if g == Outcome.PASS)
        n_detected = sum(1 for g, o in zip(gt_outcomes, outputs) if g == Outcome.FAIL and _has_error_or_warning(o))
        n_fp = sum(1 for g, o in zip(gt_outcomes, outputs) if g == Outcome.PASS and _has_error(o))

        dr = detection_rate(gt_outcomes, outputs)
        fpr = false_positive_rate(gt_outcomes, outputs)
        f1 = f1_score(gt_outcomes, outputs)

        dr_str = f"{dr.value*100:.1f} [{dr.ci_low*100:.1f}, {dr.ci_high*100:.1f}]" if dr.value is not None else "N/A"
        fpr_str = f"{fpr.value*100:.1f} [{fpr.ci_low*100:.1f}, {fpr.ci_high*100:.1f}]" if fpr.value is not None else "N/A"

        return {
            "dir": dirpath.name,
            "file": f.name,
            "n": n,
            "n_fail": n_fail,
            "n_pass": n_pass,
            "detected": n_detected,
            "fp": n_fp,
            "dr": dr_str,
            "fpr": fpr_str,
            "f1": f"{f1:.3f}",
            "dr_val": dr.value * 100 if dr.value is not None else None,
            "fpr_val": fpr.value * 100 if fpr.value is not None else None,
        }
    return None


def main():
    tau_gt = load_all_gt()
    print(f"Ground truth loaded: {len(tau_gt)} trajectories\n")

    dirs_of_interest = [
        "naive_retail", "naive_airline", "naive_swebench", "naive_atbench",
        "naive_synthetic", "naive_telecom",
        "toolathlon_fixed",
        "groq_llama4scout_retail", "llama4scout_retail_100",
        "llama4scout_airline", "llama4scout_airline_100",
        "llama4scout_swebench", "llama4scout_swebench_100",
        "claude_sonnet_retail", "claude_sonnet_retail_100",
        "claude_sonnet_airline", "claude_sonnet_airline_100",
        "claude_sonnet_swebench", "claude_swebench_100", "claude_atbench",
        "gpt5_retail_100", "gpt5_airline_100", "gpt5_swebench_100",
        "synthetic_150",
    ]

    print(f"{'Directory':<35} {'N':>4} {'Fail':>4} {'Det':>4} {'FP':>3} {'DR':>25} {'FPR':>25} {'F1':>6}")
    print("-" * 120)

    for dirn in dirs_of_interest:
        dirpath = RAW_DIR / dirn
        if not dirpath.exists():
            continue
        result = process_dir(dirpath, tau_gt)
        if result:
            print(f"{result['dir']:<35} {result['n']:>4} {result['n_fail']:>4} {result['detected']:>4} {result['fp']:>3} {result['dr']:>25} {result['fpr']:>25} {result['f1']:>6}")

    # Also check for toolathlon per-judge
    toolpath = RAW_DIR / "toolathlon_fixed"
    if toolpath.exists():
        print(f"\n{'=== Toolathlon per-judge ==='}")
        for f in sorted(toolpath.glob("*_raw.json")):
            records = json.loads(f.read_text())
            outputs = [JudgeOutput.model_validate(r) for r in records]
            gt_outcomes = [infer_outcome(o.trajectory_id, tau_gt) for o in outputs]
            dr = detection_rate(gt_outcomes, outputs)
            fpr = false_positive_rate(gt_outcomes, outputs)
            dr_str = f"{dr.value*100:.1f}" if dr.value is not None else "N/A"
            fpr_str = f"{fpr.value*100:.1f}" if fpr.value is not None else "N/A"
            print(f"  {f.stem:<40} n={len(outputs)} DR={dr_str}% FPR={fpr_str}%")


if __name__ == "__main__":
    main()
