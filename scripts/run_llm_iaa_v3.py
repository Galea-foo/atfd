#!/usr/bin/env python3
"""LLM-proxy IAA v3 — frontier models via headless CLI + Gemini API.

Annotators:
  1. Claude Sonnet 4 (claude -p)
  2. GPT-5 (codex exec)
  3. Gemini 3.1 Flash Lite (Google AI API)

Simple classification prompt. No few-shot (frontier models don't need it).
Two-turn: outcome first, then category if non-pass.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from atfd.metrics import fleiss_kappa

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "results" / "annotations" / "sample_manifest.json"
OUTPUT_DIR = ROOT / "results" / "iaa_v3"

# Load .env
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

OUTCOME_PROMPT = """\
Classify this AI agent trajectory into exactly one outcome.

Rules:
- "pass" — agent completed the user's request correctly. Minor process issues \
(extra API calls, verbose responses, suboptimal ordering) are still pass. \
If the end state matches what was requested, it is pass.
- "degraded" — task was technically completed but output quality is clearly \
substandard (shallow analysis, missing key details, poor tone). The core \
request WAS fulfilled, just poorly.
- "fail" — material error that means the user's request was NOT fulfilled: \
wrong action taken, required step skipped, system left in wrong state, \
wrong information given, or agent crashed/timed out.

Domain-specific guidance:
- Customer service (retail/airline): if the customer's actual request was \
resolved (order cancelled, flight rebooked, refund issued), it is pass — \
even if the agent was verbose or took extra steps.
- Coding (SWE-bench): if the code change resolves the issue and tests pass, \
it is pass — code style or approach doesn't determine pass/fail.
- Synthetic: these are hand-crafted to have clear labels. "degraded" means \
quality was poor but the task was completed.
- Toolathlon: long tool chains. If the final result is correct, it is pass — \
even if intermediate steps look messy.

Domain: {domain}
Task: {task_description}

Events:
{events_text}

Respond with ONLY one word: pass, degraded, or fail
"""

CATEGORY_PROMPT = """\
This trajectory was classified as "{outcome}". Identify the PRIMARY failure category.

Categories:
- action: wrong tool, wrong arguments, missing required action
- state: system/database left in wrong state
- communication: wrong info, missing info, hallucination
- quality: shallow output, inefficient approach, poor tone
- process: tool loops, circular delegation, context overflow, bad planning
- safety: unauthorized access, data leak, policy violation
- infrastructure: timeout, system error, max steps

Domain: {domain}
Task: {task_description}
Events (summary): {events_summary}

