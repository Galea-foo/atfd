# ATFD v5 — Handoff (2026-05-12, Session 2)

## What This Project Is

ATFD (Agent Trajectory Failure Detection) is a **research benchmark for evaluating agent monitoring tools** — not agents themselves.

**Author:** Saisohan Shingade, sshingade@ucsd.edu, UC San Diego

## Current State

**Paper:** 22 pages, LaTeX, compiles clean at `paper/atfd.tex`. Under revision addressing brutal reviewer feedback.

**Code:** Full Python package at `src/atfd/` with **92 passing tests**.

**Data:** 2,577-trajectory corpus across 7 sources. N=150 synthetic evaluation complete for 4 judges. Toolathlon re-evaluated after adapter bug fix.

## Results Matrix (DR%)

| System | Synthetic (50) | Synthetic (150) | Retail (tau) | Airline (tau) | SWE-bench (100) | ATBench (200) | Toolathlon (100) |
|--------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Naive Heuristic | 14 | 6 | 25 | 41 | **100** | 0 | **79** |
| LangSmith (4-rule) | 22 | — | 0 | 64 | 100* | 0 | —† |
| Braintrust (4-rule) | 22 | — | 92* | 64 | 100* | 0 | —† |
| Llama 4 Scout | **100** | **100** | 25 | 20 | 100* | 70 | 7 |
| GPT-5 (Codex) | — | 98 | — | — | — | — | — |
| Claude Sonnet 4 | **100** | 99 | **100** | 40 | **100** | **100** | 96 |

*high FPR †pending platform re-eval after adapter fix

### N=150 Synthetic (all 4 LLM judges)

| System | DR (%) | QDR (%) | F1 | CA [95% CI] |
|--------|:-:|:-:|:-:|:-:|
| Naive Heuristic | 6.0 | 0.0 | 0.114 | 0.037 [0.000, 0.111] |
| Llama 4 Scout | 100.0 | 0.0 | 0.864 | 0.471 [0.334, 0.601] |
| GPT-5 (Codex) | 98.3 | 0.0 | 0.846 | 0.402 [0.271, 0.526] |
| Claude Sonnet 4 | 99.1 | **20.6** | 0.868 | **0.545** [0.416, 0.668] |

### Multi-Judge Consensus (Fleiss' κ)

- **Outcome-level κ = 0.320** (96% raw agreement; low κ due to prevalence paradox)
- **Category-level κ = 0.557** (moderate; 54.9% full 3-way agreement on failure type)
- 3 independent model families: Claude (Anthropic), Llama (Meta/Groq), GPT-5 (OpenAI/Codex)

### Corrected Toolathlon (after adapter bug fix)

| System | Old DR | New DR | Old FPR | New FPR |
|--------|:-:|:-:|:-:|:-:|
| Naive Heuristic | 0% | **79.2%** | 0% | 0% |
| Llama 4 Scout | 14% | 6.9% | 0% | 7.1% |
| Claude Sonnet 4 | 100% | 95.8% | 67% | 46.4% |

Bug: `messages` field was JSON string, adapter iterated characters → 0 events per trajectory. Fixed in `toolathlon.py`.

## What Changed in Session 2

### Code Changes
- `src/atfd/adapters/toolathlon.py` — Fixed JSON string parsing bug (all old Toolathlon results invalid)
- `src/atfd/judges/codex_headless.py` — NEW: Codex CLI headless judge (GPT-5 via `codex exec`)
- `src/atfd/cli.py` — Added `codex-headless` judge option
- `src/atfd/adapters/agentrx.py` — NEW: AgentRx adapter (session 1)
- `.gitignore` — Added `.env`

