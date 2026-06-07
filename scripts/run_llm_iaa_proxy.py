#!/usr/bin/env python3
"""LLM-proxy inter-annotator agreement study for ATFD.

Runs 3 LLM "annotators" on the 50 sampled trajectories using simple
classification prompts that are intentionally DIFFERENT from the judge
evaluation prompt (to avoid circularity).

Annotators:
  1. Llama 4 Scout (Groq)
  2. Llama 3.3 70B (Groq)
  3. Qwen3 32B (Groq)

Each annotator labels:
  - Binary outcome: pass / fail / degraded
  - Top-level failure category (if fail): one of 7 categories

Computes Fleiss' kappa for:
  - Binary outcome agreement (pass vs non-pass)
  - Three-way outcome agreement (pass / degraded / fail)
  - Top-level category agreement (on fail-only subset)

Results saved to results/iaa_proxy/.

Usage:
    python scripts/run_llm_iaa_proxy.py [--dry-run]

Requires:
    GROQ_API_KEY (env or .env) for all three annotators
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from atfd.metrics import fleiss_kappa  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "results" / "annotations" / "sample_manifest.json"
OUTPUT_DIR = ROOT / "results" / "iaa_proxy"

# Dataset roots (same as run_annotation.py)
TAU_BENCH_ROOT = ROOT / "datasets" / "tau_bench"
SWE_BENCH_DIR = ROOT / "data" / "swe_bench" / "openhands"
SYNTHETIC_DIR = ROOT / "datasets" / "synthetic" / "trajectories"
TOOLATHLON_DIR = ROOT / "data" / "toolathlon"

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

_load_dotenv()

# ---------------------------------------------------------------------------
# Annotator model configs
# ---------------------------------------------------------------------------

ANNOTATORS = {
    "llama4_scout_groq": {
        "provider": "groq",
        "model_id": "meta-llama/llama-4-scout-17b-16e-instruct",
        "display_name": "Llama 4 Scout (Groq)",
    },
    "llama33_70b_groq": {
        "provider": "groq",
        "model_id": "llama-3.3-70b-versatile",
        "display_name": "Llama 3.3 70B (Groq)",
    },
    "qwen3_32b_groq": {
        "provider": "groq",
        "model_id": "qwen/qwen3-32b",
        "display_name": "Qwen3 32B (Groq)",
    },
}

# ---------------------------------------------------------------------------
# Annotation prompt (intentionally different from the judge prompt)
#
# The judge prompt (in src/atfd/judges/prompts.py) is a two-stage
# investigation prompt that asks for detailed reasoning, failure events,
# and quality rubric scoring.  This annotation prompt is a simple
# one-shot classifier: just read and classify.
# ---------------------------------------------------------------------------

ANNOTATION_PROMPT = """\
You are classifying an AI agent trajectory. Read the trajectory and assign \
exactly one label.

## Decision rules

1. **"pass"** — The agent completed the user's request correctly. Minor \
stylistic issues do NOT make it a fail. If the right actions were taken \
and the end state is correct, it is a pass.
2. **"degraded"** — The task was completed but output quality is clearly \
substandard (e.g., shallow analysis, poor tone, unnecessary steps). The \
core request WAS fulfilled.
3. **"fail"** — The agent made a material error: wrong action, wrong \
result, missing a required step, leaving the system in a wrong state, \
or crashing. The user's request was NOT correctly fulfilled.

Key: if the task outcome is correct, label "pass" even if the process \
was imperfect. Only label "fail" when the end result is materially wrong.

## Examples

Example 1 — pass: Agent asked to cancel order #123. Agent calls \
cancel_order(123), confirms cancellation to user. → pass
Example 2 — fail: Agent asked to cancel order #123. Agent calls \
cancel_order(456) instead. → fail, category: action
Example 3 — degraded: Agent asked to summarize a report. Agent \
produces a 1-sentence summary missing key findings. → degraded

## Trajectory

