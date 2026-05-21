# ATFD v6 — Reviewer Response Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address all 6 required changes + 2 suggested changes from v5 reviewer feedback, plus fill 5-version-pending LangSmith/Braintrust Toolathlon cells (ISS-007).

**Architecture:** Text edits to `paper/atfd.tex`, one new script (`scripts/compute_kappa_ci.py`) for bootstrap CIs, and running existing LangSmith/Braintrust baseline scripts on Toolathlon data. κ fixes = disclosure + framing + stats (no new experiments). Platform re-eval = existing 4-rule evaluators on existing Toolathlon trajectories.

**Tech Stack:** LaTeX (pdflatex + bibtex), Python 3.13 (numpy, existing `src/atfd/metrics.py` bootstrap infrastructure)

---

## Summary of Required Changes (from decision letter)

| #   | Issue   | What                                                    | Section      |
| --- | ------- | ------------------------------------------------------- | ------------ |
| 1   | ISS-042 | Report n=25 for κ=0.608 in abstract + §7, add CI        | Abstract, §7 |
| 2   | ISS-042 | Acknowledge 3-factor attribution confound               | §7           |
| 3   | ISS-038 | Report full-sample κ alongside conditioned κ            | §7           |
| 4   | ISS-037 | Elevate IAA non-independence to named limitation        | §9.8         |
| 5   | ISS-043 | Correct Landis-Koch characterization of AgentProp-Bench | §2           |
| 6   | ISS-010 | Add human IAA as named limitation                       | §9.8         |

## Suggested Changes (also implementing)

| #   | Issue   | What                                                                  | Section  |
| --- | ------- | --------------------------------------------------------------------- | -------- |
| S1  | ISS-044 | Qualify QDR=20.6% as synthetic-only in abstract                       | Abstract |
| S2  | —       | Disclose prompt development timeline (label leakage question from R1) | §7       |

---

### Task 1: Compute Bootstrap CI for κ=0.608 (n=25)

**Files:**

- Create: `scripts/compute_kappa_ci.py`
- Read: `results/iaa_v4/claude_sonnet.json`, `results/iaa_v4/gpt5_codex.json`, `results/iaa_v4/gemini_flash.json`
- Read: `src/atfd/metrics.py` (reuse `fleiss_kappa` and `bootstrap_ci`)

This script computes the 95% bootstrap CI on category κ=0.608 from the n=25 non-pass subset. We need the actual CI values before editing the paper.

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Compute bootstrap 95% CI for IAA v4 category kappa (n=25 non-pass subset).

Reads per-annotator JSON results, filters to non-pass trajectories,
extracts category labels, and bootstraps Fleiss' kappa.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from atfd.metrics import bootstrap_ci, fleiss_kappa


def load_annotations(results_dir: Path) -> dict[str, list[dict]]:
    annotators = {}
    for name in ["claude_sonnet", "gpt5_codex", "gemini_flash"]:
        path = results_dir / f"{name}.json"
        with open(path) as f:
            annotators[name] = json.load(f)
    return annotators


