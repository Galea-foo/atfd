from __future__ import annotations
"""Run Galea investigator against tau-bench trajectories and score results.

Usage:
    python run_benchmark.py --domain retail --limit 20
    python run_benchmark.py --domain airline --trials all
    python run_benchmark.py --domain retail --limit 5 --api-url http://localhost:8001
"""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from rich.console import Console
from rich.table import Table

from converter import convert_simulation, extract_ground_truth

DATA_DIR = Path(__file__).parent / "data"
console = Console()


def load_results(domain: str) -> dict:
    """Load tau-bench results file for a domain."""
    results_dir = DATA_DIR / "results" / "final"
    candidates = list(results_dir.glob(f"*_{domain}_*trials.json"))
    if not candidates:
        console.print(f"[red]No results found for domain '{domain}' in {results_dir}")
        console.print(f"[yellow]Run: python download_data.py")
        sys.exit(1)
    # Prefer gpt-4.1 results
    target = next((c for c in candidates if "gpt-4.1-2025" in c.name and "mini" not in c.name), candidates[0])
    console.print(f"Loading: {target.name}")
    return json.loads(target.read_text())


def load_tasks(domain: str) -> dict[str, dict]:
    """Load task definitions keyed by task_id."""
    tasks_file = DATA_DIR / "domains" / domain / "tasks.json"
    if not tasks_file.exists():
        return {}
    tasks = json.loads(tasks_file.read_text())
    return {str(t.get("id", i)): t for i, t in enumerate(tasks)}


def ingest_trace(api_url: str, events: list[dict], project_id: str) -> bool:
    """Ingest trace events into Galea API."""
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{api_url}/v1/events",
            json={"events": events},
            headers={"x-galea-project": project_id},
        )
        return resp.status_code == 200


def run_investigation(api_url: str, trace_id: str) -> dict | None:
    """Trigger Galea investigation on a trace."""
    with httpx.Client(timeout=60) as client:
        resp = client.post(f"{api_url}/v1/traces/{trace_id}/summarize")
        if resp.status_code == 200:
            return resp.json()
    return None


def ensure_project(api_url: str, domain: str) -> str:
    """Create or get benchmark project."""
    project_id = f"bench-tau-{domain}"
    priorities = _domain_priorities(domain)
    with httpx.Client(timeout=10) as client:
        # Try to create; ignore if exists
        client.post(f"{api_url}/v1/projects", json={
            "id": project_id,
            "name": f"tau-bench {domain}",
            "priorities": priorities,
        })
    return project_id


def _domain_priorities(domain: str) -> list[str]:
    """Map tau-bench domains to Galea priority axes."""
    mapping = {
        "retail": ["correctness", "tool_safety", "audit"],
        "airline": ["correctness", "tool_safety", "audit", "regulatory_compliance"],
        "telecom": ["correctness", "tool_safety", "cost"],
    }
    return mapping.get(domain, ["correctness", "tool_safety"])


def score_investigation(findings: list[dict], ground_truth: dict) -> dict:
    """Score Galea's findings against tau-bench ground truth."""
    is_failure = ground_truth["is_failure"]
    has_findings = len(findings) > 0

    # Filter out baseline anomalies for FP scoring — these are informational,
    # not failure indicators. They fire because benchmark project has few traces.
    baseline_categories = {"anomaly_cost", "anomaly_latency", "anomaly_volume"}
    substantive_findings = [f for f in findings if f.get("category") not in baseline_categories]
    substantive_errors = [f for f in substantive_findings if f.get("severity") == "error"]

    has_error_findings = len(substantive_errors) > 0
    has_warning_findings = any(f.get("severity") == "warning" for f in substantive_findings)

    # Detection: did Galea flag the trajectory with substantive findings?
    detected = len(substantive_findings) > 0 if is_failure else True
    false_positive = has_error_findings and not is_failure

    # Category alignment
    galea_categories = {f.get("category") for f in findings}
    tau_failures = set(ground_truth["failure_types"])

    category_hits = 0
    if "wrong_action" in tau_failures and galea_categories & {"tool_error", "tool_risk_halt", "tool_risk_warn", "loop_suspect"}:
        category_hits += 1
    if "wrong_state_change" in tau_failures and galea_categories & {"tool_risk_halt", "tool_risk_warn", "failure"}:
        category_hits += 1
    if "wrong_communication" in tau_failures and galea_categories & {"correctness_no_citation", "hallucination"}:
        category_hits += 1
    if "missing_information" in tau_failures and galea_categories & {"correctness_no_citation"}:
        category_hits += 1

    return {
        "is_failure": is_failure,
        "detected": detected,
        "false_positive": false_positive,
        "finding_count": len(findings),
        "error_findings": sum(1 for f in findings if f.get("severity") == "error"),
        "warning_findings": sum(1 for f in findings if f.get("severity") == "warning"),
        "category_hits": category_hits,
        "tau_failure_types": list(tau_failures),
        "galea_categories": list(galea_categories),
        "reward": ground_truth["reward"],
    }


