"""Generate domain heatmap (DR%) and cost-performance scatter from results.

Usage:
    python scripts/generate_heatmap.py

Reads raw result files from results/raw/<dir>/<file>_raw.json,
matches ground truth from tau-bench/SWE-bench/synthetic adapters,
and generates paper/figures/domain_heatmap.pdf and paper/figures/cost_performance_manual.pdf.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from atfd.adapters.tau_bench import TauBenchAdapter
from atfd.adapters.swe_bench import SweBenchAdapter
from atfd.adapters.toolathlon import ToolathlonAdapter
from atfd.metrics import detection_rate, false_positive_rate
from atfd.schema import JudgeOutput, Outcome

REPO = Path(__file__).resolve().parents[1]
FIG_DIR = REPO / "paper" / "figures"
RAW_DIR = REPO / "results" / "raw"

# Result directories mapped to (system_display_name, domain_display_name)
RESULT_MAP = {
    # Naive Heuristic
    ("naive_synthetic", "Synthetic"): "Naive Heuristic",
    ("naive_retail", "Retail"): "Naive Heuristic",
    ("naive_airline", "Airline"): "Naive Heuristic",
    ("naive_swebench", "SWE-bench"): "Naive Heuristic",
    ("naive_atbench", "ATBench"): "Naive Heuristic",
    ("toolathlon_fixed", "Toolathlon"): "Naive Heuristic",
    # Llama 4 Scout
    ("llama4scout_retail_100", "Retail"): "Llama 4 Scout",
    ("llama4scout_airline_100", "Airline"): "Llama 4 Scout",
    ("llama4scout_swebench_100", "SWE-bench"): "Llama 4 Scout",
    ("toolathlon_fixed", "Toolathlon"): "Llama 4 Scout",
    # Claude Sonnet 4
    ("claude_sonnet_retail_100", "Retail"): "Claude Sonnet 4",
    ("claude_sonnet_airline_100", "Airline"): "Claude Sonnet 4",
    ("claude_swebench_100", "SWE-bench"): "Claude Sonnet 4",
    ("claude_atbench", "ATBench"): "Claude Sonnet 4",
    ("toolathlon_fixed", "Toolathlon"): "Claude Sonnet 4",
    # GPT-5
    ("gpt5_retail_100", "Retail"): "GPT-5",
    ("gpt5_airline_100", "Airline"): "GPT-5",
    ("gpt5_swebench_100", "SWE-bench"): "GPT-5",
}


def load_ground_truth():
    """Build trajectory_id → Outcome map for all datasets."""
    gt = {}
    for domain in ["retail", "airline"]:
        adapter = TauBenchAdapter(domain=domain)
        trajs = adapter.load_dataset(REPO / "data" / "tau_bench", limit=0)
        for t in trajs:
            gt[t.trajectory_id] = t.ground_truth.outcome
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


def compute_dr_fpr(raw_path, gt_map):
    """Compute DR and FPR from a raw JSON file + ground truth map."""
    records = json.loads(raw_path.read_text())
    outputs = [JudgeOutput.model_validate(r) for r in records]
    gt_outcomes = []
    for o in outputs:
        tid = o.trajectory_id.lower()
        if o.trajectory_id in gt_map:
            gt_outcomes.append(gt_map[o.trajectory_id])
        elif "pass" in tid:
            gt_outcomes.append(Outcome.PASS)
        elif "degraded" in tid:
            gt_outcomes.append(Outcome.DEGRADED)
        else:
            gt_outcomes.append(Outcome.FAIL)

    dr = detection_rate(gt_outcomes, outputs)
    fpr = false_positive_rate(gt_outcomes, outputs)
    return (
        dr.value * 100 if dr.value is not None else None,
        fpr.value * 100 if fpr.value is not None else None,
        len(outputs),
    )


# Systems and domains for the heatmap
SYSTEMS = ["Naive Heuristic", "LangSmith (4 rules)", "Braintrust (4 scorers)",
           "Llama 4 Scout", "GPT-5", "Claude Sonnet 4"]
DOMAINS = ["Synthetic", "Retail", "Airline", "SWE-bench", "ATBench", "Toolathlon"]

# Hardcoded values from existing paper + will be overridden by computed values
DR_DATA = {
    ("Naive Heuristic", "Synthetic"): 14.0,
    ("Naive Heuristic", "Retail"): 25.4,
    ("Naive Heuristic", "Airline"): 40.9,
    ("Naive Heuristic", "SWE-bench"): 100.0,
    ("Naive Heuristic", "ATBench"): 0.0,
    ("Naive Heuristic", "Toolathlon"): 79.2,
    ("LangSmith (4 rules)", "Synthetic"): 22.0,
    ("LangSmith (4 rules)", "Retail"): 0.0,
    ("LangSmith (4 rules)", "Airline"): 64.3,
    ("LangSmith (4 rules)", "SWE-bench"): 100.0,
    ("LangSmith (4 rules)", "ATBench"): 0.0,
    ("LangSmith (4 rules)", "Toolathlon"): None,
    ("Braintrust (4 scorers)", "Synthetic"): 22.0,
    ("Braintrust (4 scorers)", "Retail"): 91.7,
    ("Braintrust (4 scorers)", "Airline"): 64.3,
    ("Braintrust (4 scorers)", "SWE-bench"): 100.0,
    ("Braintrust (4 scorers)", "ATBench"): 0.0,
    ("Braintrust (4 scorers)", "Toolathlon"): None,
    ("Llama 4 Scout", "Synthetic"): 100.0,
    ("Llama 4 Scout", "Retail"): None,
    ("Llama 4 Scout", "Airline"): None,
    ("Llama 4 Scout", "SWE-bench"): 100.0,
    ("Llama 4 Scout", "ATBench"): 70.0,
    ("Llama 4 Scout", "Toolathlon"): 6.9,
    ("GPT-5", "Synthetic"): 98.3,
    ("GPT-5", "Retail"): None,
    ("GPT-5", "Airline"): None,
    ("GPT-5", "SWE-bench"): None,
    ("GPT-5", "ATBench"): None,
    ("GPT-5", "Toolathlon"): None,
    ("Claude Sonnet 4", "Synthetic"): 100.0,
    ("Claude Sonnet 4", "Retail"): None,
    ("Claude Sonnet 4", "Airline"): None,
    ("Claude Sonnet 4", "SWE-bench"): 100.0,
    ("Claude Sonnet 4", "ATBench"): 100.0,
    ("Claude Sonnet 4", "Toolathlon"): 95.8,
}

FPR_DATA = {
    ("Naive Heuristic", "Synthetic"): None,
    ("Naive Heuristic", "Retail"): 17.8,
    ("Naive Heuristic", "Airline"): 3.6,
    ("Naive Heuristic", "SWE-bench"): 0.0,
    ("Naive Heuristic", "ATBench"): 0.0,
    ("Naive Heuristic", "Toolathlon"): 0.0,
    ("LangSmith (4 rules)", "Synthetic"): None,
    ("LangSmith (4 rules)", "Retail"): 0.0,
    ("LangSmith (4 rules)", "Airline"): 33.3,
    ("LangSmith (4 rules)", "SWE-bench"): 100.0,
    ("LangSmith (4 rules)", "ATBench"): 0.0,
    ("LangSmith (4 rules)", "Toolathlon"): None,
    ("Braintrust (4 scorers)", "Synthetic"): None,
    ("Braintrust (4 scorers)", "Retail"): 71.1,
    ("Braintrust (4 scorers)", "Airline"): 33.3,
    ("Braintrust (4 scorers)", "SWE-bench"): 100.0,
    ("Braintrust (4 scorers)", "ATBench"): 0.0,
    ("Braintrust (4 scorers)", "Toolathlon"): None,
    ("Llama 4 Scout", "Synthetic"): None,
    ("Llama 4 Scout", "Retail"): 13.2,
    ("Llama 4 Scout", "Airline"): 66.7,
    ("Llama 4 Scout", "SWE-bench"): 100.0,
    ("Llama 4 Scout", "ATBench"): None,
    ("Llama 4 Scout", "Toolathlon"): 7.1,
    ("GPT-5", "Synthetic"): None,
    ("GPT-5", "Retail"): 29.5,
    ("GPT-5", "Airline"): 51.7,
    ("GPT-5", "SWE-bench"): 50.0,
    ("GPT-5", "ATBench"): None,
    ("GPT-5", "Toolathlon"): None,
    ("Claude Sonnet 4", "Synthetic"): None,
    ("Claude Sonnet 4", "Retail"): 9.0,
    ("Claude Sonnet 4", "Airline"): 10.3,
    ("Claude Sonnet 4", "SWE-bench"): 0.0,
    ("Claude Sonnet 4", "ATBench"): None,
    ("Claude Sonnet 4", "Toolathlon"): 46.4,
}


def update_from_results(gt_map):
    """Try to load n=100 results and update DR_DATA."""
    updates = {
        ("Llama 4 Scout", "Retail"): ("llama4scout_retail_100", "llm_judge_groq-llama4-scout_raw.json", "retail"),
        ("Llama 4 Scout", "Airline"): ("llama4scout_airline_100", "llm_judge_groq-llama4-scout_raw.json", "airline"),
        ("Claude Sonnet 4", "Retail"): ("claude_sonnet_retail_100", "claude_headless_sonnet_raw.json", "retail"),
        ("Claude Sonnet 4", "Airline"): ("claude_sonnet_airline_100", "claude_headless_sonnet_raw.json", "airline"),
        ("GPT-5", "Retail"): ("gpt5_retail_100", "codex_headless_default_raw.json", "retail"),
        ("GPT-5", "Airline"): ("gpt5_airline_100", "codex_headless_default_raw.json", "airline"),
    }

    for key, (dirn, fname, domain) in updates.items():
        raw_path = RAW_DIR / dirn / fname
        if raw_path.exists():
            dr_pct, fpr_pct, n = compute_dr_fpr(raw_path, gt_map)
            if dr_pct is not None:
                DR_DATA[key] = dr_pct
            if fpr_pct is not None:
                FPR_DATA[key] = fpr_pct
            print(f"  Updated {key}: DR={dr_pct:.1f}% FPR={fpr_pct:.1f}% (n={n})" if dr_pct is not None else f"  {key}: no data")


def plot_heatmap():
    matrix = np.full((len(SYSTEMS), len(DOMAINS)), np.nan)
    for i, sys in enumerate(SYSTEMS):
        for j, dom in enumerate(DOMAINS):
            val = DR_DATA.get((sys, dom))
            if val is not None:
                matrix[i, j] = val

    fig, ax = plt.subplots(figsize=(10, 5.5))
    mask = np.isnan(matrix)

    sns.heatmap(
        matrix, annot=False, mask=mask,
        xticklabels=DOMAINS, yticklabels=SYSTEMS,
        cmap="RdYlGn", vmin=0, vmax=100,
        linewidths=0.5, linecolor="lightgray",
        cbar_kws={"label": "Detection Rate (%)"},
        ax=ax,
    )
    for i, sys in enumerate(SYSTEMS):
        for j, dom in enumerate(DOMAINS):
            if mask[i, j]:
                ax.text(j + 0.5, i + 0.5, "—", ha="center", va="center",
                        fontsize=9, color="gray")
            else:
                dr_val = matrix[i, j]
                fpr_val = FPR_DATA.get((sys, dom))
                dr_str = f"{dr_val:.0f}"
                if fpr_val is not None:
                    label = f"{dr_str}\n({fpr_val:.0f}%)"
                    fpr_color = "#cc0000" if fpr_val >= 50 else "#666666"
                else:
                    label = dr_str
                    fpr_color = "black"
                text_color = "white" if dr_val < 30 or dr_val > 85 else "black"
                ax.text(j + 0.5, i + 0.35, dr_str, ha="center", va="center",
                        fontsize=9, fontweight="bold", color=text_color)
                if fpr_val is not None:
                    ax.text(j + 0.5, i + 0.7, f"FPR {fpr_val:.0f}%",
                            ha="center", va="center", fontsize=6.5,
                            color=fpr_color)

    ax.set_title("Detection Rate (%) by System × Domain\n"
                 "(FPR shown below DR where available)", fontsize=12)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=10)
    plt.setp(ax.get_yticklabels(), rotation=0, fontsize=10)
    fig.tight_layout()
    out = FIG_DIR / "domain_heatmap.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


def plot_cost_performance():
    cost_data = [
        ("Naive Heuristic", 0.0, None),
        ("LangSmith (4 rules)", 0.0, None),
        ("Braintrust (4 scorers)", 0.0, None),
        ("Llama 4 Scout", 0.0, None),
        ("GPT-5", 0.23, None),
        ("Claude Sonnet 4", 0.027, None),
    ]

    mean_drs = []
    for sys, cost, _ in cost_data:
        vals = [DR_DATA.get((sys, d)) for d in DOMAINS]
        valid = [v for v in vals if v is not None]
        mean_dr = np.mean(valid) / 100 if valid else 0
        mean_drs.append(mean_dr)

    fig, ax = plt.subplots(figsize=(8, 5))
    palette = sns.color_palette("colorblind", len(cost_data))

    for i, ((name, cost, _), dr) in enumerate(zip(cost_data, mean_drs)):
        ax.scatter(dr, cost, s=150, color=palette[i], zorder=3)
        offset = (8, 5) if name != "Claude Sonnet 4" else (8, -12)
        ax.annotate(name, (dr, cost), textcoords="offset points",
                    xytext=offset, fontsize=9, color=palette[i])

    ax.set_xlabel("Mean Detection Rate across domains", fontsize=11)
    ax.set_ylabel("Cost per trajectory (USD)", fontsize=11)
    ax.set_title("Cost–Performance Frontier", fontsize=13)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlim(-0.05, 1.05)

    fig.tight_layout()
    out = FIG_DIR / "cost_performance_manual.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")


def main():
    print("Loading ground truth...")
    gt_map = load_ground_truth()
    print(f"  {len(gt_map)} trajectories loaded")

    print("Checking for n=100 results...")
    update_from_results(gt_map)

    print("Generating heatmap...")
    plot_heatmap()

    print("Generating cost-performance scatter...")
    plot_cost_performance()


if __name__ == "__main__":
    main()