Respond with ONLY one word: action, state, communication, quality, process, safety, or infrastructure
"""

# ── CLI backends ───────────────────────────────────────────────────────────

def call_claude(prompt: str) -> str:
    for attempt in range(3):
        try:
            result = subprocess.run(
                ["claude", "-p", "--output-format", "json", "--model", "sonnet"],
                input=prompt, capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                return ""
            output = json.loads(result.stdout)
            return output.get("result", "")
        except Exception:
            if attempt < 2:
                time.sleep(2 ** attempt)
            continue
    return ""


def call_codex(prompt: str) -> str:
    for attempt in range(3):
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                output_path = f.name

            result = subprocess.run(
                ["codex", "exec", "--ephemeral", "--skip-git-repo-check",
                 "--json", "-o", output_path, "-"],
                input=prompt, capture_output=True, text=True, timeout=180,
            )

            text = ""
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "item.completed":
                    item = event.get("item", {})
                    for content in item.get("content", []):
                        if content.get("type") == "output_text":
                            text += content.get("text", "")

            if not text:
                try:
                    text = Path(output_path).read_text().strip()
                except Exception:
                    pass

            if text:
                return text
            if attempt < 2:
                time.sleep(2 ** attempt)
        except Exception:
            if attempt < 2:
                time.sleep(2 ** attempt)
            continue
    return ""


def call_gemini(prompt: str) -> str:
    import urllib.request
    import urllib.error

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={GEMINI_API_KEY}"
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 256},
    }).encode()

    for attempt in range(5):
        try:
            req = urllib.request.Request(url, data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            return ""
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = min((2 ** attempt) * 5, 60)
                print(f" RL{wait}s", end="", flush=True)
                time.sleep(wait)
                continue
            print(f" ERR:{e.code}", end="", flush=True)
            return ""
        except Exception as e:
            if attempt < 4:
                time.sleep(2 ** attempt)
                continue
            return ""
    return ""


ANNOTATORS = {
    "claude_sonnet": {"call": call_claude, "display": "Claude"},
    "gpt5_codex": {"call": call_codex, "display": "GPT-5"},
    "gemini_pro": {"call": call_gemini, "display": "Gemini"},
}

# ── Trajectory loading ─────────────────────────────────────────────────────

sys.path.insert(0, str(ROOT / "scripts"))
import run_llm_iaa_proxy as v1

def parse_outcome(raw: str) -> str:
    raw = raw.lower().strip().strip('"').strip("'")
    if not raw:
        return "fail"
    first = raw.split()[0].strip(".,;:")
    for label in ("pass", "degraded", "fail"):
        if label in first:
            return label
    for label in ("pass", "degraded", "fail"):
        if label in raw:
            return label
    return "fail"

def parse_category(raw: str) -> str:
    raw = raw.lower().strip().strip('"').strip("'")
    if not raw:
        return "unknown"
    valid = {"action", "state", "communication", "quality", "process", "safety", "infrastructure"}
    first = raw.split()[0].strip(".,;:")
    for cat in valid:
        if cat in first:
            return cat
    for cat in valid:
        if cat in raw:
            return cat
    return "unknown"


def main():
    manifest = json.loads(MANIFEST.read_text())
    print(f"IAA v3 — frontier models, {len(manifest)} trajectories")
    print(f"Annotators: Claude Sonnet 4, GPT-5 (Codex), Gemini 3.1 Flash Lite\n")

    results = {k: [] for k in ANNOTATORS}

    for i, entry in enumerate(manifest):
        domain, task_desc, events_text = v1.load_and_format(entry)
        tid_short = entry["trajectory_id"][:35]

        if len(events_text) > 15000:
            events_text = events_text[:15000] + "\n...[truncated]"
        events_summary = events_text[:4000]

        prompt = OUTCOME_PROMPT.format(
            domain=domain, task_description=task_desc, events_text=events_text,
        )

        print(f"  [{i+1}/50] {tid_short}", end="  ", flush=True)

        for akey, acfg in ANNOTATORS.items():
            raw = acfg["call"](prompt)
            outcome = parse_outcome(raw)

            category = None
            if outcome in ("fail", "degraded"):
                cat_prompt = CATEGORY_PROMPT.format(
                    outcome=outcome, domain=domain,
                    task_description=task_desc, events_summary=events_summary,
                )
                raw_cat = acfg["call"](cat_prompt)
                category = parse_category(raw_cat)

            results[akey].append({"outcome": outcome, "category": category})
            print(f"{acfg['display']}={outcome}", end="  ", flush=True)

        print()

    # ── Compute κ ──────────────────────────────────────────────────────────

    keys = list(ANNOTATORS.keys())
    n = len(manifest)

    binary = [[("pass" if results[k][i]["outcome"] == "pass" else "fail") for k in keys] for i in range(n)]
    outcome = [[results[k][i]["outcome"] for k in keys] for i in range(n)]

    cat_ratings = []
    for i in range(n):
        if all(results[k][i]["outcome"] in ("fail", "degraded") for k in keys):
            cat_ratings.append([results[k][i].get("category") or "unknown" for k in keys])

    kbin = fleiss_kappa(binary)
    kout = fleiss_kappa(outcome)
    kcat = fleiss_kappa(cat_ratings) if cat_ratings else 0.0

    ba = sum(1 for r in binary if len(set(r)) == 1)
    oa = sum(1 for r in outcome if len(set(r)) == 1)
    ca = sum(1 for r in cat_ratings if len(set(r)) == 1) if cat_ratings else 0

    print(f"\n{'='*60}")
    print(f"  IAA v3 RESULTS — FRONTIER MODELS")
    print(f"{'='*60}")
    print(f"  Items: {n}, Raters: 3")
    print(f"  Binary κ:   {kbin:.3f}  ({ba}/{n} agree)")
    print(f"  Outcome κ:  {kout:.3f}  ({oa}/{n} agree)")
    print(f"  Category κ: {kcat:.3f}  ({ca}/{len(cat_ratings)} agree, n={len(cat_ratings)})")
    print()

    for akey, acfg in ANNOTATORS.items():
        dist = Counter(r["outcome"] for r in results[akey])
        cats = Counter(r.get("category") or "-" for r in results[akey] if r["outcome"] != "pass")
        print(f"  {acfg['display']}: {dict(dist)} cats={dict(cats.most_common(5))}")

    # ── Save ───────────────────────────────────────────────────────────────

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for akey in keys:
        (OUTPUT_DIR / f"{akey}.json").write_text(json.dumps(results[akey], indent=2))

    summary = {
        "kappa_binary": round(kbin, 3),
        "kappa_outcome": round(kout, 3),
        "kappa_category": round(kcat, 3),
        "n": n, "n_cat": len(cat_ratings),
        "binary_agree": ba, "outcome_agree": oa, "category_agree": ca,
    }
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n  Saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
