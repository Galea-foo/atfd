# ATFD v5 — Handoff (2026-05-20, Session 8)

## What This Project Is

ATFD (Agent Trajectory Failure Detection) — **research benchmark for evaluating agent monitoring tools**, not agents themselves.

**Author:** Saisohan Shingade, sshingade@ucsd.edu, UC San Diego

## Current State

**Paper:** 19 pages (body 8pp, appendix ~9pp, references ~2pp), LaTeX, compiles clean at `paper/atfd.tex`. Targeting NeurIPS. **Ready for v5 submission.**

**Code:** Full Python package at `src/atfd/` with **92 passing tests**.

**Data:** 2,577-trajectory corpus across 7 sources. IAA v4 complete (48/50 trajectories, 3 frontier annotators).

## What Changed in Session 8

### All 6 Required Reviewer Changes (text fixes)
- **ISS-036**: Removed "validates taxonomy reproducibility" overclaim from abstract. Now reports binary + outcome + category κ accurately.
- **ISS-037**: Added IAA non-independence disclosure in limitations (Claude dual role, author-designed trajectories, same taxonomy).
- **ISS-038**: Disclosed conditioned subsample for Fleiss' κ=0.557 (144/150 unanimous-fail, excluding 6 max-disagreement cases).
- **ISS-039**: Applied CLI qualification to McNemar consistently (abstract + §9.4 now say "Claude Code CLI vs Codex CLI").
- **ISS-040**: Disclosed IAA sample composition in appendix (20 τ-bench, 15 synthetic, 10 SWE-bench, 5 Toolathlon; 25 fail, 15 pass, 10 degraded).
- **ISS-041**: Qualified domain difficulty ordering as DR-only with FPR caveat in §9.2 and §9.6.
- Added author changelog for v5.

### IAA v4 — Category κ Improvement (COMPLETE)
Root cause analysis found 3 problems in v3:
1. Gemini 3.1 Flash Lite returned "unknown" on 77% of category classifications
2. GPT-5 labeled 68% of non-pass as "action" (massive bias)
3. Category prompt gave only 4K chars context with no examples or disambiguation

Built `scripts/run_llm_iaa_v4.py` with fixes:
- **Gemini 2.5 Flash** replaces 3.1 Flash Lite (thinking model — required multi-part response parsing)
- **Single-turn structured prompt** with CoT reasoning, 4 few-shot examples, 5 category disambiguation rules
- **Full 15K trajectory context** (was 4K for categories)
- **JSON output format** with reasoning field
- **Per-annotator mode** (`--only <key>`) with resume support for Gemini free tier quota (20 req/day)
- **Strengthened process/action rule**: "count events — 20+ without attempting solution = process, not action"

### Final 3-Rater IAA v4 Results

| Measure | v3 | v4 | Interpretation |
|---------|-----|-----|---------------|
| Binary κ | -0.058 saved / 0.751 reported | **0.769** | substantial |
| Outcome κ | 0.055 saved / 0.713 reported | **0.764** | substantial |
| Category κ | **-0.058** | **0.608** | moderate |
| "unknown" categories | 77% | **0%** | — |

n=48 (2 trajectories excluded — Gemini safety filter blocked response on items 8, 17).

Annotators: Claude Sonnet 4, GPT-5 (Codex CLI), Gemini 2.5 Flash

Per-annotator category distributions (non-pass):
- Claude: process(11), action(5), communication(4), quality(4), safety(1), infrastructure(1)
- GPT-5: process(12), action(8), quality(5), communication(4)
- Gemini: process(11), action(9), quality(5), communication(5), safety(1)

Pairwise category agreement (n=25 all-non-pass):
- Claude vs GPT-5: 68%
- Claude vs Gemini: 68%
- GPT-5 vs Gemini: 80%

## Issue Status

