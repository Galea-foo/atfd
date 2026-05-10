"""statistical_tests.py — Pairwise McNemar's test between all evaluated systems.

Usage:
    python results/analysis/statistical_tests.py

For each ordered pair (A, B), runs McNemar's test with continuity correction
and prints the chi-squared statistic and p-value.  Significant pairs
(p < 0.05) are highlighted with *.  The summary matrix is also printed as an
ASCII table for easy copy-paste into a paper.

Output columns:
    System A | System B | b (A✓B✗) | c (A✗B✓) | χ² | p-value | sig?
"""

from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo path bootstrap
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from atfd.metrics import mcnemar_test
from atfd.schema import JudgeOutput, Outcome, Severity

RAW_DIR = REPO_ROOT / "results" / "raw"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_outcome(traj_id: str) -> Outcome:
    tid = traj_id.lower()
    if "pass" in tid:
        return Outcome.PASS
    if "degraded" in tid:
        return Outcome.DEGRADED
    return Outcome.FAIL


def load_raw_file(path: Path) -> tuple[list[Outcome], list[JudgeOutput]]:
    records: list[dict] = json.loads(path.read_text())
    gt_outcomes: list[Outcome] = []
    outputs: list[JudgeOutput] = []
    for rec in records:
        gt_raw = rec.pop("gt_outcome", None)
        output = JudgeOutput.model_validate(rec)
        gt = Outcome(gt_raw) if gt_raw else _infer_outcome(output.trajectory_id)
        gt_outcomes.append(gt)
        outputs.append(output)
    return gt_outcomes, outputs


def _is_correct(gt: Outcome, output: JudgeOutput) -> bool:
    """A system is 'correct' on a trajectory when its has_failure prediction matches GT.

    PASS → correct if has_failure is False
    FAIL → correct if has_failure is True
    DEGRADED → correct if has_failure is False (degraded is not a hard failure)
    """
    if gt == Outcome.FAIL:
        return output.has_failure
    else:
        return not output.has_failure


def _align_systems(
    systems: dict[str, tuple[list[Outcome], list[JudgeOutput]]],
) -> dict[str, dict[str, bool]]:
    """Align correctness vectors by trajectory_id across all systems.

    Returns {system_name: {trajectory_id: is_correct}}.
    Only trajectories present in ALL systems are included (intersection).
    """
    # Build per-system dicts
    per_system: dict[str, dict[str, bool]] = {}
    for name, (gts, outputs) in systems.items():
        per_system[name] = {
            out.trajectory_id: _is_correct(gt, out)
            for gt, out in zip(gts, outputs)
        }

    # Intersection of trajectory ids
    all_ids_list = [set(d.keys()) for d in per_system.values()]
    common_ids = sorted(all_ids_list[0].intersection(*all_ids_list[1:])) if len(all_ids_list) > 1 else sorted(all_ids_list[0])

    # Filter to common ids
    aligned: dict[str, dict[str, bool]] = {}
    for name, d in per_system.items():
        aligned[name] = {tid: d[tid] for tid in common_ids}
    return aligned


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALPHA = 0.05


def main() -> None:
    raw_files = sorted(RAW_DIR.glob("*_raw.json"))
    if not raw_files:
        print(f"[statistical_tests] No raw files found in {RAW_DIR}")
        sys.exit(0)

    # Load all systems
    systems: dict[str, tuple[list[Outcome], list[JudgeOutput]]] = {}
    for path in raw_files:
        name = path.stem.replace("_raw", "")
        try:
            gt, outputs = load_raw_file(path)
            systems[name] = (gt, outputs)
        except Exception as exc:
            print(f"  [SKIP] {path.name}: {exc}")

    if len(systems) < 2:
        print("[statistical_tests] Need at least 2 systems for pairwise tests.")
        # Still run single-system summary
        for name, (gts, outputs) in systems.items():
            correct = [_is_correct(gt, out) for gt, out in zip(gts, outputs)]
            acc = sum(correct) / len(correct) if correct else 0.0
            print(f"  {name}: accuracy={acc:.1%} (n={len(correct)})")
        sys.exit(0)

    aligned = _align_systems(systems)
    n_common = len(next(iter(aligned.values())))
    system_names = sorted(aligned.keys())

    print(f"\nPairwise McNemar's Test (continuity correction, α={ALPHA})")
    print(f"Common trajectories: {n_common}")
    print(f"Systems: {', '.join(system_names)}\n")

    # Header
    col_w = 22
    hdr = (
        f"{'System A':<{col_w}} {'System B':<{col_w}} "
        f"{'b(A✓B✗)':>8} {'c(A✗B✓)':>8} {'χ²':>8} {'p-value':>10}  sig"
    )
    print(hdr)
    print("-" * len(hdr))

    sig_pairs: list[tuple[str, str, float, float]] = []

    for name_a, name_b in combinations(system_names, 2):
        vec_a = aligned[name_a]
        vec_b = aligned[name_b]
        tids = sorted(vec_a.keys())

        correct_a = [vec_a[t] for t in tids]
        correct_b = [vec_b[t] for t in tids]

        # McNemar contingency counts
        b = sum(1 for a, bv in zip(correct_a, correct_b) if a and not bv)
        c = sum(1 for a, bv in zip(correct_a, correct_b) if not a and bv)

        chi2, p = mcnemar_test(correct_a, correct_b)
        sig = "*" if p < ALPHA else " "

        print(
            f"{name_a:<{col_w}} {name_b:<{col_w}} "
            f"{b:>8d} {c:>8d} {chi2:>8.3f} {p:>10.4f}  {sig}"
        )

        if p < ALPHA:
            sig_pairs.append((name_a, name_b, chi2, p))

    print()

    # Summary p-value matrix
    print("P-value matrix (lower-left triangle):")
    header_row = " " * col_w + "".join(f"{n:>{col_w}}" for n in system_names)
    print(header_row)
    for i, name_a in enumerate(system_names):
        row = f"{name_a:<{col_w}}"
        for j, name_b in enumerate(system_names):
            if j < i:
                # Already computed: find in combinations
                a, b_ = (name_b, name_a) if name_b < name_a else (name_a, name_b)
                # Re-run (fast) rather than cache
                va = aligned[name_a]
                vb = aligned[name_b]
                tids = sorted(va.keys())
                ca = [va[t] for t in tids]
                cb = [vb[t] for t in tids]
                _, p = mcnemar_test(ca, cb)
                marker = "*" if p < ALPHA else " "
                row += f"{p:>{col_w - 1}.4f}{marker}"
            elif j == i:
                row += f"{'---':>{col_w}}"
            else:
                row += f"{'':>{col_w}}"
        print(row)

    print()

    if sig_pairs:
        print(f"Significant pairs (p < {ALPHA}):")
        for name_a, name_b, chi2, p in sig_pairs:
            print(f"  {name_a} vs {name_b}: χ²={chi2:.3f}, p={p:.4f}")
    else:
        print(f"No significant differences found (all p >= {ALPHA}).")

    print("\n[statistical_tests] Done.")


if __name__ == "__main__":
    main()
