# ATFD v6 — Handoff (2026-05-20, Session 9)

## What This Project Is

ATFD (Agent Trajectory Failure Detection) — **research benchmark for evaluating agent monitoring tools**, not agents themselves.

**Author:** Saisohan Shingade, sshingade@ucsd.edu, UC San Diego

## Current State

**Paper:** 20 pages (body ~9pp, appendix ~9pp, references ~2pp), LaTeX, compiles clean at `paper/atfd.tex`. Targeting NeurIPS. **v6 ready for submission.**

**Code:** Full Python package at `src/atfd/` with **92 passing tests**.

**Data:** 2,577-trajectory corpus across 7 sources. IAA v4 complete (48/50 trajectories, 3 frontier annotators).

**Review status:** v5 received **Major Revision** (first non-Reject in 5 rounds). R1+R3 upgraded; R2 maintained Reject but called it "close to acceptance." v6 addresses all 6 required changes + 3 suggested changes.

## What Changed in Session 9

### All 6 Required Changes from v5 Decision Letter

- **ISS-042 (PRIMARY)**: Added n=25 denominator and 95% bootstrap CI [0.406, 0.781] for category κ=0.608 in abstract, §7, and Appendix E. Acknowledged three-factor attribution confound (prompt engineering, model upgrade, sample restriction). Disclosed that disambiguation rules were developed *after* examining v3 disagreement patterns — framed κ=0.608 as "achievable annotation consistency under a structured protocol, not validation of taxonomy's natural discriminability."
- **ISS-038**: Reported full-sample κ=0.644 (n=48, pass as category, 95% CI [0.510, 0.763]) alongside conditioned κ=0.608 (n=25).
- **ISS-037**: Elevated IAA non-independence from bullet item to named limitation paragraph with three explicit axes and honest scoping as "cross-model consistency check."
- **ISS-010**: Added "Absence of human IAA" as named limitation paragraph with MAST κ=0.88 comparison and explicit distinction between LLM-proxy and human agreement.
- **ISS-043**: Corrected Landis-Koch characterization — AgentProp-Bench κ=0.432 is "moderate," not "poor-to-fair." ATFD's κ=0.320 falls in adjacent "fair" band.
- **ISS-044**: Qualified QDR=20.6% in abstract as "on the 34-trajectory synthetic degraded set."

### Additional Changes
- Changed "structured prompts" → "structured annotation protocols" in abstract to avoid conflating prompt engineering with taxonomy validation.
- **ISS-007**: Completed LangSmith and Braintrust Toolathlon evaluation (pending for 5 versions). DR=98.6%, FPR=96–100%. High FPR driven by event-count threshold (>20) firing on long-horizon traces.

### New Statistical Results

| Measure | κ | 95% CI | n |
|---------|---|--------|---|
| Category (non-pass) | 0.608 | [0.406, 0.781] | 25 |
| Full-sample (pass as category) | 0.644 | [0.510, 0.763] | 48 |

### Platform Toolathlon Results (new)

| Platform | DR% | FPR% |
|----------|-----|------|
| LangSmith (4-rule) | 98.6 | 100.0 |
| Braintrust (4-rule) | 98.6 | 96.4 |

## Issue Status

| Issue | Status | What Remains |
|-------|--------|-------------|
| ISS-001 | **partial** | IAA proxy κ=0.769 binary, κ=0.608 category; LLM-only |
| ISS-002 | **partial** | Circularity disclosed; structural issue persists |
| ISS-007 | **addressed** | LangSmith/Braintrust Toolathlon complete |
| ISS-010 | **partial** | Named limitation; human IAA = future work |
| ISS-036 | **addressed** | Abstract overclaim removed (v5) |
| ISS-037 | **partial** | Named limitation paragraph; structural non-independence persists |
| ISS-038 | **addressed** | Full-sample κ=0.644 reported alongside conditioned κ=0.608 |
| ISS-039 | **addressed** | McNemar CLI qualification applied |
| ISS-040 | **addressed** | IAA sample composition disclosed |
| ISS-041 | **addressed** | Domain difficulty ordering qualified |
| ISS-042 | **addressed** | n=25, CI, 3-factor confound, label-leakage disclosure |
| ISS-043 | **addressed** | Landis-Koch corrected |
| ISS-044 | **addressed** | QDR qualified as synthetic-only |
| ISS-003–006, 009, 011–035 | addressed/partial | — |
| ISS-029 | disputed | — |