| Issue | Status | What Remains |
|-------|--------|-------------|
| ISS-001 | **addressed** | IAA proxy κ=0.769 binary, κ=0.608 category |
| ISS-002 | **addressed** | Real-domain CA = 0.093; circularity disclosed |
| ISS-007 | **partial** | Llama n=100 ✓; LangSmith/Braintrust pending |
| ISS-010 | **addressed** | Category κ=0.608 (moderate); human study = future work |
| ISS-036 | **addressed** | Abstract overclaim removed |
| ISS-037 | **addressed** | IAA non-independence disclosed |
| ISS-038 | **addressed** | Conditioned subsample disclosed |
| ISS-039 | **addressed** | McNemar CLI qualification applied |
| ISS-040 | **addressed** | IAA sample composition disclosed |
| ISS-041 | **addressed** | Domain difficulty ordering qualified |
| ISS-003–006, 009, 011–035 | addressed/partial | — |
| ISS-029 | disputed | — |

## Results Matrix (DR% / FPR%)

| System | Synthetic (150) | Retail (100) | Airline (100) | SWE-bench (100) | ATBench (200) | Toolathlon (100) |
|--------|:-:|:-:|:-:|:-:|:-:|:-:|
| Naive Heuristic | 14 / — | 25 / 18 | 41 / 4 | **100 / 0** | 0 / 0 | **79 / 0** |
| LangSmith (4-rule) | 22 / — | 0 / 0 | 64 / 33 | 100 / 100 | 0 / 0 | —† |
| Braintrust (4-rule) | 22 / — | 92 / 71 | 64 / 33 | 100 / 100 | 0 / 0 | —† |
| Llama 4 Scout | **100** / — | 14 / 12 | 10 / 28 | 100 / 100 | 70 / — | 7 / 7 |
| GPT-5 (Codex CLI) | 99 / — | **86 / 30** | **91 / 52** | 100 / 50 | — | — |
| Claude Sonnet 4 | **100** / — | 77 / 9 | 67 / 10 | 96 / **0** | **100** / N/A | **96 / 46** |

†pending platform re-eval

## Key Scripts

```bash
source .venv/bin/activate
python -m pytest tests/ -v                    # 92 tests
cd paper && pdflatex atfd.tex && bibtex atfd && pdflatex atfd.tex && pdflatex atfd.tex

python scripts/compute_all_metrics.py         # DR/FPR for all result dirs
python scripts/compute_real_domain_ca.py       # real-domain CA on τ-bench
python scripts/compute_mcnemar_verify.py       # McNemar verification
python scripts/generate_heatmap.py             # regenerate heatmap + cost scatter

# IAA v4 (improved — use this, not v3)
export $(grep -v '^#' .env | xargs)
PYTHONPATH=src python3 scripts/run_llm_iaa_v4.py                     # all annotators
PYTHONPATH=src python3 scripts/run_llm_iaa_v4.py --only claude_sonnet  # single annotator
PYTHONPATH=src python3 scripts/run_llm_iaa_v4.py --only gpt5_codex
PYTHONPATH=src python3 scripts/run_llm_iaa_v4.py --only gemini_flash
```

## Environment

- `.env`: GROQ_API_KEY, GEMINI_API_KEY
- Claude CLI: `claude -p` (uses local auth)
- Codex CLI: `codex exec` (uses local auth)
- Python 3.13 venv at `.venv/`
- Gemini free tier: 20 req/day/model. Script handles with resume support.

## Session 9 Prompt

```
Read HANDOFF.md first. ATFD is a NeurIPS paper. Session 8 completed all
6 required reviewer changes + improved category κ from -0.058 to 0.608.
Paper is ready for v5 submission. Reviewer feedback for v5 should be at
/Users/sohan/Documents/sci-rev/paper-reviewer-v3/reviews/atfd/v5/

Task: Address v5 reviewer feedback.

Fallback priorities if no new feedback:
1. LangSmith/Braintrust n=100 (needs platform access)
2. Human annotation pilot (run scripts/run_annotation.py with 1 annotator on 10 trajectories)
3. Polish pass — tighten loose prose, verify cross-references
```
