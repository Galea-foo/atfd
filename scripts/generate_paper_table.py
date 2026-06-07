"""Generate LaTeX table entries for the main results matrix.

Reads raw result files and tau-bench ground truth, computes DR/FPR with
Wilson CIs, and prints LaTeX-ready rows.

Usage:
    python scripts/generate_paper_table.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from atfd.adapters.tau_bench import TauBenchAdapter
from atfd.metrics import detection_rate, false_positive_rate, wilson_ci
from atfd.schema import JudgeOutput, Outcome, Severity

REPO = Path(__file__).resolve().parents[1]
RAW_DIR = REPO / "results" / "raw"


def load_tau_gt():
    gt = {}
    for domain in ["retail", "airline", "telecom"]:
        adapter = TauBenchAdapter(domain=domain)
        try:
            trajs = adapter.load_dataset(REPO / "data" / "tau_bench", limit=0)
            for t in trajs:
                gt[t.trajectory_id] = t.ground_truth.outcome
        except Exception:
            pass
    return gt


def infer_outcome(tid, tau_gt):
    if tid in tau_gt:
        return tau_gt[tid]
    tl = tid.lower()
    if "pass" in tl:
        return Outcome.PASS
    if "degraded" in tl:
        return Outcome.DEGRADED
    return Outcome.FAIL


def compute_metrics(raw_path, tau_gt):
    records = json.loads(raw_path.read_text())
    outputs = [JudgeOutput.model_validate(r) for r in records]
    gt_outcomes = [infer_outcome(o.trajectory_id, tau_gt) for o in outputs]
    dr = detection_rate(gt_outcomes, outputs)
    fpr = false_positive_rate(gt_outcomes, outputs)
    return dr, fpr, len(outputs)


def fmt_ci(metric_result, na_str="---"):
    if metric_result.value is None:
        return na_str
    val = metric_result.value * 100
    lo = metric_result.ci_low * 100
    hi = metric_result.ci_high * 100
    return f"{val:.1f} {{\\scriptsize [{lo:.1f}, {hi:.1f}]}}"


CELLS = [
    # (system, domain_display, raw_dir, raw_file, domain_for_gt)
    # Llama 4 Scout
    ("Llama 4 Scout", "Retail (\\taubench)", "llama4scout_retail_100", "llm_judge_groq-llama4-scout_raw.json", "retail"),
    ("Llama 4 Scout", "Retail (\\taubench) [old n=50]", "groq_llama4scout_retail", "llm_judge_groq-llama4-scout_raw.json", "retail"),
    ("Llama 4 Scout", "Airline (\\taubench)", "llama4scout_airline_100", "llm_judge_groq-llama4-scout_raw.json", "airline"),
    ("Llama 4 Scout", "Airline (\\taubench) [old n=20]", "llama4scout_airline", "llm_judge_groq-llama4-scout_raw.json", "airline"),
    # Claude Sonnet 4
    ("Claude Sonnet 4", "Retail (\\taubench)", "claude_sonnet_retail_100", "claude_headless_sonnet_raw.json", "retail"),
    ("Claude Sonnet 4", "Retail (\\taubench) [old n=20]", "claude_sonnet_retail", "claude_headless_sonnet_raw.json", "retail"),
    ("Claude Sonnet 4", "Airline (\\taubench)", "claude_sonnet_airline_100", "claude_headless_sonnet_raw.json", "airline"),
    ("Claude Sonnet 4", "Airline (\\taubench) [old n=20]", "claude_sonnet_airline", "claude_headless_sonnet_raw.json", "airline"),
    # GPT-5
    ("GPT-5", "Retail (\\taubench)", "gpt5_retail_100", "codex_headless_default_raw.json", "retail"),
    ("GPT-5", "Airline (\\taubench)", "gpt5_airline_100", "codex_headless_default_raw.json", "airline"),
]


def main():
    tau_gt = load_tau_gt()
    print(f"Ground truth: {len(tau_gt)} tau-bench trajectories\n")

    print(f"{'System':<20} {'Domain':<35} {'N':>4} {'DR':>30} {'FPR':>30}")
    print("=" * 125)

    for system, domain_disp, dirn, fname, gt_domain in CELLS:
        raw_path = RAW_DIR / dirn / fname
        if not raw_path.exists():
            print(f"{system:<20} {domain_disp:<35} {'—':>4} {'[not found]':>30} {'':>30}")
            continue
        dr, fpr, n = compute_metrics(raw_path, tau_gt)
        dr_str = fmt_ci(dr)
        fpr_str = fmt_ci(fpr, "N/A")
        print(f"{system:<20} {domain_disp:<35} {n:>4} {dr_str:>30} {fpr_str:>30}")

    print("\n\n=== LaTeX rows (copy-paste into table) ===\n")
    for system, domain_disp, dirn, fname, gt_domain in CELLS:
        if "[old" in domain_disp:
            continue
        raw_path = RAW_DIR / dirn / fname
        if not raw_path.exists():
            continue
        dr, fpr, n = compute_metrics(raw_path, tau_gt)
        dr_tex = fmt_ci(dr)
        fpr_tex = fmt_ci(fpr)
        print(f"  & {domain_disp:<25} & {n:<5} & {dr_tex} & {fpr_tex} \\\\")


if __name__ == "__main__":
    main()
