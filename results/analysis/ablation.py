"""Run ablation studies for Galea heuristic and LLM judges."""
from __future__ import annotations
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()


def run_galea_ablation(trajectories, api_url, output_dir):
    """Disable each Galea heuristic mechanism one at a time."""
    from atfd.judges.galea import GaleaJudge
    from atfd.harness import run_benchmark

    variants = {
        "full": {},
        "no_pattern": {"disable": "pattern_matching"},
        "no_counting": {"disable": "counting"},
        "no_statistical": {"disable": "statistical"},
        "no_crossref": {"disable": "cross_referencing"},
        "no_risk": {"disable": "risk_scoring"},
        "pattern_only": {"only": "pattern_matching"},
    }

    results = {}
    for name, config in variants.items():
        console.print(f"\n[bold]Ablation: {name}[/bold]")
        judge = GaleaJudge(api_url=api_url, mode="heuristic")
        result = run_benchmark(judge, trajectories, output_dir / "ablation")
        results[name] = {
            "detection_rate": result.detection.value,
            "fpr": result.fpr.value,
            "f1": result.f1,
        }

    table = Table(title="Galea Heuristic Ablation")
    table.add_column("Variant")
    table.add_column("Detection Rate", justify="right")
    table.add_column("FPR", justify="right")
    table.add_column("F1", justify="right")
    for name, r in results.items():
        dr = f"{r['detection_rate']:.1%}" if r["detection_rate"] is not None else "N/A"
        fpr = f"{r['fpr']:.1%}" if r["fpr"] is not None else "N/A"
        table.add_row(name, dr, fpr, f"{r['f1']:.3f}")
    console.print(table)

    out = output_dir / "ablation_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    return results


def run_llm_judge_ablation(trajectories, output_dir):
    """Test LLM judge with/without taxonomy, few-shot, CoT."""
    console.print("[yellow]LLM judge ablation requires API calls — run separately[/yellow]")
