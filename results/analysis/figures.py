"""figures.py — Generate paper figures from raw benchmark results.

Produces three PDFs in paper/figures/:
  cost_performance.pdf     — scatter: detection rate vs $/trajectory, Pareto frontier
  category_confusion.pdf   — confusion matrix heatmap (predicted category vs GT category)
  failure_distribution.pdf — bar chart of failure type counts across datasets

Usage:
    python results/analysis/figures.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend, safe in CI and headless envs
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import seaborn as sns

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

RAW_DIR = REPO_ROOT / "results" / "raw"
FIG_DIR = REPO_ROOT / "paper" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

from atfd.metrics import detection_rate, cost_summary
from atfd.schema import JudgeOutput, Outcome
from atfd.taxonomy import all_categories

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _infer_outcome(traj_id: str) -> Outcome:
    tid = traj_id.lower()
    if "pass" in tid:
        return Outcome.PASS
    if "degraded" in tid:
        return Outcome.DEGRADED
    return Outcome.FAIL


def load_raw_file(path: Path) -> tuple[list[Outcome], list[JudgeOutput]]:
    records: list[dict] = json.loads(path.read_text())
    gt_outcomes: list[Outcome] = []
    outputs: list[JudgeOutput] = []
    for rec in records:
        gt_raw = rec.pop("gt_outcome", None)
        output = JudgeOutput.model_validate(rec)
        gt = Outcome(gt_raw) if gt_raw else _infer_outcome(output.trajectory_id)
        gt_outcomes.append(gt)
        outputs.append(output)
    return gt_outcomes, outputs


def load_all() -> dict[str, tuple[list[Outcome], list[JudgeOutput]]]:
    data: dict[str, tuple[list[Outcome], list[JudgeOutput]]] = {}
    for path in sorted(RAW_DIR.glob("*_raw.json")):
        system_name = path.stem.replace("_raw", "")
        try:
            gt, outputs = load_raw_file(path)
            data[system_name] = (gt, outputs)
        except Exception as exc:
            print(f"  [SKIP] {path.name}: {exc}")
    return data


# ---------------------------------------------------------------------------
# Seaborn theme
# ---------------------------------------------------------------------------

sns.set_theme(style="whitegrid", palette="colorblind", font_scale=1.1)
PALETTE = sns.color_palette("colorblind")

# ---------------------------------------------------------------------------
# Figure 1: cost_performance.pdf
# ---------------------------------------------------------------------------

def _pareto_frontier(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Return the Pareto-optimal subset (maximise x=detection, minimise y=cost).

    A point is dominated if there exists another point with both higher
    detection rate and lower cost.
    """
    pareto = []
    for px, py in points:
        dominated = False
        for qx, qy in points:
            if qx >= px and qy <= py and (qx > px or qy < py):
                dominated = True
                break
        if not dominated:
            pareto.append((px, py))
    return sorted(pareto, key=lambda p: p[0])


def plot_cost_performance(data: dict[str, tuple[list[Outcome], list[JudgeOutput]]]) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))

    names, xs, ys = [], [], []
    for system_name, (gt_outcomes, outputs) in data.items():
        dr = detection_rate(gt_outcomes, outputs)
        cost = cost_summary(outputs)
        dr_val = dr.value if dr.value is not None else 0.0
        cost_val = cost["mean_dollar_cost"]
        names.append(system_name)
        xs.append(dr_val)
        ys.append(cost_val)

    xs_arr = np.array(xs)
    ys_arr = np.array(ys)

    # Scatter all systems
    for i, (name, x, y) in enumerate(zip(names, xs_arr, ys_arr)):
        color = PALETTE[i % len(PALETTE)]
        ax.scatter(x, y, color=color, s=120, zorder=3, label=name.replace("_", " "))
        # Offset label slightly to avoid overlap
        ax.annotate(
            name.replace("_", " "),
            (x, y),
            textcoords="offset points",
            xytext=(6, 4),
            fontsize=8,
            color=color,
        )

    # Pareto frontier (high DR, low cost)
    points = list(zip(xs_arr.tolist(), ys_arr.tolist()))
    if len(points) > 1:
        pareto = _pareto_frontier(points)
        if len(pareto) >= 2:
            px, py = zip(*pareto)
            ax.step(px, py, where="post", color="crimson", linewidth=1.5,
                    linestyle="--", alpha=0.7, label="Pareto frontier")

    ax.set_xlabel("Detection Rate (FAIL trajectories)")
    ax.set_ylabel("Mean cost per trajectory (USD)")
    ax.set_title("Cost–Performance Trade-off")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))

    # Only show legend if more than one system
    if len(names) > 1:
        ax.legend(fontsize=8, loc="upper right")

    ax.set_xlim(-0.05, 1.05)
    ymax = max(ys_arr) if len(ys_arr) > 0 else 1.0
    ax.set_ylim(-0.02 * ymax - 0.001, ymax * 1.15 + 0.001)

    fig.tight_layout()
    out = FIG_DIR / "cost_performance.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"[figures] Saved {out}")