def main():
    results_dir = Path(__file__).resolve().parent.parent / "results" / "iaa_v4"
    annotators = load_annotations(results_dir)

    # Get list of trajectory IDs from first annotator
    first_key = list(annotators.keys())[0]
    traj_ids = [r["trajectory_id"] for r in annotators[first_key]]

    # Build per-trajectory annotations indexed by ID
    by_id: dict[str, dict[str, dict]] = {}
    for name, results in annotators.items():
        for r in results:
            tid = r["trajectory_id"]
            if tid not in by_id:
                by_id[tid] = {}
            by_id[tid][name] = r

    # Filter to non-pass: trajectories where ALL annotators labeled non-pass
    non_pass_ids = []
    for tid in traj_ids:
        if tid not in by_id:
            continue
        anns = by_id[tid]
        if len(anns) < 3:
            continue
        outcomes = [anns[k].get("outcome", anns[k].get("binary", "")).lower() for k in annotators]
        # Include if majority non-pass (at least 2 of 3 say fail or degraded)
        non_pass_count = sum(1 for o in outcomes if o in ("fail", "degraded"))
        if non_pass_count >= 2:
            non_pass_ids.append(tid)

    print(f"Total trajectories with all 3 annotators: {sum(1 for t in by_id if len(by_id[t]) == 3)}")
    print(f"Non-pass trajectories (majority rule): {len(non_pass_ids)}")

    # Extract category labels for non-pass subset
    annotator_keys = list(annotators.keys())
    ratings = []  # list of [cat_a, cat_b, cat_c] per trajectory
    for tid in non_pass_ids:
        anns = by_id[tid]
        cats = []
        for k in annotator_keys:
            cat = anns[k].get("category", "unknown")
            # Normalize to top-level category
            if "." in cat:
                cat = cat.split(".")[0]
            cats.append(cat.lower())
        ratings.append(cats)

    # Compute point estimate
    kappa = fleiss_kappa(ratings)
    print(f"\nCategory kappa (point estimate): {kappa:.3f}")
    print(f"n = {len(ratings)}")

    # Bootstrap CI
    def kappa_fn(sample):
        return fleiss_kappa(sample)

    lo, hi = bootstrap_ci(ratings, kappa_fn, n_resamples=10_000, confidence=0.95, seed=42)
    print(f"95% Bootstrap CI: [{lo:.3f}, {hi:.3f}]")

    # Also compute full-sample category kappa (all 48, treating pass as "pass" category)
    all_ids = [tid for tid in traj_ids if tid in by_id and len(by_id[tid]) == 3]
    full_ratings = []
    for tid in all_ids:
        anns = by_id[tid]
        cats = []
        for k in annotator_keys:
            outcome = anns[k].get("outcome", anns[k].get("binary", "")).lower()
            if outcome == "pass":
                cats.append("pass")
            else:
                cat = anns[k].get("category", "unknown")
                if "." in cat:
                    cat = cat.split(".")[0]
                cats.append(cat.lower())
        full_ratings.append(cats)

    full_kappa = fleiss_kappa(full_ratings)
    print(f"\nFull-sample kappa (n={len(full_ratings)}, pass as category): {full_kappa:.3f}")
    full_lo, full_hi = bootstrap_ci(full_ratings, kappa_fn, n_resamples=10_000, confidence=0.95, seed=42)
    print(f"95% Bootstrap CI: [{full_lo:.3f}, {full_hi:.3f}]")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script**

```bash
cd /Users/sohan/Documents/galea-org/atfd
source .venv/bin/activate
PYTHONPATH=src python3 scripts/compute_kappa_ci.py
```

Expected output: category κ=0.608 (or close) with a 95% CI, plus the full-sample κ with CI. Record the exact CI values — they go into the paper in Tasks 2-3.

- [ ] **Step 3: Commit**

```bash
git add scripts/compute_kappa_ci.py
git commit -m "feat: add bootstrap CI computation for IAA category kappa"
```

---

### Task 2: Fix Abstract — Add n=25, CI, and QDR qualifier (ISS-042, ISS-044)

**Files:**

- Modify: `paper/atfd.tex:131-137` (abstract κ reporting)
- Modify: `paper/atfd.tex:122-124` (abstract QDR mention)

Three changes in the abstract:

1. Add `(n=25 non-pass trajectories)` after κ=0.608

2. Add the bootstrap CI from Task 1

3. Qualify QDR=20.6% as synthetic-only
- [ ] **Step 1: Edit κ=0.608 line in abstract**

Change lines 131-135 from:

```latex
A 3-model LLM-proxy annotation study achieves $\kappa = 0.769$
(substantial) on binary failure detection and $\kappa = 0.764$
(substantial) on outcome classification, with category-level agreement
at $\kappa = 0.608$ (moderate), confirming that failure \emph{typing}
is harder than binary detection but achievable with structured prompts.
```

To (substitute actual CI values from Task 1):

```latex
A 3-model LLM-proxy annotation study achieves $\kappa = 0.769$
(substantial) on binary failure detection and $\kappa = 0.764$
(substantial) on outcome classification, with category-level agreement
at $\kappa = 0.608$ (moderate, $n = 25$ non-pass trajectories,
95\% CI $[X.XXX, X.XXX]$), confirming that failure \emph{typing}
is harder than binary detection but achievable with structured
annotation protocols.
```

