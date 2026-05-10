"""ATFD benchmark CLI."""
from __future__ import annotations
import sys
from pathlib import Path
import click
from rich.console import Console

console = Console()
ROOT = Path(__file__).parent.parent.parent


@click.group()
def main():
    """ATFD — Agent Trajectory Failure Detection benchmark."""
    pass


@main.command()
@click.option("--dataset", type=click.Choice(["tau-bench", "swe-bench", "synthetic", "all"]), default="all")
def download(dataset):
    """Download benchmark datasets."""
    if dataset in ("tau-bench", "all"):
        console.print("[bold]Downloading tau-bench data...[/bold]")
        from datasets.tau_bench.download import download as dl_tau
        dl_tau()
    console.print("[green]Done.[/green]")


@main.command()
@click.option("--judge", type=click.Choice(["naive", "llm-gpt4", "llm-claude", "llm-llama", "galea", "galea-llm"]), required=True)
@click.option("--dataset", type=click.Choice(["tau-bench", "swe-bench", "synthetic", "all"]), default="all")
@click.option("--domain", type=str, default=None)
@click.option("--limit", type=int, default=0)
@click.option("--output-dir", type=click.Path(), default="results/raw")
def run(judge, dataset, domain, limit, output_dir):
    """Run a judge against a dataset."""
    from atfd.harness import print_results, run_benchmark
    trajectories = _load_trajectories(dataset, domain, limit)
    if not trajectories:
        console.print("[red]No trajectories loaded.[/red]")
        return
    judge_instance = _make_judge(judge)
    console.print(f"[bold]Judge:[/bold] {judge_instance.name}")
    console.print(f"[bold]Trajectories:[/bold] {len(trajectories)}")
    results = run_benchmark(judge_instance, trajectories, Path(output_dir))
    print_results(results)


def _load_trajectories(dataset, domain, limit):
    from atfd.schema import Trajectory
    trajectories: list[Trajectory] = []
    data_dir = ROOT / "data"
    if dataset in ("tau-bench", "all"):
        from atfd.adapters.tau_bench import TauBenchAdapter
        domains = [domain] if domain else ["retail", "airline", "telecom"]
        for d in domains:
            try:
                adapter = TauBenchAdapter(domain=d)
                trajectories.extend(adapter.load_dataset(data_dir / "tau_bench", limit=limit))
            except FileNotFoundError:
                console.print(f"[yellow]Skipping tau-bench/{d} — data not found[/yellow]")
    if dataset in ("swe-bench", "all"):
        from atfd.adapters.swe_bench import SweBenchAdapter
        for sub in ["openhands", "swe-agent"]:
            try:
                adapter = SweBenchAdapter(submission=sub)
                trajectories.extend(adapter.load_dataset(data_dir / "swe_bench", limit=limit))
            except FileNotFoundError:
                console.print(f"[yellow]Skipping swe-bench/{sub} — data not found[/yellow]")
    if dataset in ("synthetic", "all"):
        from atfd.adapters.synthetic import SyntheticAdapter
        try:
            adapter = SyntheticAdapter()
            trajectories.extend(adapter.load_dataset(ROOT / "datasets" / "synthetic", limit=limit))
        except FileNotFoundError:
            console.print("[yellow]Skipping synthetic — not found[/yellow]")
    return trajectories


def _make_judge(judge_key):
    if judge_key == "naive":
        from atfd.judges.naive import NaiveHeuristicJudge
        return NaiveHeuristicJudge()
    elif judge_key.startswith("llm-"):
        from atfd.judges.llm_judge import LLMJudge
        model_map = {"llm-gpt4": "gpt-4.1", "llm-claude": "claude-sonnet-4", "llm-llama": "llama-4-scout"}
        return LLMJudge(model_key=model_map[judge_key])
    elif judge_key == "galea":
        from atfd.judges.galea import GaleaJudge
        return GaleaJudge(mode="heuristic")
    elif judge_key == "galea-llm":
        from atfd.judges.galea import GaleaJudge
        return GaleaJudge(mode="llm")
    raise ValueError(f"Unknown judge: {judge_key}")


@main.command()
@click.option("--system", type=click.Choice(["galea", "llm"]), required=True)
@click.option("--dataset", type=click.Choice(["tau-bench", "swe-bench", "synthetic", "all"]), default="all")
@click.option("--output-dir", type=click.Path(), default="results/raw")
def ablation(system, dataset, output_dir):
    """Run ablation study."""
    trajectories = _load_trajectories(dataset, None, 0)
    if system == "galea":
        from results.analysis.ablation import run_galea_ablation
        run_galea_ablation(trajectories, "http://localhost:8000", Path(output_dir))
    elif system == "llm":
        from results.analysis.ablation import run_llm_judge_ablation
        run_llm_judge_ablation(trajectories, Path(output_dir))
