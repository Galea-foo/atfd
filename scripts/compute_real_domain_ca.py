"""Compute real-domain Category Alignment on τ-bench retail+airline.

Uses Claude Sonnet 4's predictions vs. τ-bench programmatic ground truth
to provide independent validation of CA (breaking synthetic circularity).

Usage:
    python scripts/compute_real_domain_ca.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from atfd.adapters.tau_bench import TauBenchAdapter
from atfd.metrics import category_alignment
from atfd.schema import JudgeOutput, Outcome

REPO = Path(__file__).resolve().parents[1]
RAW_DIR = REPO / "results" / "raw"

TAU_EXPRESSIBLE_TOP = {"state", "action", "communication", "infrastructure"}


def main():
    gt_by_id = {}
    for domain in ["retail", "airline"]:
        adapter = TauBenchAdapter(domain=domain)
        trajs = adapter.load_dataset(REPO / "data" / "tau_bench", limit=0)
        for t in trajs:
            gt_by_id[t.trajectory_id] = {
                "outcome": t.ground_truth.outcome,
                "categories": t.ground_truth.failure_categories,
            }

    print(f"Ground truth: {len(gt_by_id)} trajectories, "
          f"{sum(1 for v in gt_by_id.values() if v['categories'])} with categories\n")

    all_gt_cats = []
    all_pred_cats = []

    for label, dirn in [("retail", "claude_sonnet_retail_100"),
                        ("airline", "claude_sonnet_airline_100")]:
        result_file = RAW_DIR / dirn / "claude_headless_sonnet_raw.json"
        if not result_file.exists():
            print(f"MISSING: {result_file}")
            continue

        records = json.loads(result_file.read_text())
        outputs = [JudgeOutput.model_validate(r) for r in records]

        domain_gt = []
        domain_pred = []
        for out in outputs:
            gt_info = gt_by_id.get(out.trajectory_id)
            if not gt_info or gt_info["outcome"] != Outcome.FAIL or not gt_info["categories"]:
                continue
            gt_cats = gt_info["categories"]
            pred_cats = [f.category for f in out.findings
                         if f.severity.value in ("error", "warning")]
            domain_gt.append(gt_cats)
            domain_pred.append(pred_cats)

        if domain_gt:
            gt_top = [list(set(c.split(".")[0] for c in cats)) for cats in domain_gt]
            pred_top = [list(set(c.split(".")[0] for c in cats)) for cats in domain_pred]
            ca = category_alignment(gt_top, pred_top)
            print(f"{label}: n={len(domain_gt)} fail trajectories, "
                  f"top-level CA = {ca['macro_f1']:.3f}")

        all_gt_cats.extend(domain_gt)
        all_pred_cats.extend(domain_pred)

    if not all_gt_cats:
        print("No matching trajectories found.")
        return

    n = len(all_gt_cats)

    # Unconstrained top-level
    gt_top = [list(set(c.split(".")[0] for c in cats)) for cats in all_gt_cats]
    pred_top = [list(set(c.split(".")[0] for c in cats)) for cats in all_pred_cats]
    ca_top = category_alignment(gt_top, pred_top)

    # Constrained top-level (only τ-bench-expressible)
    gt_constrained = [list(set(c.split(".")[0] for c in cats
                               if c.split(".")[0] in TAU_EXPRESSIBLE_TOP))
                      for cats in all_gt_cats]
    pred_constrained = [list(set(c.split(".")[0] for c in cats
                                 if c.split(".")[0] in TAU_EXPRESSIBLE_TOP))
                        for cats in all_pred_cats]
    pairs = [(g, p) for g, p in zip(gt_constrained, pred_constrained) if g]
    if pairs:
        gc, pc = zip(*pairs)
        ca_constrained = category_alignment(list(gc), list(pc))
    else:
        ca_constrained = {"macro_f1": 0.0, "per_category": {}}

    # Subcategory-level
    ca_sub = category_alignment(all_gt_cats, all_pred_cats)

    print(f"\n=== Combined retail+airline (n={n}) ===")
    print(f"  Subcategory CA (macro F1): {ca_sub['macro_f1']:.3f}")
    print(f"  Top-level CA (macro F1):   {ca_top['macro_f1']:.3f}")
    print(f"  Constrained CA (macro F1): {ca_constrained['macro_f1']:.3f}")

    print(f"\n  Per top-level category:")
    for cat, vals in sorted(ca_top["per_category"].items()):
        print(f"    {cat}: P={vals['precision']:.3f} R={vals['recall']:.3f} F1={vals['f1']:.3f}")

    # Category distribution comparison
    gt_counter = Counter(c for cats in all_gt_cats for c in cats)
    pred_counter = Counter(c for cats in all_pred_cats for c in cats)
    print(f"\n  GT category distribution:   {dict(gt_counter.most_common())}")
    print(f"  Pred category distribution: {dict(pred_counter.most_common(10))}")


if __name__ == "__main__":
    main()