Note: Change "structured prompts" → "structured annotation protocols" (reviewer R1's concern: "achievable with structured prompts" conflates prompt engineering with taxonomy validation).

- [ ] **Step 2: Edit QDR line in abstract**

Change lines 122-124 from:

```latex
and the only non-zero quality degradation detection
rate (QDR = 20.6\%).
```

To:

```latex
and the only non-zero quality degradation detection
rate (QDR = 20.6\% on the 34-trajectory synthetic degraded set).
```

- [ ] **Step 3: Compile paper to verify**

```bash
cd /Users/sohan/Documents/galea-org/atfd/paper && pdflatex atfd.tex && bibtex atfd && pdflatex atfd.tex && pdflatex atfd.tex
```

Expected: clean compile, no errors.

- [ ] **Step 4: Commit**

```bash
git add paper/atfd.tex
git commit -m "fix: add n=25 and CI to abstract kappa, qualify QDR as synthetic-only (ISS-042, ISS-044)"
```

---

### Task 3: Fix §7 — κ Attribution Confound + Full-Sample κ + CI (ISS-042, ISS-038)

**Files:**

- Modify: `paper/atfd.tex:514-521` (§7 proxy IAA paragraph)

This is the primary concern from all three reviewers. Three additions to §7:

1. Add n=25 and CI to category κ=0.608

2. Add attribution confound acknowledgment (3 simultaneous changes)

3. Report full-sample κ alongside conditioned κ

4. Disclose prompt development timeline (R1 label-leakage question)
- [ ] **Step 1: Edit the proxy IAA paragraph**

Replace lines 514-521 (the proxy IAA reporting paragraph):

```latex
families---Claude Sonnet~4 (Anthropic), GPT-5 (OpenAI), Gemini~2.5
Flash (Google)---on 50 sampled trajectories using a classification
prompt distinct from the judge prompt, with few-shot examples and
category disambiguation rules: binary $\kappa = 0.769$
(substantial), outcome $\kappa = 0.764$ (substantial), category
$\kappa = 0.608$ (moderate). Detection agreement is strong; failure
\emph{typing} is harder but achievable with structured annotation.
```

With:

```latex
families---Claude Sonnet~4 (Anthropic), GPT-5 (OpenAI), Gemini~2.5
Flash (Google)---on 48 sampled trajectories (of 50; 2 excluded due to
Gemini safety-filter refusals) using a classification prompt distinct
from the judge prompt, with few-shot examples and category
disambiguation rules: binary $\kappa = 0.769$ (substantial, $n = 48$),
outcome $\kappa = 0.764$ (substantial), category $\kappa = 0.608$
(moderate, $n = 25$ non-pass trajectories, 95\% CI $[X.XXX, X.XXX]$).
On the full 48-trajectory sample (treating ``pass'' as its own category),
$\kappa = X.XXX$ (95\% CI $[X.XXX, X.XXX]$).
Detection agreement is strong; failure \emph{typing} is harder but
achievable with structured annotation protocols.
```

- [ ] **Step 2: Add attribution confound paragraph after the κ reporting**

Insert a new paragraph after the proxy IAA reporting, before the "Circularity disclosure" paragraph (before line 523):

```latex
\paragraph{Attribution of category $\kappa$ improvement.}
The category $\kappa$ improved from $-0.058$ (v3, with Gemini~3.1~Flash
Lite returning ``unknown'' on 77\% of classifications) to 0.608 (v4,
with Gemini~2.5~Flash and structured prompts). This improvement reflects
three simultaneous changes: (1)~upgrading the Gemini annotator from
3.1~Flash~Lite to 2.5~Flash, (2)~adding structured prompts with
few-shot examples and category disambiguation rules, and (3)~restricting
category $\kappa$ computation to the $n = 25$ non-pass subset (category
is undefined for pass trajectories). We cannot attribute the improvement
to any single factor. The few-shot examples and disambiguation rules
were developed \emph{after} examining the v3 disagreement patterns
(specifically, Gemini's 77\% ``unknown'' rate and GPT-5's 68\%
``action'' bias), making the $\kappa = 0.608$ partly a measure of
calibration to the taxonomy designer's intent rather than independent
category discriminability. We report it as evidence of achievable
annotation consistency under a structured protocol, not as validation
of the taxonomy's natural discriminability.
```

- [ ] **Step 3: Compile paper**

```bash
cd /Users/sohan/Documents/galea-org/atfd/paper && pdflatex atfd.tex && bibtex atfd && pdflatex atfd.tex && pdflatex atfd.tex
```

Expected: clean compile.

- [ ] **Step 4: Commit**

```bash
git add paper/atfd.tex
git commit -m "fix: add kappa attribution confound, full-sample kappa, CI in §7 (ISS-042, ISS-038)"
```

---

### Task 4: Elevate ISS-037 to Named Limitation (IAA Non-Independence)

**Files:**

- Modify: `paper/atfd.tex:842-850` (§9.8 item 8)

Currently item 8 in the numbered limitations list. Reviewers want a named paragraph, not a bullet point.

- [ ] **Step 1: Replace item 8 with a named paragraph**

Remove item 8 from the enumerated list (lines 842-850):

```latex
  \item \textbf{IAA non-independence.} The LLM-proxy IAA study has three
    non-independence limitations: (a)~Claude Sonnet~4 serves as both an
    IAA annotator and an evaluated detection system; (b)~the 50-trajectory
    sample includes 15 synthetic trajectories designed by the paper's
    author using the same taxonomy being validated; and (c)~the taxonomy
    was designed by the same author. These limitations mean the IAA study
    functions as a cross-model consistency check rather than a fully
    independent validation. A human IAA study with external annotators
    remains future work.
```

And add it as a named paragraph after the `\end{enumerate}` (after line 851):

```latex
\paragraph{IAA non-independence (structural limitation).}
The LLM-proxy IAA study has three non-independence axes that cannot be
resolved by textual revision: (a)~Claude Sonnet~4 serves as both an
IAA annotator and an evaluated detection system, creating a shared-model
confound; (b)~15 of the 50 sampled trajectories are synthetic scenarios
designed by the paper's author using the same taxonomy, so annotators
classify author-designed failures against an author-designed rubric;
and (c)~the taxonomy itself was designed by the same author, closing
the loop between task design and evaluation criteria. These three axes
mean the IAA study functions as a \emph{cross-model consistency check}
--- evidence that three frontier LLMs apply the taxonomy similarly under
structured prompting --- rather than a fully independent validation of
taxonomy discriminability. Independent validation would require external
annotators (human or LLM) classifying trajectories they had no role in
designing, against a taxonomy they had no role in creating.
```

- [ ] **Step 2: Compile paper**

```bash
cd /Users/sohan/Documents/galea-org/atfd/paper && pdflatex atfd.tex && bibtex atfd && pdflatex atfd.tex && pdflatex atfd.tex
```

- [ ] **Step 3: Commit**

```bash
git add paper/atfd.tex
git commit -m "fix: elevate IAA non-independence to named limitation paragraph (ISS-037)"
```

---

### Task 5: Add Human IAA as Named Limitation (ISS-010)

**Files:**

- Modify: `paper/atfd.tex` — add after the ISS-037 paragraph from Task 4

This was item 3 in the limitations list but was just a brief mention. The editor requires it as a named limitation with explicit distinction between LLM-proxy and human IAA.

- [ ] **Step 1: Add named paragraph**

Insert after the ISS-037 paragraph added in Task 4:

```latex
\paragraph{Absence of human IAA (ISS-010).}
No human inter-annotator agreement study has been conducted on the
24-subcategory taxonomy. The LLM-proxy IAA ($\kappa = 0.608$ category,
$n = 25$) measures consistency across frontier LLMs, not human
annotator agreement. MAST~\citep{cemri2025mast} reports $\kappa = 0.88$
with human annotators on a 14-category taxonomy; whether ATFD's
finer-grained 24-subcategory taxonomy achieves comparable human
agreement is unknown. Fine-grained distinctions (e.g.,
\texttt{communication.wrong\_response} vs.\
\texttt{communication.hallucination}) may map poorly to human
intuitions. A human IAA study with trained external annotators is
the most important piece of future validation work.
```

- [ ] **Step 2: Update item 3 in the enumerated list to cross-reference**

Change lines 825-829 (item 3 in limitations list) from:

```latex
  \item \textbf{Ground truth.} LLM consensus ($\kappa = 0.557$ category)
    on synthetic only. LLM-based IAA proxy achieves $\kappa = 0.769$
    (binary), $\kappa = 0.608$ (category) with frontier models
    (\S\ref{sec:ground_truth}); human annotation may
    differ~\citep{groundtruth2025}.
```

To:

```latex
  \item \textbf{Ground truth.} LLM consensus ($\kappa = 0.557$ category)
    on synthetic only. See ``Absence of human IAA'' and ``IAA
    non-independence'' paragraphs below for structural limitations of
    the LLM-proxy IAA study.
```

- [ ] **Step 3: Compile paper**

```bash
cd /Users/sohan/Documents/galea-org/atfd/paper && pdflatex atfd.tex && bibtex atfd && pdflatex atfd.tex && pdflatex atfd.tex
```

- [ ] **Step 4: Commit**

```bash
git add paper/atfd.tex
git commit -m "fix: add human IAA as named limitation, cross-reference from item 3 (ISS-010)"
```

---

### Task 6: Correct Landis-Koch Characterization (ISS-043)

**Files:**

- Modify: `paper/atfd.tex:245-247` (§2 Related Work)

One-line fix. κ=0.432 is Landis-Koch "moderate" (0.41–0.60), not "poor-to-fair."

- [ ] **Step 1: Edit the AgentProp-Bench line**

Change lines 245-247:

```latex
AgentProp-Bench~\citep{agentpropbench2026} evaluates judge reliability
($\kappa = 0.432$, higher than \atfd's 0.320 but in the same
poor-to-fair range);
```

To:

```latex
AgentProp-Bench~\citep{agentpropbench2026} evaluates judge reliability
($\kappa = 0.432$, Landis-Koch ``moderate''; \atfd's consensus
$\kappa = 0.320$ falls in the adjacent ``fair'' band---both below the
$0.61$ substantial-agreement threshold);
```

- [ ] **Step 2: Compile paper**

```bash
cd /Users/sohan/Documents/galea-org/atfd/paper && pdflatex atfd.tex && bibtex atfd && pdflatex atfd.tex && pdflatex atfd.tex
```

- [ ] **Step 3: Commit**

```bash
git add paper/atfd.tex
git commit -m "fix: correct Landis-Koch characterization of AgentProp-Bench kappa (ISS-043)"
```

---

### Task 7: Update Author's Changelog and Appendix E κ table

**Files:**

- Modify: `paper/atfd.tex:874-892` (Author's Changelog)

- Modify: `paper/atfd.tex:1077-1088` (Appendix E κ table)

- Modify: `paper/atfd.tex:1107-1111` (Appendix E interpretation text)

- [ ] **Step 1: Add CI to Appendix E κ table**

Change lines 1079-1087 (the IAA table):

```latex
\begin{tabular}{@{}lcc@{}}
\toprule
\textbf{Measure} & \textbf{$\kappa$} & \textbf{Interpretation} \\
\midrule
Binary (pass vs.\ non-pass) & 0.769 & substantial \\
Outcome (pass/degraded/fail) & 0.764 & substantial \\
Category (non-pass subset, $n=25$) & 0.608 & moderate \\
\bottomrule
\end{tabular}
```

To (substitute actual CI values):

```latex
\begin{tabular}{@{}lccc@{}}
\toprule
\textbf{Measure} & \textbf{$\kappa$} & \textbf{95\% CI} & \textbf{Interpretation} \\
\midrule
Binary (pass vs.\ non-pass, $n=48$) & 0.769 & --- & substantial \\
Outcome (pass/degraded/fail, $n=48$) & 0.764 & --- & substantial \\
Category (non-pass subset, $n=25$) & 0.608 & $[X.XXX, X.XXX]$ & moderate \\
Full-sample (pass as category, $n=48$) & $X.XXX$ & $[X.XXX, X.XXX]$ & TBD \\
\bottomrule
\end{tabular}
```

- [ ] **Step 2: Update Appendix E interpretation text**

Change lines 1107-1111:

```latex
disambiguation rules. All three annotators show balanced
outcome distributions with no systematic fail-bias.
```

To:

```latex
disambiguation rules. The 95\% CI on category $\kappa$ is wide
($[X.XXX, X.XXX]$), reflecting the small $n = 25$ denominator; the
point estimate should be interpreted with this uncertainty in mind.
All three annotators show balanced outcome distributions with no
systematic fail-bias. Claude Sonnet~4 classifies 22 of 48 trajectories
as pass against a ground truth of 15 pass, suggesting possible
pass-over-classification; this pattern warrants investigation in
future annotation studies.
```

- [ ] **Step 3: Replace the Author's Changelog**

Replace lines 874-892 (the existing v4→v5 changelog) with:

```latex
\section*{Author's Changelog (v5 $\to$ v6)}
\begin{itemize}[leftmargin=2em,itemsep=1pt]
  \item Added $n = 25$ denominator and 95\% bootstrap CI for category
    $\kappa = 0.608$ in abstract, \S\ref{sec:ground_truth}, and
    Appendix (ISS-042).
  \item Acknowledged three-factor attribution confound (prompt engineering,
    model upgrade, sample restriction) for category $\kappa$ improvement;
    disclosed that disambiguation rules were developed after examining
    v3 disagreement patterns (ISS-042).
  \item Reported full-sample $\kappa$ alongside conditioned-subsample
    $\kappa$ in \S\ref{sec:ground_truth} and Appendix (ISS-038).
  \item Elevated IAA non-independence to named limitation paragraph with
    three explicit axes and honest scoping as ``cross-model consistency
    check'' (ISS-037).
  \item Corrected Landis-Koch characterization: AgentProp-Bench
    $\kappa = 0.432$ is ``moderate,'' not ``poor-to-fair'' (ISS-043).
  \item Added human IAA absence as named limitation with MAST comparison
    and explicit distinction between LLM-proxy and human agreement
    (ISS-010).
  \item Qualified QDR = 20.6\% in abstract as synthetic-only (ISS-044).
  \item Changed ``structured prompts'' to ``structured annotation
    protocols'' in abstract to avoid conflating prompt engineering with
    taxonomy validation.
\end{itemize}
```

- [ ] **Step 4: Compile paper**

```bash
cd /Users/sohan/Documents/galea-org/atfd/paper && pdflatex atfd.tex && bibtex atfd && pdflatex atfd.tex && pdflatex atfd.tex
```

- [ ] **Step 5: Commit**

```bash
git add paper/atfd.tex
git commit -m "fix: update changelog to v5→v6, add CI to appendix E table (ISS-042, ISS-038)"
```

---

### Task 8: Run LangSmith + Braintrust on Toolathlon (ISS-007)

**Files:**

- Modify: `baselines/langsmith/run_langsmith_eval.py` (add Toolathlon support)
- Modify: `baselines/braintrust/run_braintrust_eval.py` (add Toolathlon support)
- Modify: `paper/atfd.tex:652,660` (fill in `---†` cells in Table 4)

Toolathlon cells have been "pending" for 5 versions. R1 called it out explicitly. Both scripts already have the 4-rule evaluator logic — just need to load Toolathlon trajectories and run.

- [ ] **Step 1: Add Toolathlon to LangSmith script**

Add Toolathlon adapter import and dataset option to `baselines/langsmith/run_langsmith_eval.py`. The script currently loads synthetic via `SyntheticAdapter`. Add:

```python
from atfd.adapters.toolathlon import ToolathlonAdapter

# In load_and_upload_dataset or a new function:
def load_toolathlon():
    adapter = ToolathlonAdapter()
    return adapter.load_dataset(ROOT / "datasets" / "toolathlon")
```

Then add a `run_toolathlon()` function that runs the same 4 evaluators locally (no need to upload to LangSmith platform — just apply rules directly like the Braintrust script does for retail):

```python
def run_toolathlon_local():
    trajectories = load_toolathlon()
    print(f"\n═══ LangSmith × Toolathlon ({len(trajectories)} trajectories) ═══")

    fails = sum(1 for t in trajectories if t.ground_truth.outcome.value == "fail")
    passes = len(trajectories) - fails
    print(f"Ground truth: {fails} failures, {passes} passes")

    detected = 0
    false_positives = 0

    for traj in trajectories:
        events_dicts = [
            {"type": e.type.value, "content": e.content, "metadata": e.metadata}
            for e in traj.events
        ]
        output = {"events": events_dicts}

        flagged = combined_failure_evaluator(output)["score"] == 0
        is_fail = traj.ground_truth.outcome.value == "fail"

        if is_fail and flagged:
            detected += 1
        if not is_fail and flagged:
            false_positives += 1

    dr = detected / fails * 100 if fails > 0 else 0
    fpr = false_positives / passes * 100 if passes > 0 else 0

    print(f"Detection Rate: {dr:.1f}% ({detected}/{fails})")
    print(f"False Positive Rate: {fpr:.1f}% ({false_positives}/{passes})")
    return {"dataset": "toolathlon", "n": len(trajectories), "dr": dr, "fpr": fpr,
            "detected": detected, "false_positives": false_positives,
            "fails": fails, "passes": passes}
```

Call `run_toolathlon_local()` from `main()` and save results to `results/raw/langsmith_toolathlon.json`.

- [ ] **Step 2: Add Toolathlon to Braintrust script**

Same pattern — add to `baselines/braintrust/run_braintrust_eval.py`:

```python
from atfd.adapters.toolathlon import ToolathlonAdapter
```

Add `"toolathlon"` case to `load_trajectories()`:

```python
elif dataset_type == "toolathlon":
    adapter = ToolathlonAdapter()
    return adapter.load_dataset(ROOT / "datasets" / "toolathlon", limit=limit)
```

Add `run_eval("toolathlon")` call in `main()`.

- [ ] **Step 3: Run both scripts**

```bash
cd /Users/sohan/Documents/galea-org/atfd
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)

PYTHONPATH=src python3 baselines/langsmith/run_langsmith_eval.py
PYTHONPATH=src python3 baselines/braintrust/run_braintrust_eval.py
```

Record DR% and FPR% for both platforms on Toolathlon.

- [ ] **Step 4: Update Table 4 in paper**

Replace the `---†` cells for LangSmith and Braintrust Toolathlon rows (lines 652, 660) with actual results:

```latex
  % LangSmith Toolathlon row:
  & Toolathlon             & 100   & XX.X {\scriptsize [CI]} & XX.X {\scriptsize [CI]} \\
  % Braintrust Toolathlon row:
  & Toolathlon             & 100   & XX.X {\scriptsize [CI]} & XX.X {\scriptsize [CI]} \\
```

Also remove the `†` footnote about "re-evaluation pending" from the table footnotes (line 685).

- [ ] **Step 5: Update Detection Profiles table (Appendix)**

Update `Table~\ref{tab:profiles}` (lines 980-995) Platforms column for Toolathlon row — currently shows `---`, replace with actual DR/FPR.

- [ ] **Step 6: Compile and verify**

```bash
cd /Users/sohan/Documents/galea-org/atfd/paper && pdflatex atfd.tex && bibtex atfd && pdflatex atfd.tex && pdflatex atfd.tex
```

- [ ] **Step 7: Commit**

```bash
git add baselines/ results/raw/ paper/atfd.tex
git commit -m "feat: run LangSmith + Braintrust on Toolathlon, fill pending table cells (ISS-007)"
```

---

### Task 9: Update HANDOFF.md and Run Tests

**Files:**

- Modify: `HANDOFF.md`

- [ ] **Step 1: Run all tests**

```bash
cd /Users/sohan/Documents/galea-org/atfd
source .venv/bin/activate
python -m pytest tests/ -v
```

Expected: 92 tests pass.

- [ ] **Step 2: Final paper compile**

```bash
cd /Users/sohan/Documents/galea-org/atfd/paper && pdflatex atfd.tex && bibtex atfd && pdflatex atfd.tex && pdflatex atfd.tex
```

Expected: clean compile, no warnings.

- [ ] **Step 3: Update HANDOFF.md**

Update the handoff document with:

- Session number → 9

- Current state → v6 ready for submission

- Issue status table updated with ISS-042/043/044 addressed

- ISS-037/038 upgraded from partial

- New results (CI values) documented

- Session 10 prompt (if any remaining issues)

- [ ] **Step 4: Commit**

```bash
git add HANDOFF.md
git commit -m "docs: update handoff for session 9 — v6 reviewer response complete"
```

---

## Execution Order

Task 1 must run first (CI values needed for Tasks 2, 3, 7).
Tasks 2–6 are independent text edits (can run in parallel after Task 1).
Task 7 depends on Tasks 2–6 (changelog references all changes).
Task 8 (LangSmith/Braintrust) is independent — can run in parallel with Tasks 2–6.
Task 9 is final verification after everything else.

```
Task 1 (compute CI) → Tasks 2,3,4,5,6 + Task 8 (parallel) → Task 7 (changelog + appendix) → Task 9 (verify + handoff)
```

## Issue Resolution Map

| Issue                         | Required? | Resolved by   |
| ----------------------------- | --------- | ------------- |
| ISS-042 (κ attribution)       | Yes       | Tasks 1, 2, 3 |
| ISS-038 (full-sample κ)       | Yes       | Tasks 1, 3, 7 |
| ISS-037 (named limitation)    | Yes       | Task 4        |
| ISS-010 (human IAA)           | Yes       | Task 5        |
| ISS-043 (Landis-Koch)         | Yes       | Task 6        |
| ISS-007 (platform Toolathlon) | Partial   | Task 8        |
| ISS-044 (QDR qualifier)       | Suggested | Task 2        |
| R1 label leakage Q            | Suggested | Task 3        |
