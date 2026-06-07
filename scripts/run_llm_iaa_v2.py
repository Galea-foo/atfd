#!/usr/bin/env python3
"""LLM-proxy IAA v2 — all four improvements.

1. Binary framing (degraded→fail in scoring)
2. Stricter prompt with examples
3. Two-turn: outcome first, then category separately
4. Few-shot calibration (5 labeled examples before classification)

Annotators: Llama 4 Scout, Llama 3.3 70B, Qwen3 32B (all Groq)
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from atfd.metrics import fleiss_kappa

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "results" / "annotations" / "sample_manifest.json"
OUTPUT_DIR = ROOT / "results" / "iaa_v2"

def _load_dotenv():
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

_load_dotenv()

ANNOTATORS = {
    "llama4_scout": {
        "model_id": "meta-llama/llama-4-scout-17b-16e-instruct",
        "display": "Llama4Scout",
    },
    "llama33_70b": {
        "model_id": "llama-3.3-70b-versatile",
        "display": "Llama33-70B",
    },
    "qwen3_32b": {
        "model_id": "qwen/qwen3-32b",
        "display": "Qwen3-32B",
    },
}

# ── Few-shot calibration examples ──────────────────────────────────────────

FEW_SHOT_EXAMPLES = """
## Calibration examples (study these before classifying)

### Example A — PASS
Domain: retail
Task: Customer wants to check order status for order #7829
Events: [user] "What's the status of my order 7829?" → [assistant] calls get_order(7829) → [tool_result] status=shipped, tracking=1Z999... → [assistant] "Your order #7829 has shipped! Tracking: 1Z999..."
Label: **pass** — correct action, correct information relayed.

### Example B — PASS (imperfect process, correct result)
Domain: retail
Task: Customer wants to return item from order #4412
Events: [user] "I want to return the blue shirt from order 4412" → [assistant] calls get_order(4412) → [assistant] calls get_order(4412) again → [tool_result] order details → [assistant] calls initiate_return(order=4412, item="blue shirt") → [tool_result] return initiated → [assistant] "Return initiated for your blue shirt, you'll get a refund in 5-7 days."
Label: **pass** — duplicate API call is sloppy but the task was completed correctly. Process imperfection ≠ failure.

### Example C — FAIL
Domain: retail
Task: Customer wants to cancel order #5501
Events: [user] "Cancel order 5501" → [assistant] calls cancel_order(5502) → [tool_result] order 5502 cancelled → [assistant] "Your order has been cancelled."
Label: **fail** — wrong order cancelled. Category: **action** (wrong_args)

### Example D — FAIL
Domain: airline
Task: Rebook passenger on next available flight to LAX
Events: [user] "My flight was cancelled, rebook me to LAX" → [assistant] "I understand your frustration. Let me look into that for you." → [assistant] "I've found several options..." → [no tool calls made] → [assistant] "You should be all set!"
Label: **fail** — no actual rebooking action taken. Category: **action** (missing_action)

### Example E — DEGRADED
Domain: retail
Task: Provide detailed product comparison between items A and B
Events: [user] "Compare product A vs B in detail" → [assistant] calls get_product(A) → calls get_product(B) → [assistant] "Product A costs $50, Product B costs $60."
Label: **degraded** — comparison was requested but only price mentioned, missing features/reviews/specs. Task technically done but quality clearly insufficient.
"""

# ── Turn 1: Outcome classification ─────────────────────────────────────────

OUTCOME_PROMPT = FEW_SHOT_EXAMPLES + """
## Now classify this trajectory

Domain: {domain}
Task: {task_description}

Events:
{events_text}

## Rules
- "pass" = task completed correctly, even if process was imperfect
- "degraded" = task completed but output quality clearly substandard
- "fail" = material error — wrong result, missing action, wrong state

Respond with ONLY one word: pass, degraded, or fail
"""

# ── Turn 2: Category classification (only if fail/degraded) ────────────────

CATEGORY_PROMPT = """You classified this trajectory as "{outcome}".

Now identify the PRIMARY failure category from this list:
- action: wrong tool called, wrong arguments, or missing required action
- state: system/database left in wrong state
- communication: wrong info told to user, missing info, or hallucination
- quality: output is shallow, inefficient approach, poor tone
- process: tool loops, circular delegation, context overflow, bad planning
- safety: unauthorized access, data leak, policy violation
- infrastructure: timeout, system error, hit max steps

Domain: {domain}
Task: {task_description}
Events (summary): {events_summary}

