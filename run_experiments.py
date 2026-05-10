#!/usr/bin/env python3
"""Run all ATFD benchmark experiments and collect results."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

os.environ["GROQ_API_KEY"] = "REDACTED_GROQ_KEY"
os.environ["OPENROUTER_API_KEY"] = "REDACTED_OPENROUTER_KEY"

from rich.console import Console
from rich.table import Table

from atfd.adapters.synthetic import SyntheticAdapter
from atfd.adapters.tau_bench import TauBenchAdapter
from atfd.harness import print_results, run_benchmark
from atfd.judges.naive import NaiveHeuristicJudge
from atfd.judges.llm_judge import LLMJudge

console = Console()
ROOT = Path(__file__).parent
RESULTS_DIR = ROOT / "results" / "raw"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_synthetic():
    adapter = SyntheticAdapter()
    return adapter.load_dataset(ROOT / "datasets" / "synthetic")


def load_tau_bench(domain, limit=0):
    adapter = TauBenchAdapter(domain=domain)
    return adapter.load_dataset(ROOT / "data" / "tau_bench", limit=limit)


def run_and_save(judge, trajectories, label):
    console.print(f"\n[bold cyan]═══ {label} ═══[/bold cyan]")
    console.print(f"Judge: {judge.name} | Trajectories: {len(trajectories)}")
    out_dir = RESULTS_DIR / label.replace(" ", "_").lower()
    results = run_benchmark(judge, trajectories, out_dir)
    print_results(results)
    summary = {
        "label": label,
        "system": judge.name,
        "n": len(trajectories),
        "detection_rate": results.detection.value,
        "detection_ci": [results.detection.ci_low, results.detection.ci_high] if results.detection.ci_low else None,
        "quality_detection_rate": results.quality_detection.value,
        "fpr": results.fpr.value,
        "fpr_ci": [results.fpr.ci_low, results.fpr.ci_high] if results.fpr.ci_low else None,
        "f1": results.f1,
        "category_alignment": results.alignment["macro_f1"],
        "cost": results.cost,
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    return summary


def main():
    all_results = []

    # -- Load datasets --
    synthetic = load_synthetic()
    console.print(f"[green]Loaded {len(synthetic)} synthetic trajectories[/green]")

    tau_retail = load_tau_bench("retail", limit=100)
    console.print(f"[green]Loaded {len(tau_retail)} retail trajectories[/green]")

    tau_airline = load_tau_bench("airline", limit=50)
    console.print(f"[green]Loaded {len(tau_airline)} airline trajectories[/green]")

    # -- Naive heuristic baseline (all datasets) --
    naive = NaiveHeuristicJudge()
    all_results.append(run_and_save(naive, synthetic, "naive synthetic"))
    all_results.append(run_and_save(naive, tau_retail, "naive retail"))
    all_results.append(run_and_save(naive, tau_airline, "naive airline"))

    # -- LLM judges on synthetic (fits in free tier) --
    for model_key in ["groq-llama-70b", "groq-llama4-scout"]:
        judge = LLMJudge(model_key=model_key)
        all_results.append(run_and_save(judge, synthetic, f"{model_key} synthetic"))

    # -- LLM judge on tau-bench sample (with rate limit retry) --
    tau_sample = tau_retail[:20]
    for model_key in ["groq-llama4-scout"]:
        judge = LLMJudge(model_key=model_key)
        all_results.append(run_and_save(judge, tau_sample, f"{model_key} retail_sample"))

    # -- Summary --
    console.print("\n[bold]═══ ALL RESULTS ═══[/bold]")
    table = Table()
    table.add_column("Experiment")
    table.add_column("N", justify="right")
    table.add_column("DR", justify="right")
    table.add_column("FPR", justify="right")
    table.add_column("F1", justify="right")
    table.add_column("Cat.Align", justify="right")
    for r in all_results:
        dr = f"{r['detection_rate']:.1%}" if r["detection_rate"] is not None else "N/A"
        fpr = f"{r['fpr']:.1%}" if r["fpr"] is not None else "N/A"
        table.add_row(r["label"], str(r["n"]), dr, fpr, f"{r['f1']:.3f}", f"{r['category_alignment']:.3f}")
    console.print(table)

    # Save combined results
    combined_path = RESULTS_DIR / "all_results.json"
    combined_path.write_text(json.dumps(all_results, indent=2, default=str))
    console.print(f"\n[dim]Combined results: {combined_path}[/dim]")


if __name__ == "__main__":
    main()
