#!/usr/bin/env python3
"""LLM-proxy IAA v4 — improved category prompts with single-turn structured output.

Fixes from v3:
  - Gemini 2.5 Flash replaces Gemini 3.1 Flash Lite (was returning 77% "unknown")
  - Single-turn prompt with JSON output (outcome + category in one call)
  - 4 few-shot examples from annotation guidelines
  - 5 category disambiguation rules for confusable pairs
  - Full 15K char trajectory context (not truncated 4K for category)
  - JSON output with chain-of-thought reasoning field
  - Gemini JSON mode via responseMimeType: "application/json"

Annotators:
  1. Claude Sonnet 4 (claude -p)
  2. GPT-5 (codex exec)
  3. Gemini 2.5 Flash (Google AI API)
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
OUTPUT_DIR = ROOT / "results" / "iaa_v4"

# Load .env
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ── Combined single-turn prompt ──────────────────────────────────────────────

COMBINED_PROMPT = """\
You are an expert evaluator of AI agent trajectories. Your task is to \
classify a trajectory and, if there is a failure, identify the primary \
failure category.

## Outcome Definitions

Assign exactly one outcome label:

- **pass** — The agent completed the user's request correctly. Actions, \
state changes, and communication are all appropriate. Minor process issues \
(extra API calls, verbose responses, suboptimal ordering) are still pass. \
If the end state matches what was requested, it is pass.
- **degraded** — The task was technically completed but output quality is \
clearly substandard (shallow analysis, missing key details, poor tone). The \
core request WAS fulfilled, just poorly.
- **fail** — Material error that means the user's request was NOT fulfilled: \
wrong action taken, required step skipped, system left in wrong state, \
wrong information given, or agent crashed/timed out.

Decision boundary: if the user's core request was fulfilled but the quality \
of fulfillment is poor, label "degraded". If the core request was NOT \
fulfilled or the agent made a factual/action error, label "fail".

## Failure Category Definitions

If outcome is "fail" or "degraded", assign exactly one category:

1. **action** — Wrong tool executed, wrong arguments passed, or a required \
action was omitted entirely. The agent DID something wrong or FAILED to do \
something necessary.
2. **state** — The system, database, or environment was left in an incorrect \
or incomplete state after the agent's actions. The actions themselves may have \
been correct, but the resulting state is wrong.
3. **communication** — The agent conveyed incorrect information, omitted \
critical information, or hallucinated facts in its response to the user. \
The actions may have been correct, but what was SAID to the user was wrong.
4. **quality** — The task was completed but the output is shallow, \
inefficient, poorly toned, or incomplete. Use this primarily for "degraded" \
outcomes. For "fail" outcomes, quality is rare — usually another category \
is more appropriate.
5. **process** — Flawed reasoning or execution flow: tool loops, circular \
delegation, context overflow, or poor planning. The agent's STRATEGY or \
EXECUTION PLAN was broken, not a single action.
6. **safety** — Unauthorized access, data exposure, or policy violations. \
The agent did something it should not have been allowed to do.
7. **infrastructure** — Timeout, system error, max steps reached, or other \
hard execution limits. External system failure, not agent logic.

## Category Disambiguation Rules

Use these rules to resolve commonly confused category pairs:

1. **action vs. state**: If the agent called the WRONG tool or passed WRONG \
arguments, it is "action". If the agent called the right tool but the \
resulting system state is incorrect (e.g., partial update, stale data), \
it is "state". Ask: was the mistake in WHAT the agent did, or in the \
RESULT of what it did?

2. **action vs. communication**: If the agent took the wrong action AND \
told the user something incorrect, pick "action" — the wrong action is the \
root cause, and the wrong communication is a downstream effect. Only pick \
"communication" when the agent's ACTIONS were correct but it SAID something \
wrong (e.g., gave the user incorrect information from a correct API call).

3. **communication vs. quality**: "communication" means factually wrong or \
missing critical information. "quality" means the information was technically \
correct but shallow, poorly organized, or poorly toned. If the response \
contains a factual error, it is "communication". If it is merely superficial, \
it is "quality".

4. **quality vs. process**: "quality" is about the OUTPUT — the final \
response or deliverable is substandard. "process" is about the EXECUTION — \
the agent looped, overflowed context, or had a flawed plan. If the agent \
went in circles before producing a bad answer, the primary issue is \
"process" (the looping caused the bad output).

