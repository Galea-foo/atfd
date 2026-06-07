"""Compute DR/FPR/F1 for tau-bench judge results using ground truth from dataset.

Usage:
    python scripts/compute_tau_metrics.py results/raw/claude_sonnet_retail/claude_headless_sonnet_raw.json retail
    python scripts/compute_tau_metrics.py results/raw/llama4scout_airline_100/llm_judge_groq-llama4-scout_raw.json airline
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from atfd.adapters.tau_bench import TauBenchAdapter
from atfd.metrics import detection_rate, false_positive_rate, f1_score, quality_detection_rate
from atfd.schema import JudgeOutput, Outcome


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <raw_json> <domain>")
        sys.exit(1)

    raw_path = Path(sys.argv[1])
    domain = sys.argv[2]

    adapter = TauBenchAdapter(domain=domain)
    trajs = adapter.load_dataset(Path("data/tau_bench"), limit=0)
    gt_map = {t.trajectory_id: t.ground_truth.outcome for t in trajs}

    records = json.loads(raw_path.read_text())
    outputs = [JudgeOutput.model_validate(r) for r in records]
    gt_outcomes = [gt_map.get(o.trajectory_id, Outcome.PASS) for o in outputs]

    n = len(outputs)
    n_fail = sum(1 for g in gt_outcomes if g == Outcome.FAIL)
    n_pass = sum(1 for g in gt_outcomes if g == Outcome.PASS)
    n_detected = sum(1 for g, o in zip(gt_outcomes, outputs) if g == Outcome.FAIL and o.has_failure)
    n_fp = sum(1 for g, o in zip(gt_outcomes, outputs) if g == Outcome.PASS and o.has_failure)

    dr = detection_rate(gt_outcomes, outputs)
    fpr = false_positive_rate(gt_outcomes, outputs)
    f1 = f1_score(gt_outcomes, outputs)
    qdr = quality_detection_rate(gt_outcomes, outputs)

    print(f"Domain: {domain}")
    print(f"N: {n} ({n_fail} fail, {n_pass} pass)")
    print(f"Detected: {n_detected}/{n_fail} failures, {n_fp}/{n_pass} false positives")
    print(f"DR: {dr.value*100:.1f}% [{dr.ci_low*100:.1f}, {dr.ci_high*100:.1f}]" if dr.value is not None else "DR: N/A")
    print(f"FPR: {fpr.value*100:.1f}% [{fpr.ci_low*100:.1f}, {fpr.ci_high*100:.1f}]" if fpr.value is not None else "FPR: N/A")
    print(f"F1: {f1:.3f}")
    print(f"QDR: {qdr.value*100:.1f}%" if qdr.value is not None else "QDR: N/A")


if __name__ == "__main__":
    main()