Respond with ONLY one word from: action, state, communication, quality, process, safety, infrastructure
"""

# ── API call ───────────────────────────────────────────────────────────────

def call_groq(prompt: str, model_id: str, max_retries: int = 8) -> str:
    from openai import OpenAI
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY", ""),
    )
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=64,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                wait_match = re.search(r"(\d+(?:\.\d+)?)s", str(e))
                wait = float(wait_match.group(1)) + 2.0 if wait_match else min((2 ** attempt) * 5, 120)
                wait = min(wait, 120)
                print(f"    RL {wait:.0f}s...", end="", flush=True, file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"    ERR: {e}", file=sys.stderr)
                return ""
    return ""

# ── Trajectory loading (reuse from v1) ─────────────────────────────────────

sys.path.insert(0, str(ROOT / "scripts"))
import run_llm_iaa_proxy as v1

def load_and_format(entry):
    return v1.load_and_format(entry)

# ── Parse helpers ──────────────────────────────────────────────────────────

def parse_outcome(raw: str) -> str:
    raw = raw.lower().strip().strip('"').strip("'").split()[0] if raw else "fail"
    # Handle JSON responses
    if "{" in raw:
        m = re.search(r'"outcome"\s*:\s*"(\w+)"', raw)
        if m:
            raw = m.group(1)
    for label in ("pass", "degraded", "fail"):
        if label in raw:
            return label
    return "fail"

def parse_category(raw: str) -> str:
    raw = raw.lower().strip().strip('"').strip("'").split()[0] if raw else "unknown"
    valid = {"action", "state", "communication", "quality", "process", "safety", "infrastructure"}
    for cat in valid:
        if cat in raw:
            return cat
    return "unknown"

# ── Main ───────────────────────────────────────────────────────────────────

def main():
    manifest = json.loads(MANIFEST.read_text())
    print(f"Loaded {len(manifest)} trajectories")
    print(f"Annotators: {', '.join(c['display'] for c in ANNOTATORS.values())}")
    print(f"Improvements: few-shot calibration, stricter prompt, two-turn, binary scoring\n")

    results = {k: [] for k in ANNOTATORS}

    for i, entry in enumerate(manifest):
        domain, task_desc, events_text = load_and_format(entry)
        tid_short = entry["trajectory_id"][:35]

        # Truncate events for prompt
        if len(events_text) > 12000:
            events_text = events_text[:12000] + "\n...[truncated]"
        events_summary = events_text[:3000] if len(events_text) > 3000 else events_text

        outcome_prompt = OUTCOME_PROMPT.format(
            domain=domain, task_description=task_desc, events_text=events_text,
        )

        print(f"  [{i+1}/50] {tid_short}", end="  ", flush=True)

        for akey, acfg in ANNOTATORS.items():
            # Turn 1: outcome
            raw_outcome = call_groq(outcome_prompt, acfg["model_id"])
            outcome = parse_outcome(raw_outcome)

            # Turn 2: category (only if fail or degraded)
            category = None
            if outcome in ("fail", "degraded"):
                cat_prompt = CATEGORY_PROMPT.format(
                    outcome=outcome, domain=domain,
                    task_description=task_desc, events_summary=events_summary,
                )
                raw_cat = call_groq(cat_prompt, acfg["model_id"])
                category = parse_category(raw_cat)

            results[akey].append({"outcome": outcome, "category": category})
            print(f"{acfg['display'][:6]}={outcome}", end="  ", flush=True)

        print()

    # ── Compute κ ──────────────────────────────────────────────────────────

    annotator_keys = list(ANNOTATORS.keys())
    n = len(manifest)

    # 3-way outcome
    outcome_ratings = []
    for i in range(n):
        outcome_ratings.append([results[k][i]["outcome"] for k in annotator_keys])
    kappa_outcome = fleiss_kappa(outcome_ratings)

    # Binary: pass vs non-pass (improvement #1)
    binary_ratings = []
    for i in range(n):
        binary_ratings.append([
            "pass" if results[k][i]["outcome"] == "pass" else "fail"
            for k in annotator_keys
        ])
    kappa_binary = fleiss_kappa(binary_ratings)

    # Category: all-3-fail subset
    cat_ratings = []
    for i in range(n):
        outcomes = [results[k][i]["outcome"] for k in annotator_keys]
        if all(o in ("fail", "degraded") for o in outcomes):
            cat_ratings.append([
                results[k][i].get("category") or "unknown"
                for k in annotator_keys
            ])
    kappa_cat = fleiss_kappa(cat_ratings) if cat_ratings else 0.0

    # Agreement counts
    binary_agree = sum(1 for r in binary_ratings if len(set(r)) == 1)
    outcome_agree = sum(1 for r in outcome_ratings if len(set(r)) == 1)
    cat_agree = sum(1 for r in cat_ratings if len(set(r)) == 1) if cat_ratings else 0

    print(f"\n{'='*60}")
    print(f"  IAA v2 RESULTS (improved prompt)")
    print(f"{'='*60}")
    print(f"  Items: {n}, Raters: {len(annotator_keys)}")
    print(f"")
    print(f"  Binary κ (pass vs fail+degraded):  {kappa_binary:.3f}  ({binary_agree}/{n} agree)")
    print(f"  Outcome κ (pass/degraded/fail):    {kappa_outcome:.3f}  ({outcome_agree}/{n} agree)")
    print(f"  Category κ (non-pass subset n={len(cat_ratings)}):  {kappa_cat:.3f}  ({cat_agree}/{len(cat_ratings)} agree)")
    print()

    # Per-annotator stats
    for akey, acfg in ANNOTATORS.items():
        dist = Counter(r["outcome"] for r in results[akey])
        gt_outcomes = [m.get("gt_outcome", m.get("ground_truth_outcome", "")) for m in manifest]
        correct = sum(1 for r, gt in zip(results[akey], gt_outcomes) if r["outcome"] == gt)
        cats = Counter(r.get("category") or "-" for r in results[akey] if r["outcome"] != "pass")
        print(f"  {acfg['display']}: {dict(dist)} acc={correct}/{n} cats={dict(cats.most_common(5))}")

    # ── Save ───────────────────────────────────────────────────────────────

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for akey in annotator_keys:
        p = OUTPUT_DIR / f"{akey}.json"
        p.write_text(json.dumps(results[akey], indent=2))

    summary = {
        "kappa_binary": round(kappa_binary, 3),
        "kappa_outcome": round(kappa_outcome, 3),
        "kappa_category": round(kappa_cat, 3),
        "n_items": n,
        "n_raters": len(annotator_keys),
        "n_category_subset": len(cat_ratings),
        "binary_agreement": binary_agree,
        "outcome_agreement": outcome_agree,
        "category_agreement": cat_agree,
    }
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n  Saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