### Paper Changes (32 → 22 pages)
- **7 systems** (was 6): GPT-5 added via Codex CLI
- **6 new citations**: AgentPex, ToolGuard/Near-Miss, AgentFixer, WASP, Trajectory Guard, AgentProp-Bench
- **Fleiss' κ** reported: category-level 0.557 (moderate agreement across 3 model families)
- **McNemar's tests** executed: naive vs LLMs p<0.001
- **Bootstrap CIs** for CA added
- **Toolathlon corrected**: all numbers updated after adapter fix
- **Circularity disclosed** with 3-family mitigation
- **Funding statement** added ($12 Anthropic API)
- **Epistemic separation**: synthetic validates rubric clarity; real validates ecological validity
- **Platform thresholds** disclosed (>20 events, >5 tool calls, error flags)
- **Truncation stats**: only 8.6% of Toolathlon failures exceed 100 messages
- Removed: Planned Extensions section, empty confusion matrix, summary matrix table
- Compressed: Analysis (7→4 subsections), Conclusion, Related Work, Introduction

### Reviewer Issues Addressed (21 of 23)

| Issue | Severity | Status |
|-------|----------|--------|
| ISS-001 Ground truth unexecuted | FATAL | **Addressed** — κ computed, consensus executed on synthetic |
| ISS-002 Synthetic circularity | FATAL | **Mitigated** — 3-family κ=0.557 shows taxonomy discriminability |
| ISS-003 Trajectory Guard uncited | serious | **Fixed** |
| ISS-004 AgentProp-Bench uncited | serious | **Fixed** |
| ISS-005 GPT-4.1 absent | serious | **Fixed** — GPT-5 added (better than requested) |
| ISS-006 Platform predetermined | serious | **Addressed** — thresholds disclosed, acknowledged |
| ISS-007 n=20 + no McNemar | serious | **Partially addressed** — McNemar done; n=20 cells remain |
| ISS-008 Toolathlon truncation | serious | **Fixed** — 8.6% truncated + adapter bug found & fixed |
| ISS-009 "No benchmark" overclaim | serious | **Fixed** |
| ISS-010 No taxonomy IAA | serious | **Addressed** — κ=0.557 as LLM-judge proxy |
| ISS-011 Complementarity overdetermined | moderate | **Fixed** |
| ISS-012 Platform thresholds | moderate | **Fixed** |
| ISS-013 CA=0.489 misleading | moderate | **Fixed** |
| ISS-014 Paper too long | moderate | **Fixed** (32→22) |
| ISS-015 FPR inconsistency | moderate | **Fixed** |
| ISS-016 Llama 3.3 in matrix | moderate | **Fixed** |
| ISS-017 Claude COI | moderate | **Fixed** |
| ISS-018 Truncated name | minor | Already correct |
| ISS-019 Telecom exclusion | minor | **Fixed** |
| ISS-020 κ wording | minor | **Fixed** |
| ISS-021 Heatmap FPR | minor | **Fixed** |
| ISS-022 CA CIs absent | minor | **Fixed** |
| ISS-023 Contribution 4 | minor | **Fixed** |

### Remaining for Next Session

1. **Expand n=20 cells** — Claude/Llama/GPT-5 on retail+airline to n=100 (ISS-007 partial)
2. **Re-run LangSmith/Braintrust** on fixed Toolathlon (needs platform access)
3. **Regenerate heatmap figure** with corrected Toolathlon data
4. **Human annotation study** for true IAA (current κ is LLM-judge proxy)

## Commands

```bash
source .venv/bin/activate
python -m pytest tests/ -v                    # 92 tests
cd paper && pdflatex atfd.tex && bibtex atfd && pdflatex atfd.tex && pdflatex atfd.tex

# Run judges
PYTHONPATH=src python -c "
from atfd.adapters.synthetic import SyntheticAdapter
from atfd.judges.codex_headless import CodexHeadlessJudge  # GPT-5
from atfd.harness import run_benchmark, print_results
from pathlib import Path
trajs = SyntheticAdapter().load_dataset(Path('datasets/synthetic'))
results = run_benchmark(CodexHeadlessJudge(), trajs, Path('results/raw/test'))
print_results(results)
"

# Judges: naive, groq-llama4-scout, claude-headless, codex-headless
# GROQ_API_KEY in .env (gitignored)
```