def print_results(scores: list[dict], domain: str):
    """Print benchmark results summary."""
    total = len(scores)
    failures = [s for s in scores if s["is_failure"]]
    successes = [s for s in scores if not s["is_failure"]]

    detected = sum(1 for s in failures if s["detected"])
    false_positives = sum(1 for s in successes if s["false_positive"])

    console.print(f"\n[bold]═══ Galea × tau-bench: {domain} ═══[/bold]\n")

    table = Table()
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_column("Detail")

    table.add_row("Total trajectories", str(total), "")
    table.add_row("Failed (tau-bench)", str(len(failures)), f"reward < 1.0")
    table.add_row("Passed (tau-bench)", str(len(successes)), f"reward = 1.0")
    table.add_row("", "", "")

    detection_rate = detected / len(failures) * 100 if failures else 0
    table.add_row("Detection rate", f"{detection_rate:.1f}%", f"{detected}/{len(failures)} failed runs flagged")

    fp_rate = false_positives / len(successes) * 100 if successes else 0
    table.add_row("False positive rate", f"{fp_rate:.1f}%", f"{false_positives}/{len(successes)} clean runs flagged as error")

    avg_findings_fail = sum(s["finding_count"] for s in failures) / len(failures) if failures else 0
    avg_findings_pass = sum(s["finding_count"] for s in successes) / len(successes) if successes else 0
    table.add_row("Avg findings (failed)", f"{avg_findings_fail:.1f}", "")
    table.add_row("Avg findings (passed)", f"{avg_findings_pass:.1f}", "")

    category_hits = sum(s["category_hits"] for s in failures)
    category_possible = sum(len(s["tau_failure_types"]) for s in failures)
    cat_rate = category_hits / category_possible * 100 if category_possible else 0
    table.add_row("Category alignment", f"{cat_rate:.1f}%", f"{category_hits}/{category_possible} failure types matched")

    console.print(table)

    # Severity calibration: correlation between reward and finding severity
    if failures:
        console.print("\n[bold]Severity calibration (failed runs):[/bold]")
        by_reward = sorted(failures, key=lambda s: s["reward"])
        for s in by_reward[:5]:
            console.print(
                f"  reward={s['reward']:.2f}  "
                f"errors={s['error_findings']} warnings={s['warning_findings']}  "
                f"tau={s['tau_failure_types']}"
            )


def main():
    parser = argparse.ArgumentParser(description="Galea × tau-bench benchmark")
    parser.add_argument("--domain", default="retail", choices=["retail", "airline", "telecom"])
    parser.add_argument("--limit", type=int, default=20, help="Max simulations to process (0=all)")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Galea API URL")
    parser.add_argument("--dry-run", action="store_true", help="Convert only, don't call API")
    args = parser.parse_args()

    results = load_results(args.domain)
    tasks = load_tasks(args.domain)
    simulations = results.get("simulations") or []

    if args.limit and args.limit > 0:
        simulations = simulations[:args.limit]

    console.print(f"[bold]Domain:[/bold] {args.domain}")
    console.print(f"[bold]Simulations:[/bold] {len(simulations)}")
    console.print(f"[bold]Tasks loaded:[/bold] {len(tasks)}")

    if not args.dry_run:
        project_id = ensure_project(args.api_url, args.domain)
        console.print(f"[bold]Project:[/bold] {project_id}")

    scores: list[dict] = []

    for i, sim in enumerate(simulations):
        task_id = str(sim.get("task_id", ""))
        task = tasks.get(task_id)
        trace_events = convert_simulation(sim, task, args.domain)
        ground_truth = extract_ground_truth(sim)
        trace_id = trace_events[0]["traceId"]

        status = "✗" if ground_truth["is_failure"] else "✓"
        console.print(
            f"  [{i+1}/{len(simulations)}] task={task_id} reward={ground_truth['reward']:.2f} "
            f"{status} events={len(trace_events)}",
            end="",
        )

        if args.dry_run:
            scores.append(score_investigation([], ground_truth))
            console.print(" [dim](dry-run)[/dim]")
            continue

        # Ingest
        ok = ingest_trace(args.api_url, trace_events, project_id)
        if not ok:
            console.print(" [red]ingest failed[/red]")
            continue

        # Investigate
        time.sleep(0.1)
        result = run_investigation(args.api_url, trace_id)
        if not result:
            console.print(" [red]investigation failed[/red]")
            continue

        summary = (result.get("summary") or {})
        findings = summary.get("findings") or []
        score = score_investigation(findings, ground_truth)
        scores.append(score)

        finding_summary = f"findings={score['finding_count']} (err={score['error_findings']})"
        console.print(f" → {finding_summary}")

    print_results(scores, args.domain)

    # Save detailed results
    out_path = Path(__file__).parent / f"results_{args.domain}.json"
    out_path.write_text(json.dumps(scores, indent=2))
    console.print(f"\n[dim]Detailed results: {out_path}[/dim]")


if __name__ == "__main__":
    main()