Domain: {domain}
Task: {task_description}

Events:
{events_text}

## Classification

If "fail", identify the PRIMARY failure type: action, state, \
communication, quality, process, safety, or infrastructure.

Respond with ONLY a JSON object:
{{"outcome": "pass" or "degraded" or "fail", "category": "action" or null}}
"""


# ---------------------------------------------------------------------------
# Trajectory loading (reused from run_annotation.py)
# ---------------------------------------------------------------------------

_TAU_CACHE: dict[str, list[dict]] = {}


def _load_tau_sims(domain: str) -> list[dict]:
    if domain in _TAU_CACHE:
        return _TAU_CACHE[domain]
    results_dir = TAU_BENCH_ROOT / "results" / "final"
    candidates = list(results_dir.glob(f"*_{domain}_*.json"))
    preferred = [f for f in candidates if "gpt-4.1" in f.name]
    path = preferred[0] if preferred else sorted(candidates)[0]
    with path.open() as fh:
        data = json.load(fh)
    sims = data if isinstance(data, list) else data.get("simulations", data.get("results", []))
    _TAU_CACHE[domain] = sims
    return sims


def _truncate(text: str, max_len: int = 400) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _format_tau_events(messages: list[dict], max_events: int = 60) -> str:
    lines = []
    for i, msg in enumerate(messages[:max_events]):
        role = msg.get("role", "?")
        content = _truncate(str(msg.get("content", "")))
        line = f"[{i}] {role}: {content}"
        tool_calls = msg.get("tool_calls")
        if tool_calls and isinstance(tool_calls, list):
            for tc in tool_calls:
                fn = tc.get("function", tc)
                name = fn.get("name", tc.get("name", "?"))
                args = str(fn.get("arguments", tc.get("arguments", "")))[:200]
                line += f"\n     -> tool_call: {name}({args})"
        lines.append(line)
    return "\n".join(lines)


def _format_synthetic_events(events: list[dict], max_events: int = 60) -> str:
    lines = []
    for i, evt in enumerate(events[:max_events]):
        etype = evt.get("type", "?")
        content = _truncate(str(evt.get("content", "")))
        lines.append(f"[{i}] {etype}: {content}")
    return "\n".join(lines)


def _format_swe_events(history: list[dict], max_events: int = 40) -> str:
    lines = []
    for i, entry in enumerate(history[:max_events]):
        if not isinstance(entry, dict):
            continue
        action = entry.get("action", "")
        if action:
            args = entry.get("args", {})
            content = str(args.get("content", args.get("command", str(args))))[:300]
            lines.append(f"[{i}] ACTION({action}): {_truncate(content, 300)}")
        obs = entry.get("observation", "")
        if obs:
            obs_content = entry.get("content", str(entry))[:300]
            lines.append(f"    OBS({obs}): {_truncate(str(obs_content), 300)}")
    return "\n".join(lines)


def load_and_format(entry: dict) -> tuple[str, str, str]:
    """Load a trajectory and return (domain, task_description, events_text)."""
    loader = entry["loader"]
    args = entry["loader_args"]

    if loader == "tau_bench":
        sims = _load_tau_sims(args["domain"])
        sim = next((s for s in sims if str(s.get("id", "")) == str(args["sim_id"])), None)
        if sim is None:
            return args["domain"], "(not found)", "(no events)"
        # Task description
        tasks_file = TAU_BENCH_ROOT / "domains" / args["domain"] / "tasks.json"
        task_desc = ""
        if tasks_file.exists():
            with tasks_file.open() as fh:
                tasks = json.load(fh)
            if isinstance(tasks, list):
                tid = str(sim.get("task_id", ""))
                for t in tasks:
                    if str(t.get("id", "")) == tid:
                        task_desc = t.get("user_scenario", {}).get("reason_for_call", "")
                        break
        events_text = _format_tau_events(sim.get("messages", []))
        return args["domain"], task_desc or "(no task description)", events_text

    elif loader == "swe_bench":
        path = SWE_BENCH_DIR / args["filename"]
        with path.open() as fh:
            data = json.load(fh)
        history = data.get("history", data.get("trajectory", []))
        task_desc = _truncate(data.get("problem_statement", ""), 1500)
        events_text = _format_swe_events(history)
        return "coding", task_desc or "(no task description)", events_text

    elif loader == "synthetic":
        path = SYNTHETIC_DIR / args["filename"]
        with path.open() as fh:
            data = json.load(fh)
        domain = data.get("domain", "mixed")
        task_desc = data.get("description", "")
        events_text = _format_synthetic_events(data.get("events", []))
        return domain, task_desc or "(no task description)", events_text

    elif loader == "toolathlon":
        path = TOOLATHLON_DIR / args["filename"]
        with path.open() as fh:
            data = json.load(fh)
        messages = data.get("messages", [])
        if isinstance(messages, str):
            messages = json.loads(messages)
        events_text = _format_tau_events(messages[:80])
        task_desc = f"Toolathlon: {data.get('task_name', 'unknown')} ({data.get('modelname_run', 'unknown')})"
        return "tool_use", task_desc, events_text

    return "unknown", "(unknown loader)", "(no events)"


# ---------------------------------------------------------------------------
# LLM calling
# ---------------------------------------------------------------------------

def _call_anthropic(prompt: str, model_id: str, max_retries: int = 5) -> str:
    """Call Anthropic API and return the text response."""
    from anthropic import Anthropic

    client = Anthropic()
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=256,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = min((2 ** attempt) * 5, 120)
                print(f"    Rate limited (Anthropic), waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Rate limit exceeded after retries")


def _call_groq(prompt: str, model_id: str, max_retries: int = 5) -> str:
    """Call Groq API via OpenAI-compatible endpoint."""
    from openai import OpenAI

    api_key = os.environ.get("GROQ_API_KEY", "")
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait_match = re.search(r"(\d+(?:\.\d+)?)s", str(e))
                wait = float(wait_match.group(1)) + 1.0 if wait_match else (2 ** attempt) * 5
                wait = min(wait, 120)
                print(f"    Rate limited (Groq), waiting {wait:.0f}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Rate limit exceeded after retries")


def call_annotator(prompt: str, annotator_key: str) -> str:
    """Dispatch to the correct provider for the given annotator."""
    config = ANNOTATORS[annotator_key]
    provider = config["provider"]
    model_id = config["model_id"]

    if provider == "anthropic":
        return _call_anthropic(prompt, model_id)
    elif provider == "groq":
        return _call_groq(prompt, model_id)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def parse_annotation_response(raw: str) -> dict:
    """Parse the JSON annotation response from an LLM."""
    # Strip markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract JSON from the text
        match = re.search(r"\{[^}]+\}", raw)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}

    outcome = str(data.get("outcome", "fail")).lower().strip()
    if outcome not in ("pass", "degraded", "fail"):
        outcome = "fail"  # conservative default

    category = data.get("category")
    if category and isinstance(category, str):
        category = category.lower().strip()
        valid = {"action", "state", "communication", "quality", "process", "safety", "infrastructure"}
        if category not in valid:
            category = None

    return {"outcome": outcome, "category": category}


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_annotations(manifest: list[dict], dry_run: bool = False) -> dict[str, list[dict]]:
    """Run all 3 annotators on all trajectories.

    Returns a dict mapping annotator_key -> list of annotation dicts.
    """
    results: dict[str, list[dict]] = {k: [] for k in ANNOTATORS}

    for i, entry in enumerate(manifest):
        traj_id = entry["trajectory_id"]
        domain, task_desc, events_text = load_and_format(entry)

        prompt = ANNOTATION_PROMPT.format(
            domain=domain,
            task_description=task_desc,
            events_text=events_text,
        )

        # Cap prompt length to avoid context overflow on smaller models
        if len(prompt) > 25_000:
            prompt = prompt[:25_000] + "\n... [trajectory truncated for length]"

        print(f"  [{i+1}/{len(manifest)}] {traj_id} ({domain})", end="", flush=True)

        for ann_key, ann_config in ANNOTATORS.items():
            if dry_run:
                # In dry-run mode, use ground truth as a stand-in
                parsed = {
                    "outcome": entry.get("gt_outcome", "fail"),
                    "category": "action" if entry.get("gt_outcome") == "fail" else None,
                }
            else:
                try:
                    raw = call_annotator(prompt, ann_key)
                    parsed = parse_annotation_response(raw)
                except Exception as e:
                    print(f"\n    ERROR [{ann_config['display_name']}]: {e}", file=sys.stderr)
                    parsed = {"outcome": "fail", "category": None}

            results[ann_key].append({
                "trajectory_id": traj_id,
                "gt_outcome": entry.get("gt_outcome"),
                **parsed,
            })
            print(f"  {ann_config['display_name'][:8]}={parsed['outcome']}", end="", flush=True)

        print()  # newline after all annotators

    return results


def compute_agreement(all_annotations: dict[str, list[dict]], manifest: list[dict]) -> dict:
    """Compute Fleiss' kappa for various agreement dimensions."""
    annotator_keys = list(all_annotations.keys())
    n_items = len(manifest)
    n_raters = len(annotator_keys)

    # --- Binary agreement (pass vs non-pass) ---
    binary_ratings: list[list[str]] = []
    for i in range(n_items):
        row = []
        for ak in annotator_keys:
            outcome = all_annotations[ak][i]["outcome"]
            row.append("pass" if outcome == "pass" else "non-pass")
        binary_ratings.append(row)

    kappa_binary = fleiss_kappa(binary_ratings)

    # --- Three-way outcome agreement ---
    outcome_ratings: list[list[str]] = []
    for i in range(n_items):
        row = []
        for ak in annotator_keys:
            row.append(all_annotations[ak][i]["outcome"])
        outcome_ratings.append(row)

    kappa_outcome = fleiss_kappa(outcome_ratings)

    # --- Category agreement (fail-only subset) ---
    # Only include items where at least 2 annotators said "fail"
    fail_indices = []
    for i in range(n_items):
        fail_count = sum(
            1 for ak in annotator_keys
            if all_annotations[ak][i]["outcome"] == "fail"
        )
        if fail_count >= 2:
            fail_indices.append(i)

    kappa_category = None
    if len(fail_indices) >= 3:
        cat_ratings: list[list[str]] = []
        for i in fail_indices:
            row = []
            for ak in annotator_keys:
                cat = all_annotations[ak][i].get("category") or "none"
                row.append(cat)
            cat_ratings.append(row)
        kappa_category = fleiss_kappa(cat_ratings)

    # --- Per-annotator vs ground truth agreement ---
    gt_agreement = {}
    for ak in annotator_keys:
        correct = sum(
            1 for i in range(n_items)
            if all_annotations[ak][i]["outcome"] == manifest[i]["gt_outcome"]
        )
        gt_agreement[ak] = {
            "accuracy": correct / n_items if n_items > 0 else 0.0,
            "correct": correct,
            "total": n_items,
        }

    return {
        "n_items": n_items,
        "n_raters": n_raters,
        "kappa_binary": round(kappa_binary, 4),
        "kappa_outcome_3way": round(kappa_outcome, 4),
        "kappa_category_fail_subset": round(kappa_category, 4) if kappa_category is not None else None,
        "n_fail_subset": len(fail_indices),
        "gt_agreement": gt_agreement,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(agreement: dict, all_annotations: dict[str, list[dict]]) -> None:
    """Print a human-readable summary."""
    print("\n" + "=" * 70)
    print("  LLM-PROXY INTER-ANNOTATOR AGREEMENT RESULTS")
    print("=" * 70)

    print(f"\n  Items:  {agreement['n_items']}")
    print(f"  Raters: {agreement['n_raters']}")

    print(f"\n  Fleiss' kappa (binary: pass vs non-pass): {agreement['kappa_binary']}")
    print(f"  Fleiss' kappa (3-way: pass/degraded/fail): {agreement['kappa_outcome_3way']}")

    if agreement["kappa_category_fail_subset"] is not None:
        print(f"  Fleiss' kappa (category, fail subset N={agreement['n_fail_subset']}): "
              f"{agreement['kappa_category_fail_subset']}")
    else:
        print(f"  Fleiss' kappa (category): N/A (too few agreed-fail items)")

    print("\n  Interpretation:")
    for label, k_val in [
        ("binary", agreement["kappa_binary"]),
        ("3-way", agreement["kappa_outcome_3way"]),
    ]:
        if k_val < 0:
            interp = "less than chance"
        elif k_val < 0.20:
            interp = "slight"
        elif k_val < 0.40:
            interp = "fair"
        elif k_val < 0.60:
            interp = "moderate"
        elif k_val < 0.80:
            interp = "substantial"
        else:
            interp = "almost perfect"
        print(f"    {label}: kappa={k_val} ({interp})")

    print("\n  Per-annotator accuracy vs ground truth:")
    for ak, stats in agreement["gt_agreement"].items():
        display = ANNOTATORS[ak]["display_name"]
        print(f"    {display}: {stats['accuracy']:.1%} ({stats['correct']}/{stats['total']})")

    # Outcome distribution per annotator
    print("\n  Outcome distribution per annotator:")
    for ak in all_annotations:
        outcomes = {}
        for a in all_annotations[ak]:
            outcomes[a["outcome"]] = outcomes.get(a["outcome"], 0) + 1
        display = ANNOTATORS[ak]["display_name"]
        print(f"    {display}: {outcomes}")

    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="LLM-proxy IAA study for ATFD benchmark"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Skip LLM calls; use ground-truth labels as stand-in (for testing)",
    )
    args = parser.parse_args()

    if not MANIFEST.exists():
        print(f"ERROR: Manifest not found at {MANIFEST}")
        print("Run scripts/sample_iaa_trajectories.py first.")
        sys.exit(1)

    with MANIFEST.open() as fh:
        manifest = json.load(fh)

    print(f"Loaded {len(manifest)} trajectories from manifest.")
    print(f"Running {'DRY RUN' if args.dry_run else 'LIVE'} with 3 annotators:")
    for ak, cfg in ANNOTATORS.items():
        print(f"  - {cfg['display_name']} ({cfg['model_id']})")
    print()

    # Check API keys
    if not args.dry_run:
        if not os.environ.get("GROQ_API_KEY"):
            print("WARNING: GROQ_API_KEY not set. Groq calls will fail.", file=sys.stderr)

    # Run annotations
    all_annotations = run_annotations(manifest, dry_run=args.dry_run)

    # Compute agreement
    agreement = compute_agreement(all_annotations, manifest)

    # Print report
    print_report(agreement, all_annotations)

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save per-annotator results
    for ak, anns in all_annotations.items():
        out_path = OUTPUT_DIR / f"{ak}_annotations.json"
        with out_path.open("w") as fh:
            json.dump(anns, fh, indent=2)
        print(f"  Saved: {out_path}")

    # Save agreement summary
    summary_path = OUTPUT_DIR / "agreement_summary.json"
    with summary_path.open("w") as fh:
        json.dump(agreement, fh, indent=2)
    print(f"  Saved: {summary_path}")

    # Save combined results
    combined = {
        "manifest": manifest,
        "annotations": all_annotations,
        "agreement": agreement,
    }
    combined_path = OUTPUT_DIR / "iaa_proxy_results.json"
    with combined_path.open("w") as fh:
        json.dump(combined, fh, indent=2)
    print(f"  Saved: {combined_path}")


if __name__ == "__main__":
    main()
