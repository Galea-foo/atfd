"""Benchmark runner — loads datasets, runs judges, scores results."""
from __future__ import annotations
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from atfd.metrics import (
    BenchmarkResults, category_alignment, cost_summary,
    detection_rate, f1_score, false_positive_rate, quality_detection_rate,
)
from atfd.schema import CostReport, JudgeOutput, Outcome, Trajectory
from atfd.judges.base import Judge

console = Console()


def run_benchmark(judge: Judge, trajectories: list[Trajectory], output_dir: Path | None = None) -> BenchmarkResults:
    gt_outcomes: list[Outcome] = []
    outputs: list[JudgeOutput] = []
    gt_categories: list[list[str]] = []
    pred_categories: list[list[str]] = []

    for i, traj in enumerate(trajectories):
        status = "✗" if traj.ground_truth.outcome == Outcome.FAIL else ("◐" if traj.ground_truth.outcome == Outcome.DEGRADED else "✓")
        console.print(f"  [{i+1}/{len(trajectories)}] {traj.trajectory_id} {status}", end="")
        try:
            output = judge.evaluate(traj)
        except Exception as e:
            console.print(f" [red]ERROR: {e}[/red]")
            output = JudgeOutput(
                trajectory_id=traj.trajectory_id, has_failure=False, findings=[],
                cost=CostReport(dollar_cost=0, latency_seconds=0, total_tokens=0, api_calls=0, infrastructure="none"),
            )
        gt_outcomes.append(traj.ground_truth.outcome)
        outputs.append(output)
        gt_categories.append(traj.ground_truth.failure_categories)
        pred_categories.append([f.category for f in output.findings])
        console.print(f" → {len(output.findings)} findings (${output.cost.dollar_cost:.4f})")

    dr = detection_rate(gt_outcomes, outputs)
    qdr = quality_detection_rate(gt_outcomes, outputs)
    fpr = false_positive_rate(gt_outcomes, outputs)
    f1 = f1_score(gt_outcomes, outputs)
    alignment = category_alignment(gt_categories, pred_categories)
    cost = cost_summary(outputs)

    results = BenchmarkResults(
        system_name=judge.name, detection=dr, quality_detection=qdr,
        fpr=fpr, f1=f1, alignment=alignment, cost=cost,
    )

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_path = output_dir / f"{judge.name}_raw.json"
        raw_path.write_text(json.dumps([o.model_dump() for o in outputs], indent=2, default=str))

    return results


def print_results(results: BenchmarkResults):
    table = Table(title=f"Results: {results.system_name}")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_column("95% CI")

    def _fmt(m):
        if m.value is None: return ("N/A", "")
        val = f"{m.value:.1%}"
        ci = f"[{m.ci_low:.1%}, {m.ci_high:.1%}]" if m.ci_low is not None else ""
        return (val, ci)

    v, c = _fmt(results.detection); table.add_row("Detection Rate", v, c)
    v, c = _fmt(results.quality_detection); table.add_row("Quality Detection Rate", v, c)
    v, c = _fmt(results.fpr); table.add_row("False Positive Rate", v, c)
    table.add_row("F1 Score", f"{results.f1:.3f}", "")
    table.add_row("Category Alignment (macro-F1)", f"{results.alignment['macro_f1']:.3f}", "")
    table.add_row("", "", "")
    table.add_row("Mean $/trajectory", f"${results.cost['mean_dollar_cost']:.4f}", "")
    table.add_row("Latency p50", f"{results.cost['p50_latency_seconds']:.3f}s", "")
    table.add_row("Latency p95", f"{results.cost['p95_latency_seconds']:.3f}s", "")
    table.add_row("Mean tokens/traj", f"{results.cost['mean_total_tokens']:.0f}", "")
    console.print(table)
