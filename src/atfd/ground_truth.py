"""Run LLM judges to produce ground truth labels, then compute consensus."""
from __future__ import annotations
import json
from pathlib import Path
from rich.console import Console
from atfd.consensus import compute_consensus, ConsensusResult
from atfd.judges.llm_judge import LLMJudge
from atfd.schema import Outcome, Severity, SourceLabel, Trajectory

console = Console()
JUDGE_MODELS = ["gpt-4.1", "claude-sonnet-4", "llama-4-scout"]


def label_trajectory(trajectory: Trajectory) -> dict[str, SourceLabel]:
    """Run all LLM judges + use programmatic label to produce source labels."""
    labels: dict[str, SourceLabel] = {}

    # Programmatic label (from existing ground truth)
    labels["programmatic"] = SourceLabel(
        outcome=trajectory.ground_truth.outcome,
        failure_categories=trajectory.ground_truth.failure_categories,
        quality_categories=trajectory.ground_truth.quality_categories,
    )

    # LLM judge labels
    for model_key in JUDGE_MODELS:
        judge = LLMJudge(model_key=model_key)
        output = judge.evaluate(trajectory)

        failure_cats = [f.category for f in output.findings if f.severity == Severity.ERROR]
        quality_cats = [f.category for f in output.findings if f.category.startswith("quality.")]

        if output.has_failure and failure_cats:
            outcome = Outcome.FAIL
        elif quality_cats:
            outcome = Outcome.DEGRADED
        else:
            outcome = Outcome.PASS

        labels[model_key] = SourceLabel(
            outcome=outcome,
            failure_categories=failure_cats,
            quality_categories=quality_cats,
            reasoning=output.findings[0].description if output.findings else "",
        )

    return labels


def run_consensus_pipeline(
    trajectories: list[Trajectory],
    output_path: Path,
    skip_existing: bool = True,
) -> list[ConsensusResult]:
    """Run full consensus pipeline on all trajectories."""
    output_path.mkdir(parents=True, exist_ok=True)
    results: list[ConsensusResult] = []

    for i, traj in enumerate(trajectories):
        cache_file = output_path / f"{traj.trajectory_id}_labels.json"
        if skip_existing and cache_file.exists():
            cached = json.loads(cache_file.read_text())
            labels = {k: SourceLabel.model_validate(v) for k, v in cached.items()}
        else:
            console.print(f"  [{i+1}/{len(trajectories)}] Labeling {traj.trajectory_id}...")
            labels = label_trajectory(traj)
            cache_file.write_text(json.dumps(
                {k: v.model_dump() for k, v in labels.items()}, indent=2, default=str
            ))

        consensus = compute_consensus(labels)
        results.append(consensus)
        console.print(
            f"    → {consensus.outcome.value} ({consensus.consensus})"
            f" cats={consensus.failure_categories}"
        )

    return results
