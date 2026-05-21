"""Compute Fleiss' kappa with bootstrap 95% CIs on IAA v4 results.

Usage:
    cd /Users/sohan/Documents/galea-org/atfd
    source .venv/bin/activate
    PYTHONPATH=src python3 scripts/compute_kappa_ci.py
"""

from __future__ import annotations

import json
from pathlib import Path

from atfd.metrics import fleiss_kappa, bootstrap_ci

# ---------------------------------------------------------------------------
# Load annotator files
# ---------------------------------------------------------------------------

RESULTS_DIR = Path(__file__).parent.parent / "results" / "iaa_v4"

def load_annotations(path: Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)

claude  = load_annotations(RESULTS_DIR / "claude_sonnet.json")
gpt5    = load_annotations(RESULTS_DIR / "gpt5_codex.json")
gemini  = load_annotations(RESULTS_DIR / "gemini_flash.json")

assert len(claude) == len(gpt5) == len(gemini), (
    f"Length mismatch: claude={len(claude)}, gpt5={len(gpt5)}, gemini={len(gemini)}"
)

n_total = len(claude)
print(f"Total items in each file: {n_total}")

# ---------------------------------------------------------------------------
# Build aligned triples — skip items where any annotator is missing / errored.
# The summary.json notes 2 Gemini failures excluded → keep only items where
# all three annotators have a valid outcome.
# ---------------------------------------------------------------------------

VALID_OUTCOMES = {"pass", "fail", "degraded"}

triples: list[tuple[dict, dict, dict]] = []
skipped = []
for i, (c, g5, gm) in enumerate(zip(claude, gpt5, gemini)):
    if (c["outcome"] in VALID_OUTCOMES
            and g5["outcome"] in VALID_OUTCOMES
            and gm["outcome"] in VALID_OUTCOMES):
        triples.append((c, g5, gm))
    else:
        skipped.append(i)

print(f"Valid triples (all 3 annotators present): {len(triples)}")
if skipped:
    print(f"Skipped items (indices): {skipped}")

# ---------------------------------------------------------------------------
# Helper: extract top-level category label
# e.g. "process.planning_failure" → "process"
# "action" → "action"
# None / null → not applicable (only arises for pass outcomes)
# ---------------------------------------------------------------------------

def top_category(ann: dict) -> str | None:
    cat = ann.get("category")
    if cat is None:
        return None
    return cat.split(".")[0]


# ---------------------------------------------------------------------------
# FULL-SAMPLE kappa
# Treat each trajectory's outcome as the label.
# "pass" → label "pass"; "fail" / "degraded" → label as-is.
# (Three-way: pass / fail / degraded)
# ---------------------------------------------------------------------------

full_ratings: list[list[str]] = [
    [c["outcome"], g5["outcome"], gm["outcome"]]
    for c, g5, gm in triples
]

kappa_full = fleiss_kappa(full_ratings)

def kappa_full_stat(data):
    return fleiss_kappa(data)

ci_full_lo, ci_full_hi = bootstrap_ci(
    full_ratings,
    stat_fn=kappa_full_stat,
    n_resamples=10_000,
    confidence=0.95,
    seed=42,
)

print()
print("=" * 60)
print("FULL-SAMPLE KAPPA (all trajectories, outcome: pass/fail/degraded)")
print("=" * 60)
print(f"  N                 = {len(full_ratings)}")
print(f"  Fleiss' kappa     = {kappa_full:.4f}")
print(f"  95% CI            = [{ci_full_lo:.4f}, {ci_full_hi:.4f}]")


# ---------------------------------------------------------------------------
# NON-PASS subset
# Keep only items where at least 2 of 3 annotators say fail OR degraded.
# ---------------------------------------------------------------------------

def is_non_pass(outcome: str) -> bool:
    return outcome in ("fail", "degraded")

non_pass_triples: list[tuple[dict, dict, dict]] = []
for c, g5, gm in triples:
    votes_non_pass = sum([
        is_non_pass(c["outcome"]),
        is_non_pass(g5["outcome"]),
        is_non_pass(gm["outcome"]),
    ])
    if votes_non_pass >= 2:
        non_pass_triples.append((c, g5, gm))

print()
print("=" * 60)
print("NON-PASS SUBSET (≥2 of 3 annotators say fail or degraded)")
print("=" * 60)
print(f"  N (non-pass subset) = {len(non_pass_triples)}")