## Results Matrix (DR% / FPR%)

| System | Synthetic (150) | Retail (100) | Airline (100) | SWE-bench (100) | ATBench (200) | Toolathlon (100) |
|--------|:-:|:-:|:-:|:-:|:-:|:-:|
| Naive Heuristic | 14 / — | 25 / 18 | 41 / 4 | **100 / 0** | 0 / 0 | **79 / 0** |
| LangSmith (4-rule) | 22 / — | 0 / 0 | 64 / 33 | 100 / 100 | 0 / 0 | 99 / 100 |
| Braintrust (4-rule) | 22 / — | 92 / 71 | 64 / 33 | 100 / 100 | 0 / 0 | 99 / 96 |
| Llama 4 Scout | **100** / — | 14 / 12 | 10 / 28 | 100 / 100 | 70 / — | 7 / 7 |
| GPT-5 (Codex CLI) | 99 / — | **86 / 30** | **91 / 52** | 100 / 50 | — | — |
| Claude Sonnet 4 | **100** / — | 77 / 9 | 67 / 10 | 96 / **0** | **100** / N/A | **96 / 46** |

## Key Scripts

```bash
source .venv/bin/activate
python -m pytest tests/ -v                    # 92 tests
cd paper && pdflatex atfd.tex && bibtex atfd && pdflatex atfd.tex && pdflatex atfd.tex

python scripts/compute_all_metrics.py         # DR/FPR for all result dirs
python scripts/compute_real_domain_ca.py       # real-domain CA on τ-bench
python scripts/compute_mcnemar_verify.py       # McNemar verification
python scripts/generate_heatmap.py             # regenerate heatmap + cost scatter
python scripts/compute_kappa_ci.py             # bootstrap CI for IAA κ values

# IAA v4
export $(grep -v '^#' .env | xargs)
PYTHONPATH=src python3 scripts/run_llm_iaa_v4.py                     # all annotators
PYTHONPATH=src python3 scripts/run_llm_iaa_v4.py --only claude_sonnet
PYTHONPATH=src python3 scripts/run_llm_iaa_v4.py --only gpt5_codex
PYTHONPATH=src python3 scripts/run_llm_iaa_v4.py --only gemini_flash

# Platform baselines (with Toolathlon)
PYTHONPATH=src python3 baselines/langsmith/run_langsmith_eval.py
PYTHONPATH=src python3 baselines/braintrust/run_braintrust_eval.py
```

## Environment

- `.env`: GROQ_API_KEY, GEMINI_API_KEY, BRAINTRUST_API_KEY, LANGSMITH_API_KEY
- Claude CLI: `claude -p` (uses local auth)
- Codex CLI: `codex exec` (uses local auth)
- Python 3.13 venv at `.venv/`
- Gemini free tier: 20 req/day/model. Script handles with resume support.

## Session 10 Prompt

```
Read HANDOFF.md first. ATFD is a NeurIPS paper. Session 9 addressed all
6 required changes from v5 Major Revision decision + completed pending
LangSmith/Braintrust Toolathlon evaluation. Paper is v6, ready for
re-submission. Reviewer feedback for v6 should be at
/Users/sohan/Documents/sci-rev/paper-reviewer-v3/reviews/atfd/v6/

Task: Address v6 reviewer feedback.

Remaining structural issues (not fixable without new experiments):
- ISS-010: Human IAA — need external annotators (budget/collaborator)
- ISS-001/002: Circularity — disclosed, not eliminable
- ISS-037: Non-independence — disclosed as structural limitation

Fallback priorities if no new feedback:
1. Human annotation pilot (run scripts/run_annotation.py with 1 annotator on 10 trajectories)
2. NeurIPS formatting pass (body → exactly 8 pages)
3. Polish pass — tighten loose prose, verify cross-references
```
