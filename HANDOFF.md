# ATFD v5 — Handoff (2026-05-15, Session 8)

## What This Project Is

ATFD (Agent Trajectory Failure Detection) — **research benchmark for evaluating agent monitoring tools**, not agents themselves.

**Author:** Saisohan Shingade, sshingade@ucsd.edu, UC San Diego

## Current State

**Paper:** 19 pages (body 8pp, appendix ~9pp, references ~2pp), LaTeX, compiles clean at `paper/atfd.tex`. Targeting NeurIPS.

**Code:** Full Python package at `src/atfd/` with **92 passing tests**.

**Data:** 2,577-trajectory corpus across 7 sources. All Llama 4 Scout, Claude, GPT-5 cells at n=100 on τ-bench. IAA proxy complete with frontier models.

## What Changed in Session 7

### ISS-007: Scale n≥100
- Llama 4 Scout **retail** n=50→100: DR 25.0%→13.6%, FPR 13.2%→11.5%
- Llama 4 Scout **airline** n=20→100: DR 20.0%→9.5%, FPR 66.7%→27.6%
- Table 1 + heatmap updated
- LangSmith/Braintrust n=100 still pending (needs platform access)

### ISS-001/010: IAA Study
- Built full annotation infrastructure (sampling, guidelines, human annotation script, LLM proxy)
- Ran multiple rounds:
  - **v1**: Groq small models (Llama 4 Scout, Llama 3.3 70B, Qwen3 32B) → κ=0.429 binary. Llama 3.3 had massive fail-bias (41/50 fail)
  - **v2**: Improved prompt + few-shot + two-turn → κ went negative. Longer prompts overwhelmed small models
  - **v3 (final)**: Frontier models (Claude Sonnet 4 via `claude -p`, GPT-5 via `codex exec`, Gemini 3.1 Flash via API) with domain-specific calibration → **κ=0.751 binary (substantial), κ=0.713 outcome (substantial), κ=0.229 category (fair)**
- Key insight: frontier models needed for reliable annotation; small models have systematic biases
- Script: `scripts/run_llm_iaa_v3.py`, results: `results/iaa_v3/`
- Paper updated: abstract, §7, limitations, appendix (full table + per-annotator distributions)

### ISS-002: Real-domain CA
- Computed on τ-bench retail+airline (n=64 fail trajectories with programmatic GT)
- **Top-level CA = 0.093** (vs 0.545 synthetic) — confirms synthetic CA inflated
- GT dominated by `state.wrong_state` (58/64); Claude predicts richer category set
- Script: `scripts/compute_real_domain_ca.py`
- Paper updated: §9.3, F1/CA table, abstract, circularity disclosure, limitations, conclusion

### Paper Edits
- **Abstract**: real-domain CA (0.093), IAA κ=0.751
- **§7**: frontier-model IAA proxy (3 models, 3 κ values), circularity disclosure updated
- **§9.3**: real-domain CA paragraph
- **§9.6**: Llama 4 Scout numbers updated
- **Appendix**: IAA proxy results table with per-annotator distributions; real-domain CA rows in F1/CA table
- **Limitations**: items 3 (IAA κ=0.751), 6 (compressed), 7 (circularity partially addressed)
- **Conclusion**: compressed, includes real-domain CA + future work
- **Body = 8 pages exactly**, 92 tests pass, compiles clean

## Issue Status

| Issue | Status | What Remains |
|-------|--------|-------------|
| ISS-001 | **addressed** | LLM IAA proxy κ=0.751 binary; human study = future work |
| ISS-002 | **addressed** | Real-domain CA = 0.093 |
| ISS-007 | **mostly addressed** | Llama retail+airline n=100 ✓; LangSmith/Braintrust pending |
| ISS-010 | **addressed** | (=ISS-001) |
| ISS-003–006, 009, 011–035 | addressed | — |
| ISS-029 | disputed | — |

**Remaining open:** ISS-007 partial (LangSmith/Braintrust n=100 needs platform access)

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

## IAA Proxy Results (v3 — frontier models)

| Measure | κ | Interpretation |
|---------|---|----------------|
| Binary (pass vs non-pass) | 0.751 | substantial |
| Outcome (pass/degraded/fail) | 0.713 | substantial |
| Category (non-pass subset, n=25) | 0.229 | fair |

Annotators: Claude Sonnet 4, GPT-5, Gemini 3.1 Flash Lite

## Key Scripts

