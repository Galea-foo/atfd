"""main_results.py — Load raw results, compute metrics, emit a LaTeX table.

Usage:
    python results/analysis/main_results.py

Reads every *_raw.json file in results/raw/, computes detection rate, FPR,
F1, quality detection rate, and cost per trajectory, then writes a LaTeX
longtable to paper/tables/main_results.tex and prints a plain-text summary.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve package root so this script works when run from any cwd
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from atfd.metrics import (
    BenchmarkResults,
    MetricResult,
    detection_rate,
    false_positive_rate,
    f1_score,
    quality_detection_rate,
    cost_summary,
)
from atfd.schema import JudgeOutput, Outcome

RAW_DIR = REPO_ROOT / "results" / "raw"
TABLE_DIR = REPO_ROOT / "paper" / "tables"
TABLE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_metric(m: MetricResult) -> str:
    """Format a MetricResult as 'value [lo, hi]' or 'N/A'."""
    if m.value is None:
        return "N/A"
    pct = f"{m.value:.1%}"
    if m.ci_low is not None and m.ci_high is not None:
        return f"{pct} [{m.ci_low:.1%}, {m.ci_high:.1%}]"
    return pct


def _fmt_pct(v: float) -> str:
    return f"{v:.1%}"


def _infer_outcome(traj_id: str) -> Outcome:
    """Infer ground-truth outcome from trajectory_id naming convention.

    Synthetic trajectories are named:
        synth_<failure_type>_NNN  → FAIL
        synth_pass_NNN            → PASS
        synth_degraded_NNN        → DEGRADED

    tau-bench / SWE-bench trajectories embedded in raw files carry
    ground-truth via 'gt_outcome' if present; otherwise fall back to PASS
    so callers can iterate and the caller provides the override.

    This function is used only when the raw file does not carry gt_outcome.
    """
    tid = traj_id.lower()
    if "pass" in tid:
        return Outcome.PASS
    if "degraded" in tid:
        return Outcome.DEGRADED
    # Any other synth_* trajectory is treated as FAIL
    return Outcome.FAIL


def load_raw_file(path: Path) -> tuple[list[Outcome], list[JudgeOutput]]:
    """Load a *_raw.json file.

    Each record may optionally include a ``gt_outcome`` field that was
    written by a harness run.  If absent, outcome is inferred from the
    trajectory_id (see _infer_outcome).
    """
    records: list[dict] = json.loads(path.read_text())
    gt_outcomes: list[Outcome] = []
    outputs: list[JudgeOutput] = []
    for rec in records:
        gt_raw = rec.pop("gt_outcome", None)
        output = JudgeOutput.model_validate(rec)
        if gt_raw is not None:
            gt = Outcome(gt_raw)
        else:
            gt = _infer_outcome(output.trajectory_id)
        gt_outcomes.append(gt)
        outputs.append(output)
    return gt_outcomes, outputs


def compute_results(system_name: str, gt_outcomes: list[Outcome], outputs: list[JudgeOutput]) -> BenchmarkResults:
    dr = detection_rate(gt_outcomes, outputs)
    qdr = quality_detection_rate(gt_outcomes, outputs)
    fpr = false_positive_rate(gt_outcomes, outputs)
    f1 = f1_score(gt_outcomes, outputs)
    cost = cost_summary(outputs)
    return BenchmarkResults(
        system_name=system_name,
        detection=dr,
        quality_detection=qdr,
        fpr=fpr,
        f1=f1,
        alignment={},
        cost=cost,
    )


# ---------------------------------------------------------------------------
# LaTeX table generation
# ---------------------------------------------------------------------------

LATEX_HEADER = r"""\begin{table}[t]
\centering
\caption{Main benchmark results across all evaluated systems (95\% Wilson confidence intervals).
DR = Detection Rate on FAIL trajectories; QDR = Quality Detection Rate on DEGRADED trajectories;
FPR = False Positive Rate on PASS trajectories; F1 computed over binary FAIL/non-FAIL labelling;
\$/traj = mean dollar cost per trajectory.}
\label{tab:main_results}
\small
\begin{tabular}{lrrrrr}
\toprule
\textbf{System} & \textbf{DR (\%)} & \textbf{QDR (\%)} & \textbf{FPR (\%)} & \textbf{F1} & \textbf{\$/traj} \\
\midrule
"""

LATEX_FOOTER = r"""\bottomrule
\end{tabular}
\end{table}
"""


def _latex_escape(s: str) -> str:
    return s.replace("_", r"\_")


def _pct_cell(m: MetricResult) -> str:
    """Format MetricResult as 'XX.X \\small{[lo, hi]}' for LaTeX."""
    if m.value is None:
        return "---"
    val = f"{m.value * 100:.1f}"
    if m.ci_low is not None and m.ci_high is not None:
        lo = f"{m.ci_low * 100:.1f}"
        hi = f"{m.ci_high * 100:.1f}"
        return rf"{val} {{\small [{lo}, {hi}]}}"
    return val


def generate_latex_table(all_results: list[BenchmarkResults]) -> str:
    lines = [LATEX_HEADER]
    for r in all_results:
        name = _latex_escape(r.system_name)
        dr = _pct_cell(r.detection)
        qdr = _pct_cell(r.quality_detection)
        fpr = _pct_cell(r.fpr)
        f1 = f"{r.f1:.3f}"
        cost = f"\\${r.cost['mean_dollar_cost']:.4f}"
        lines.append(f"{name} & {dr} & {qdr} & {fpr} & {f1} & {cost} \\\\\n")
    lines.append(LATEX_FOOTER)
    return "".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    raw_files = sorted(RAW_DIR.glob("*_raw.json"))
    if not raw_files:
        print(f"[main_results] No raw files found in {RAW_DIR}")
        sys.exit(0)

    all_results: list[BenchmarkResults] = []

    print(f"{'System':<30} {'DR':>8} {'QDR':>8} {'FPR':>8} {'F1':>6} {'$/traj':>10}  n")
    print("-" * 80)

    for path in raw_files:
        system_name = path.stem.replace("_raw", "")
        try:
            gt_outcomes, outputs = load_raw_file(path)
        except Exception as exc:
            print(f"  [SKIP] {path.name}: {exc}")
            continue

        results = compute_results(system_name, gt_outcomes, outputs)
        all_results.append(results)

        dr_str = _fmt_metric(results.detection)
        qdr_str = _fmt_metric(results.quality_detection)
        fpr_str = _fmt_metric(results.fpr)
        cost_str = f"${results.cost['mean_dollar_cost']:.4f}"
        n = len(outputs)
        print(f"{system_name:<30} {dr_str:>8} {qdr_str:>8} {fpr_str:>8} {results.f1:>6.3f} {cost_str:>10}  n={n}")

    # Write LaTeX table
    latex = generate_latex_table(all_results)
    out_path = TABLE_DIR / "main_results.tex"
    out_path.write_text(latex)
    print(f"\n[main_results] LaTeX table written to {out_path}")


if __name__ == "__main__":
    main()