5. **action vs. process**: A single wrong action is "action". A PATTERN of \
bad decisions (multiple wrong tools, circular retry loops, planning failures) \
is "process". If the agent made one clear mistake, it is "action". If the \
agent's overall approach was flawed, it is "process". \
**Key test:** count the events. If the agent spent 20+ events reading, \
searching, and exploring without ever attempting a solution (no code written, \
no tool applied to solve the problem), that is "process" (planning failure) \
— the agent failed to converge, not just failed to take one action.

## Few-Shot Examples

### Example 1: fail / action
Domain: retail
Task: Customer asks to change the shipping address on order #12345.
Events:
[0] system: You are a retail customer service agent. Tools: modify_order, cancel_order, get_order_details.
[1] user_message: Hi, I need to change my shipping address on order #12345.
[2] assistant_message: I'll help you with that. Let me cancel your order first.
[3] tool_call: cancel_order | {{"order_id": "12345"}}
[4] tool_result: Order #12345 has been cancelled.
[5] assistant_message: I've cancelled your order. You can place a new one with the correct address.

Correct answer:
{{"reasoning": "The customer asked for an address change, which requires modify_order. The agent used cancel_order instead — a destructive action the customer did not request. The order is now cancelled rather than modified. This is a wrong tool error.", "outcome": "fail", "category": "action"}}

### Example 2: degraded / quality
Domain: finance
Task: Analyze the risk profile of a diversified investment portfolio.
Events:
[0] system: You are a financial analysis agent with access to portfolio data tools.
[1] user_message: Please analyze the risk profile of portfolio P-7892.
[2] tool_call: get_portfolio | {{"id": "P-7892"}}
[3] tool_result: Portfolio contains 60% equities, 30% bonds, 10% alternatives. Total value: $2.4M.
[4] assistant_message: Your portfolio has moderate market risk due to 60% equity allocation. The bond allocation provides some stability. Overall risk is moderate.

Correct answer:
{{"reasoning": "The agent correctly retrieved portfolio data and provided a technically accurate response. However, the analysis only addresses market risk and ignores credit risk, liquidity risk, concentration risk, and interest rate risk. The task was completed but quality is substandard.", "outcome": "degraded", "category": "quality"}}

### Example 3: fail / communication
Domain: airline
Task: Customer asks about baggage allowance for their upcoming flight.
Events:
[0] system: You are an airline customer service agent. Tools: get_booking, get_policy, update_booking.
[1] user_message: What is the baggage allowance for my booking BK-9981?
[2] tool_call: get_booking | {{"booking_id": "BK-9981"}}
[3] tool_result: Booking BK-9981: Economy class, LAX-LHR, 1 checked bag (23kg) included.
[4] assistant_message: Your booking includes 2 checked bags up to 32kg each. You can also bring a carry-on.

Correct answer:
{{"reasoning": "The agent called the correct tool and got the right booking data. However, the response says 2 bags at 32kg when the actual policy is 1 bag at 23kg. The action was correct but the information communicated to the user is factually wrong.", "outcome": "fail", "category": "communication"}}

### Example 4: fail / process
Domain: coding
Task: Fix a bug in the authentication module where login fails for users with special characters in passwords.
Events:
[0] system: You are a coding agent. Tools: read_file, write_file, run_tests, search_code.
[1] user_message: Fix the login bug for special character passwords in auth.py.
[2] tool_call: read_file | {{"path": "auth.py"}}
[3] tool_result: [contents of auth.py with password validation function]
[4] tool_call: search_code | {{"query": "password validation"}}
[5] tool_result: Found 3 matches in auth.py, utils.py, tests/test_auth.py
[6] tool_call: read_file | {{"path": "auth.py"}}
[7] tool_result: [same contents of auth.py]
[8] tool_call: search_code | {{"query": "special characters password"}}
[9] tool_result: No matches found.
[10] tool_call: read_file | {{"path": "auth.py"}}
[11] tool_result: [same contents of auth.py again]
[12] tool_call: search_code | {{"query": "password escape"}}
[13] tool_result: No matches found.
[14] assistant_message: I was unable to identify the exact issue. The authentication module looks correct to me.

Correct answer:
{{"reasoning": "The agent read the same file 3 times and ran repetitive searches without making progress. It never attempted a fix or ran tests. The execution flow was circular — re-reading and re-searching without advancing. This is a planning/process failure, not a single wrong action.", "outcome": "fail", "category": "process"}}

## Domain-Specific Guidance