# For the non-pass subset kappa, use the top-level category as the label.
# Items where an annotator says "pass" on a majority-non-pass item still need
# a label.  We use the outcome itself ("pass") as the label for that rater
# to keep the data well-defined.
def label_for(ann: dict) -> str:
    if ann["outcome"] == "pass":
        return "pass"
    cat = top_category(ann)
    if cat is None:
        # fail/degraded with no category → use outcome as fallback
        return ann["outcome"]
    return cat

non_pass_ratings: list[list[str]] = [
    [label_for(c), label_for(g5), label_for(gm)]
    for c, g5, gm in non_pass_triples
]

if len(non_pass_ratings) < 2:
    print("  WARNING: too few items for kappa computation.")
else:
    kappa_np = fleiss_kappa(non_pass_ratings)

    def kappa_np_stat(data):
        return fleiss_kappa(data)

    ci_np_lo, ci_np_hi = bootstrap_ci(
        non_pass_ratings,
        stat_fn=kappa_np_stat,
        n_resamples=10_000,
        confidence=0.95,
        seed=42,
    )

    print(f"  Categories used     = {sorted(set(lbl for row in non_pass_ratings for lbl in row))}")
    print(f"  Fleiss' kappa       = {kappa_np:.4f}")
    print(f"  95% CI              = [{ci_np_lo:.4f}, {ci_np_hi:.4f}]")


# ---------------------------------------------------------------------------
# STRICT NON-PASS subset (all 3 annotators say fail or degraded)
# This matches the n_cat=25 / kappa_category=0.608 in summary.json
# ---------------------------------------------------------------------------

strict_non_pass_triples: list[tuple[dict, dict, dict]] = [
    (c, g5, gm)
    for c, g5, gm in triples
    if is_non_pass(c["outcome"]) and is_non_pass(g5["outcome"]) and is_non_pass(gm["outcome"])
]

print()
print("=" * 60)
print("STRICT NON-PASS SUBSET (all 3 annotators say fail or degraded)")
print("(matches n_cat=25 / kappa_category=0.608 in summary.json)")
print("=" * 60)
print(f"  N (strict non-pass subset) = {len(strict_non_pass_triples)}")

strict_non_pass_ratings: list[list[str]] = [
    [label_for(c), label_for(g5), label_for(gm)]
    for c, g5, gm in strict_non_pass_triples
]

if len(strict_non_pass_ratings) < 2:
    print("  WARNING: too few items for kappa computation.")
else:
    kappa_snp = fleiss_kappa(strict_non_pass_ratings)

    def kappa_snp_stat(data):
        return fleiss_kappa(data)

    ci_snp_lo, ci_snp_hi = bootstrap_ci(
        strict_non_pass_ratings,
        stat_fn=kappa_snp_stat,
        n_resamples=10_000,
        confidence=0.95,
        seed=42,
    )

    print(f"  Categories used     = {sorted(set(lbl for row in strict_non_pass_ratings for lbl in row))}")
    print(f"  Fleiss' kappa       = {kappa_snp:.4f}")
    print(f"  95% CI              = [{ci_snp_lo:.4f}, {ci_snp_hi:.4f}]")
    print()
    print(f"  NOTE: summary.json reports kappa_category=0.608 for n_cat=25.")
    print(f"  Recomputed kappa on the same n=25 strict subset = {kappa_snp:.4f}")


# ---------------------------------------------------------------------------
# Breakdown: outcome distribution per annotator
# ---------------------------------------------------------------------------

print()
print("=" * 60)
print("OUTCOME DISTRIBUTION (full valid set, N={})".format(len(triples)))
print("=" * 60)
for name, anns in [("claude_sonnet", [c for c, _, _ in triples]),
                   ("gpt5_codex",    [g5 for _, g5, _ in triples]),
                   ("gemini_flash",  [gm for _, _, gm in triples])]:
    counts = {}
    for a in anns:
        counts[a["outcome"]] = counts.get(a["outcome"], 0) + 1
    print(f"  {name:20s}: {counts}")

# Category breakdown on non-pass subset
print()
print("=" * 60)
print("CATEGORY DISTRIBUTION (non-pass subset, N={})".format(len(non_pass_triples)))
print("=" * 60)
for name, idx in [("claude_sonnet", 0), ("gpt5_codex", 1), ("gemini_flash", 2)]:
    counts: dict[str, int] = {}
    for triple in non_pass_triples:
        lbl = label_for(triple[idx])
        counts[lbl] = counts.get(lbl, 0) + 1
    print(f"  {name:20s}: {dict(sorted(counts.items()))}")