# ---------------------------------------------------------------------------
# Figure 2: category_confusion.pdf
# ---------------------------------------------------------------------------

# Top-level taxonomy categories
TOP_CATS = [c.name for c in all_categories()]


def _top_category(dotted: str) -> str:
    """Map 'action.wrong_tool' → 'action', unknown → 'other'."""
    top = dotted.split(".")[0] if dotted else "other"
    return top if top in TOP_CATS else "other"


def plot_category_confusion(data: dict[str, tuple[list[Outcome], list[JudgeOutput]]]) -> None:
    """Confusion matrix: rows = GT top-level category, cols = predicted top-level category.

    We aggregate across all systems and all FAIL/DEGRADED trajectories where
    the trajectory_id encodes a category (synth_<category>_* naming).
    """
    labels = TOP_CATS + ["other"]
    n = len(labels)
    label_idx = {c: i for i, c in enumerate(labels)}
    matrix = np.zeros((n, n), dtype=int)

    for system_name, (gt_outcomes, outputs) in data.items():
        for gt_outcome, output in zip(gt_outcomes, outputs):
            if gt_outcome == Outcome.PASS:
                continue  # skip PASS — no GT category to compare

            # Infer GT category from trajectory_id (synth_<cat>_<sub>_NNN)
            parts = output.trajectory_id.split("_")
            # e.g. "synth_hallucination_001" → parts[1] = "hallucination" (comm)
            # We'll map common keywords → top-level cats
            gt_cat_key = "_".join(parts[1:-1]) if len(parts) >= 3 else parts[-1]
            gt_cat = _keyword_to_top(gt_cat_key)

            # Predicted categories from findings
            pred_cats_top = {_top_category(f.category) for f in output.findings}
            if not pred_cats_top:
                pred_cats_top = {"other"}

            gt_idx = label_idx.get(gt_cat, label_idx["other"])
            for pc in pred_cats_top:
                pred_idx = label_idx.get(pc, label_idx["other"])
                matrix[gt_idx, pred_idx] += 1

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        matrix,
        annot=True,
        fmt="d",
        xticklabels=labels,
        yticklabels=labels,
        cmap="Blues",
        linewidths=0.5,
        linecolor="lightgray",
        ax=ax,
    )
    ax.set_xlabel("Predicted category")
    ax.set_ylabel("Ground-truth category")
    ax.set_title("Category Confusion Matrix (aggregated across all systems)")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9)
    plt.setp(ax.get_yticklabels(), rotation=0, fontsize=9)

    fig.tight_layout()
    out = FIG_DIR / "category_confusion.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"[figures] Saved {out}")


_KEYWORD_MAP: dict[str, str] = {
    "hallucination": "communication",
    "wrong_response": "communication",
    "missing_info": "communication",
    "tool_loop": "process",
    "planning": "process",
    "context_overflow": "process",
    "infinite_delegation": "process",
    "wrong_tool": "action",
    "wrong_args": "action",
    "missing_action": "action",
    "wrong_state": "state",
    "partial_state": "state",
    "shallow_output": "quality",
    "suboptimal": "quality",
    "poor_tone": "quality",
    "incomplete_analysis": "quality",
    "permission": "safety",
    "data_leakage": "safety",
    "policy": "safety",
    "timeout": "infrastructure",
    "error": "infrastructure",
    "max_steps": "infrastructure",
}