- **Customer service (retail/airline/telecom):** If the customer's actual request \
was resolved (order cancelled, flight rebooked, refund issued), it is pass — even \
if the agent was verbose or took extra steps.
- **Coding (SWE-bench):** If the code change resolves the issue and tests pass, it \
is pass — code style or approach does not determine pass/fail.
- **Synthetic:** These are hand-crafted to have clear labels. "degraded" means quality \
was poor but the task was completed.
- **Toolathlon:** Long tool chains. If the final result is correct, it is pass — even \
if intermediate steps look messy.

## Trajectory to Classify

Domain: {domain}
Task: {task_description}

Events:
{events_text}

## Output Instructions

Respond with ONLY a JSON object (no markdown, no extra text) with these fields:
- "reasoning": 1-3 sentences explaining your classification logic
- "outcome": exactly one of "pass", "degraded", or "fail"
- "category": exactly one of "action", "state", "communication", "quality", "process", "safety", "infrastructure", or null (null only if outcome is "pass")
"""

# ── CLI backends ───────────────────────────────────────────────────────────
# call_claude and call_codex copied exactly from v3 — they work fine.

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
    """Call Gemini 2.5 Flash. No JSON mode — parse plain text instead.

    Gemini 2.5 Flash is a thinking model: response has multiple parts
    (thinking + text). We iterate all parts to find text content.
    JSON mode (responseMimeType) is unreliable with thinking models,
    so we let the model respond freely and parse JSON from the text.
    """
    import urllib.request
    import urllib.error

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 1024,
            "thinkingConfig": {"thinkingBudget": 1024},
        },
    }).encode()

    for attempt in range(5):
        try:
            req = urllib.request.Request(url, data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            candidates = data.get("candidates", [])
            if not candidates:
                return ""
            parts = candidates[0].get("content", {}).get("parts", [])
            # Iterate all parts — thinking models put thought in early parts
            for part in parts:
                text = part.get("text", "")
                if text and ("outcome" in text or "pass" in text or "fail" in text):
                    return text
            # Fallback: return last non-empty text part
            for part in reversed(parts):
                text = part.get("text", "")
                if text.strip():
                    return text
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
    "gemini_flash": {"call": call_gemini, "display": "Gemini"},
}

# ── Trajectory loading ─────────────────────────────────────────────────────

sys.path.insert(0, str(ROOT / "scripts"))
import run_llm_iaa_proxy as v1

# ── JSON response parsing ─────────────────────────────────────────────────

VALID_OUTCOMES = {"pass", "degraded", "fail"}
VALID_CATEGORIES = {"action", "state", "communication", "quality", "process", "safety", "infrastructure"}


def parse_json_response(raw: str) -> dict:
    """Parse a JSON response with reasoning, outcome, and category.

    Tries multiple strategies:
    1. Strip markdown code fences, then json.loads
    2. Regex extraction of JSON object from surrounding text
    3. Plain text fallback (same logic as v3's parse_outcome/parse_category)
    """
    if not raw or not raw.strip():
        return {"reasoning": "", "outcome": "fail", "category": None}

    # Strategy 1: strip code fences and try json.loads
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        data = json.loads(cleaned)
        return _normalize_parsed(data)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: regex extract JSON object from text
    # Find the largest JSON-like object in the text
    matches = list(re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", raw))
    for match in reversed(matches):  # try longest/last match first
        try:
            data = json.loads(match.group())
            result = _normalize_parsed(data)
            if result["outcome"] in VALID_OUTCOMES:
                return result
        except (json.JSONDecodeError, ValueError):
            continue

    # Strategy 3: plain text fallback
    return _parse_plain_text(raw)


def _normalize_parsed(data: dict) -> dict:
    """Normalize a parsed JSON dict to standard form."""
    reasoning = str(data.get("reasoning", ""))

    outcome = str(data.get("outcome", "fail")).lower().strip()
    if outcome not in VALID_OUTCOMES:
        outcome = "fail"

    category = data.get("category")
    if category and isinstance(category, str):
        category = category.lower().strip()
        if category == "null" or category == "none":
            category = None
        elif category not in VALID_CATEGORIES:
            category = None
    elif category is not None:
        category = None

    # If outcome is pass, category should be null
    if outcome == "pass":
        category = None
    # If outcome is fail/degraded and no category, default to "action" for fail
    if outcome == "fail" and category is None:
        category = "action"
    if outcome == "degraded" and category is None:
        category = "quality"

    return {"reasoning": reasoning, "outcome": outcome, "category": category}


def _parse_plain_text(raw: str) -> dict:
    """Fallback: parse outcome and category from plain text (like v3)."""
    text = raw.lower().strip()

    # Parse outcome
    outcome = "fail"
    for label in ("pass", "degraded", "fail"):
        if label in text:
            outcome = label
            break

    # Parse category
    category = None
    if outcome in ("fail", "degraded"):
        for cat in VALID_CATEGORIES:
            if cat in text:
                category = cat
                break
        if category is None:
            category = "action" if outcome == "fail" else "quality"

    if outcome == "pass":
        category = None

    return {"reasoning": "", "outcome": outcome, "category": category}


# ── Resume support ────────────────────────────────────────────────────────

def load_partial_results() -> dict[str, list]:
    """Load previously saved partial results for resume."""
    results = {}
    for akey in ANNOTATORS:
        fpath = OUTPUT_DIR / f"{akey}.json"
        if fpath.exists():
            results[akey] = json.loads(fpath.read_text())
        else:
            results[akey] = []
    return results


def save_incremental(results: dict[str, list]):
    """Save current results after each trajectory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for akey in ANNOTATORS:
        (OUTPUT_DIR / f"{akey}.json").write_text(json.dumps(results[akey], indent=2))


# ── Main ──────────────────────────────────────────────────────────────────

PLACEHOLDER = {"outcome": "__skipped__", "category": None, "reasoning": ""}


def is_valid_result(r: dict) -> bool:
    """Check if result is a real annotation (not a skipped placeholder or quota-failure fallback)."""
    if r.get("outcome") == "__skipped__":
        return False
    if r.get("reasoning", "") == "" and r.get("outcome") == "fail":
        return False
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=list(ANNOTATORS.keys()),
                        help="Run only this annotator (skip others)")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text())
    active_annotators = {args.only: ANNOTATORS[args.only]} if args.only else ANNOTATORS

    print(f"IAA v4 — single-turn structured prompts, {len(manifest)} trajectories")
    print(f"Active annotators: {', '.join(a['display'] for a in active_annotators.values())}")
    print(f"Improvements: few-shot examples, disambiguation rules, JSON output, full context\n")

    results = load_partial_results()
    for akey in ANNOTATORS:
        if akey not in results or not results[akey]:
            results[akey] = []

    gemini_consecutive_failures = 0
    GEMINI_QUOTA_THRESHOLD = 5
    annotated_count = 0

    for i, entry in enumerate(manifest):
        domain, task_desc, events_text = v1.load_and_format(entry)
        tid_short = entry["trajectory_id"][:35]

        if len(events_text) > 15000:
            events_text = events_text[:15000] + "\n...[truncated]"

        any_work = False
        for akey in active_annotators:
            if i < len(results[akey]) and is_valid_result(results[akey][i]):
                continue
            any_work = True
            break

        if not any_work:
            continue

        prompt = COMBINED_PROMPT.format(
            domain=domain, task_description=task_desc, events_text=events_text,
        )

        print(f"  [{i+1}/50] {tid_short}", end="  ", flush=True)

        for akey, acfg in ANNOTATORS.items():
            while len(results[akey]) <= i:
                results[akey].append(dict(PLACEHOLDER))

            if akey not in active_annotators:
                if not is_valid_result(results[akey][i]):
                    print(f"{acfg['display']}=skip", end="  ", flush=True)
                else:
                    print(f"{acfg['display']}=cached", end="  ", flush=True)
                continue

            if is_valid_result(results[akey][i]):
                print(f"{acfg['display']}=cached", end="  ", flush=True)
                continue

            raw = acfg["call"](prompt)
            parsed = parse_json_response(raw)

            results[akey][i] = {
                "outcome": parsed["outcome"],
                "category": parsed["category"],
                "reasoning": parsed["reasoning"],
            }

            if akey == "gemini_flash":
                if not raw or raw.strip() == "":
                    gemini_consecutive_failures += 1
                else:
                    gemini_consecutive_failures = 0

            print(f"{acfg['display']}={parsed['outcome']}", end="  ", flush=True)

        print()
        annotated_count += 1
        save_incremental(results)

        if gemini_consecutive_failures >= GEMINI_QUOTA_THRESHOLD:
            print(f"\n  ⚠ Gemini quota exhausted ({gemini_consecutive_failures} consecutive failures).")
            print(f"  Saved progress. Re-run with: --only gemini_flash")
            break

    if annotated_count == 0:
        print("  All trajectories already annotated for active annotators.")

    all_complete = all(
        len(results[k]) >= len(manifest) and all(is_valid_result(r) for r in results[k])
        for k in ANNOTATORS
    )
    if not all_complete:
        missing = {}
        for k in ANNOTATORS:
            m = sum(1 for j in range(len(manifest)) if j >= len(results[k]) or not is_valid_result(results[k][j]))
            if m > 0:
                missing[ANNOTATORS[k]["display"]] = m
        print(f"\n  Incomplete: {missing}")
        print(f"  Run with --only <annotator_key> to fill gaps.")
        return

    # ── Compute κ ──────────────────────────────────────────────────────────

    keys = list(ANNOTATORS.keys())
    n = len(manifest)

    binary = [[("pass" if results[k][i]["outcome"] == "pass" else "fail") for k in keys] for i in range(n)]
    outcome = [[results[k][i]["outcome"] for k in keys] for i in range(n)]

    # Category κ: computed on items where ALL 3 annotators assigned non-pass outcome
    cat_ratings = []
    cat_indices = []
    for i in range(n):
        if all(results[k][i]["outcome"] in ("fail", "degraded") for k in keys):
            cat_ratings.append([results[k][i].get("category") or "unknown" for k in keys])
            cat_indices.append(i)

    kbin = fleiss_kappa(binary)
    kout = fleiss_kappa(outcome)
    kcat = fleiss_kappa(cat_ratings) if cat_ratings else 0.0

    ba = sum(1 for r in binary if len(set(r)) == 1)
    oa = sum(1 for r in outcome if len(set(r)) == 1)
    ca = sum(1 for r in cat_ratings if len(set(r)) == 1) if cat_ratings else 0

    print(f"\n{'='*60}")
    print(f"  IAA v4 RESULTS — FRONTIER MODELS (IMPROVED PROMPTS)")
    print(f"{'='*60}")
    print(f"  Items: {n}, Raters: 3")
    print(f"  Binary κ:   {kbin:.3f}  ({ba}/{n} agree)")
    print(f"  Outcome κ:  {kout:.3f}  ({oa}/{n} agree)")
    print(f"  Category κ: {kcat:.3f}  ({ca}/{len(cat_ratings)} agree, n={len(cat_ratings)})")
    print()

    for akey, acfg in ANNOTATORS.items():
        dist = Counter(r["outcome"] for r in results[akey])
        cats = Counter(r.get("category") or "-" for r in results[akey] if r["outcome"] != "pass")
        print(f"  {acfg['display']}: {dict(dist)} cats={dict(cats.most_common(7))}")

    # ── Pairwise category agreement breakdown ─────────────────────────────

    print(f"\n  Pairwise Category Agreement (on {len(cat_ratings)} items where all 3 = non-pass):")
    pair_names = [
        (0, 1, "Claude vs GPT-5"),
        (0, 2, "Claude vs Gemini"),
        (1, 2, "GPT-5 vs Gemini"),
    ]
    for ia, ib, label in pair_names:
        if not cat_ratings:
            print(f"    {label}: N/A (no items)")
            continue
        agree = sum(1 for r in cat_ratings if r[ia] == r[ib])
        total = len(cat_ratings)
        print(f"    {label}: {agree}/{total} ({agree/total:.1%})")

    # ── Comparison with v3 ────────────────────────────────────────────────

    v3_summary_path = ROOT / "results" / "iaa_v3" / "summary.json"
    if v3_summary_path.exists():
        v3 = json.loads(v3_summary_path.read_text())
        print(f"\n  {'─'*50}")
        print(f"  Comparison with v3:")
        print(f"    Binary κ:   v3={v3['kappa_binary']:.3f}  →  v4={kbin:.3f}  (Δ={kbin - v3['kappa_binary']:+.3f})")
        print(f"    Outcome κ:  v3={v3['kappa_outcome']:.3f}  →  v4={kout:.3f}  (Δ={kout - v3['kappa_outcome']:+.3f})")
        print(f"    Category κ: v3={v3['kappa_category']:.3f}  →  v4={kcat:.3f}  (Δ={kcat - v3['kappa_category']:+.3f})")
        print(f"    Cat items:  v3={v3['n_cat']}  →  v4={len(cat_ratings)}")

    # ── Save final ─────────────────────────────────────────────────────────

    save_incremental(results)

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