```bash
source .venv/bin/activate
python -m pytest tests/ -v                    # 92 tests
cd paper && pdflatex atfd.tex && bibtex atfd && pdflatex atfd.tex && pdflatex atfd.tex

python scripts/compute_all_metrics.py         # DR/FPR for all result dirs
python scripts/compute_real_domain_ca.py      # real-domain CA on τ-bench
python scripts/compute_mcnemar_verify.py      # McNemar verification
python scripts/generate_heatmap.py            # regenerate heatmap + cost scatter

# IAA proxy (frontier models — needs claude CLI, codex CLI, GEMINI_API_KEY)
export $(grep -v '^#' .env | xargs)
PYTHONPATH=src python3 scripts/run_llm_iaa_v3.py

# Run eval
PYTHONPATH=src python3 -c "import sys; sys.argv=['atfd','run','--judge','<judge>','--dataset','<dataset>','--limit','100','--output-dir','results/raw/<dir>']; from atfd.cli import main; main()"
```

## Environment

- `.env`: GROQ_API_KEY, GEMINI_API_KEY
- Claude CLI: `claude -p` (uses local auth)
- Codex CLI: `codex exec` (uses local auth)
- Python 3.13 venv at `.venv/`

## What Changed in Session 8

### All 6 Required Reviewer Changes (paper text fixes)
- **ISS-036**: Removed "validates taxonomy reproducibility" overclaim from abstract. Now reports binary κ + outcome κ + category κ accurately.
- **ISS-037**: Added IAA non-independence disclosure in limitations (Claude dual role, author-designed trajectories, same taxonomy).
- **ISS-038**: Disclosed conditioned subsample for Fleiss' κ=0.557 (144/150 unanimous-fail, excluding 6 max-disagreement cases).
- **ISS-039**: Applied CLI qualification to McNemar consistently (abstract + §9.4 now say "Claude Code CLI vs Codex CLI").
- **ISS-040**: Disclosed IAA sample composition in appendix (20 τ-bench, 15 synthetic, 10 SWE-bench, 5 Toolathlon; 25 fail, 15 pass, 10 degraded).
- **ISS-041**: Qualified domain difficulty ordering as DR-only with FPR caveat in §9.2 and §9.6.
- Added author changelog for v5.

### IAA v4 — Category κ Improvement (IN PROGRESS)
- Built `scripts/run_llm_iaa_v4.py` with improved prompts:
  - Gemini 2.5 Flash (replaces broken 3.1 Flash Lite — was 77% "unknown")
  - Single-turn structured prompt with CoT + 4 few-shot examples + 5 disambiguation rules
  - Full 15K trajectory context (was 4K for categories)
  - JSON output format with reasoning
  - Resume support for Gemini daily quota (20 req/day free tier)
- **Claude Sonnet 4**: 50/50 DONE
- **GPT-5 (Codex)**: 50/50 DONE
- **Gemini 2.5 Flash**: PENDING (daily quota exhausted, needs 3 runs of ~20/day)

### Preliminary 2-Rater Results (Claude + GPT-5)
| Measure | v3 | v4 (2-rater) | Δ |
|---------|-----|-------------|---|
| Binary κ | 0.491 | 0.919 | +0.428 |
| Outcome κ | 0.407 | 0.860 | +0.453 |
| Category κ | -0.058 | 0.284 | +0.342 |

Category κ dragged by 10/14 disagreements being process(Claude) vs action(GPT-5) on SWE-bench "explored but never fixed" pattern. Strengthened disambiguation rule for Gemini run.

## Session 9 Priorities

1. **Finish Gemini IAA** — run `PYTHONPATH=src python3 scripts/run_llm_iaa_v4.py --only gemini_flash` each day until 50/50. Script resumes automatically.
2. **Compute final 3-rater κ** — after Gemini completes. If category κ ≥ 0.5, proceed. If < 0.5, iterate (Task 3).
3. **Update paper with new κ values** — Task 5: update §7, abstract, appendix, limitations.
4. **Final verification** — Task 6: compile paper, run tests, check for stale values.
5. **LangSmith/Braintrust n=100** — if platform access available.

## How to Resume Gemini

```bash
cd /Users/sohan/Documents/galea-org/atfd
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
PYTHONPATH=src python3 scripts/run_llm_iaa_v4.py --only gemini_flash
```

Script auto-resumes. Expect ~20 trajectories per day. After 50/50, the script computes full κ.