def _keyword_to_top(key: str) -> str:
    key_lower = key.lower()
    # exact match first
    if key_lower in _KEYWORD_MAP:
        return _KEYWORD_MAP[key_lower]
    # partial match
    for kw, cat in _KEYWORD_MAP.items():
        if kw in key_lower:
            return cat
    # if key is itself a top-level category
    if key_lower in TOP_CATS:
        return key_lower
    return "other"


# ---------------------------------------------------------------------------
# Figure 3: failure_distribution.pdf
# ---------------------------------------------------------------------------

def plot_failure_distribution(data: dict[str, tuple[list[Outcome], list[JudgeOutput]]]) -> None:
    """Bar chart of failure type distribution (by GT top-level category) across datasets.

    Dataset is inferred from trajectory_id prefix:
      synth_*   → synthetic
      tau_*     → tau-bench
      swe_*     → swe-bench
      (other)   → unknown
    """
    # Aggregate counts per (dataset, top_category)
    dataset_cat_counts: dict[str, Counter] = defaultdict(Counter)

    # Use a single representative system (or union across all) for GT distribution
    # We take the union across all loaded systems for coverage
    seen_traj_ids: set[str] = set()

    for system_name, (gt_outcomes, outputs) in data.items():
        for gt_outcome, output in zip(gt_outcomes, outputs):
            tid = output.trajectory_id
            if tid in seen_traj_ids:
                continue
            seen_traj_ids.add(tid)

            if gt_outcome == Outcome.PASS:
                continue

            # Infer dataset
            tid_lower = tid.lower()
            if tid_lower.startswith("synth"):
                dataset = "synthetic"
            elif tid_lower.startswith("tau"):
                dataset = "tau-bench"
            elif tid_lower.startswith("swe"):
                dataset = "swe-bench"
            else:
                dataset = "other"

            # Infer GT category
            parts = tid.split("_")
            gt_cat_key = "_".join(parts[1:-1]) if len(parts) >= 3 else parts[-1]
            gt_cat = _keyword_to_top(gt_cat_key)
            dataset_cat_counts[dataset][gt_cat] += 1

    if not dataset_cat_counts:
        print("[figures] No FAIL/DEGRADED trajectories found; skipping failure_distribution.pdf")
        # Still write an empty figure so the paper/ directory has all files
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No failure data available", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.set_title("Failure Type Distribution (no data)")
        fig.tight_layout()
        out = FIG_DIR / "failure_distribution.pdf"
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)
        print(f"[figures] Saved {out}")
        return

    datasets = sorted(dataset_cat_counts.keys())
    all_cats = sorted({cat for counts in dataset_cat_counts.values() for cat in counts})

    x = np.arange(len(all_cats))
    width = 0.8 / max(len(datasets), 1)

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, dataset in enumerate(datasets):
        counts = [dataset_cat_counts[dataset].get(cat, 0) for cat in all_cats]
        offset = (i - len(datasets) / 2 + 0.5) * width
        bars = ax.bar(x + offset, counts, width, label=dataset,
                      color=PALETTE[i % len(PALETTE)], alpha=0.85)
        # Label bars with non-zero counts
        for bar, count in zip(bars, counts):
            if count > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.05,
                    str(count),
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

    ax.set_xticks(x)
    ax.set_xticklabels(all_cats, rotation=30, ha="right", fontsize=10)
    ax.set_ylabel("Number of trajectories")
    ax.set_title("Failure Type Distribution across Datasets")
    ax.legend(title="Dataset", fontsize=9)
    ax.yaxis.get_major_locator().set_params(integer=True)

    fig.tight_layout()
    out = FIG_DIR / "failure_distribution.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"[figures] Saved {out}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    data = load_all()
    if not data:
        print(f"[figures] No raw files found in {RAW_DIR}")
        sys.exit(0)

    plot_cost_performance(data)
    plot_category_confusion(data)
    plot_failure_distribution(data)
    print("[figures] Done.")


if __name__ == "__main__":
    main()
