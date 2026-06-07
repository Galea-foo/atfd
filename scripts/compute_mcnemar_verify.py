"""Verify McNemar test and compute two-proportion z-test for FPR comparison.

Usage:
    python scripts/compute_mcnemar_verify.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

REPO = Path(__file__).resolve().parents[1]


def load_results_and_gt(judge_dir, judge_file, domain):
    """Load judge results and ground truth for a domain."""
    import os

    raw_path = REPO / "results" / "raw" / judge_dir / judge_file
    results = json.loads(raw_path.read_text())

    gt_map = {}
    if domain in ("retail", "airline"):
        from atfd.adapters.tau_bench import TauBenchAdapter
        adapter = TauBenchAdapter(domain=domain)
        trajs = adapter.load_dataset(REPO / "data" / "tau_bench", limit=0)
        for t in trajs:
            gt_map[t.trajectory_id] = t.ground_truth.outcome.value

    return results, gt_map


def mcnemar_test(claude_results, gpt5_results, gt_map):
    """Run McNemar test on paired binary detection outcomes."""
    matched = []
    for cr, gr in zip(claude_results, gpt5_results):
        tid_c = cr["trajectory_id"]
        tid_g = gr["trajectory_id"]
        gt_c = gt_map.get(tid_c, "fail")
        gt_g = gt_map.get(tid_g, "fail")

        c_detect = cr.get("has_failure", False)
        g_detect = gr.get("has_failure", False)
        c_correct = (gt_c == "fail" and c_detect) or (gt_c == "pass" and not c_detect)
        g_correct = (gt_g == "fail" and g_detect) or (gt_g == "pass" and not g_detect)
        matched.append((c_correct, g_correct))

    b = sum(1 for c, g in matched if c and not g)
    c = sum(1 for c, g in matched if not c and g)
    n = len(matched)

    if b + c == 0:
        print(f"  No disagreements (b={b}, c={c})")
        return

    chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    p = 1 - stats.chi2.cdf(chi2, df=1)
    print(f"  McNemar: b={b} (Claude right, GPT-5 wrong), c={c} (GPT-5 right, Claude wrong)")
    print(f"  chi2={chi2:.3f}, p={p:.4f} (n={n})")


def two_proportion_z_test(p1, n1, p2, n2, label):
    """Two-proportion z-test for comparing FPR."""
    p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    if se == 0:
        print(f"  {label}: SE=0, cannot compute z-test")
        return
    z = (p1 - p2) / se
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    print(f"  {label}: p1={p1:.3f} (n={n1}), p2={p2:.3f} (n={n2})")
    print(f"  z={z:.3f}, p={p:.4f}")


def main():
    print("=== McNemar Verification ===\n")

    for domain in ["retail", "airline"]:
        print(f"--- {domain.upper()} (n=100) ---")

        claude_results, gt_map = load_results_and_gt(
            f"claude_sonnet_{domain}_100", "claude_headless_sonnet_raw.json", domain
        )
        gpt5_results, _ = load_results_and_gt(
            f"gpt5_{domain}_100", "codex_headless_default_raw.json", domain
        )

        print(f"  Claude: {len(claude_results)} results")
        print(f"  GPT-5:  {len(gpt5_results)} results")
        print(f"  GT:     {len(gt_map)} trajectories")

        mcnemar_test(claude_results, gpt5_results, gt_map)

        c_pass = [r for r in claude_results if gt_map.get(r["trajectory_id"]) == "pass"]
        g_pass = [r for r in gpt5_results if gt_map.get(r["trajectory_id"]) == "pass"]
        c_fp = sum(1 for r in c_pass if r.get("has_failure", False))
        g_fp = sum(1 for r in g_pass if r.get("has_failure", False))
        n_pass_c = len(c_pass)
        n_pass_g = len(g_pass)

        if n_pass_c > 0 and n_pass_g > 0:
            print(f"\n  FPR comparison:")
            two_proportion_z_test(
                g_fp / n_pass_g, n_pass_g,
                c_fp / n_pass_c, n_pass_c,
                f"GPT-5 vs Claude FPR on {domain}"
            )
        print()


if __name__ == "__main__":
    main()
