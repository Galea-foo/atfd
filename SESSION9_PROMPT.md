# Session 9 Prompt — ATFD v5 Reviewer Response

## Context

Read HANDOFF.md first. ATFD is a NeurIPS paper (agent monitoring benchmark). Session 8 addressed all 6 required reviewer changes from v4 feedback + improved category κ:

- **ISS-036–041**: All 6 text fixes applied (abstract overclaim, IAA disclosures, McNemar framing, sample composition, domain ordering)
- **Category κ**: Improved from -0.058 to **0.608** (moderate) with structured prompts, few-shot examples, disambiguation rules, Gemini 2.5 Flash
- **Binary κ**: 0.769 (substantial), **Outcome κ**: 0.764 (substantial)
- Author changelog added for v5

Paper compiles clean. Body = 8 pages. 92 tests pass.

## Task

Address new reviewer feedback. The reviewer response will be provided at session start.

### If no new feedback, priorities are:

1. **LangSmith/Braintrust n=100** — run with platform access if available
2. **Human annotation pilot** — run `scripts/run_annotation.py` with 1 annotator on 10 trajectories to estimate human κ
3. **Polish pass** — tighten any remaining loose prose, verify all cross-references

### How to address typical reviewer feedback types:

- **"Numbers changed, update X"** → Run `python scripts/compute_all_metrics.py`, update table, recompile
- **"Need more statistical tests"** → McNemar in `src/atfd/metrics.py`, bootstrap CIs available
- **"Overclaim in §X"** → Qualify language, add CIs, add "initial" or "preliminary"
- **"Missing related work"** → Check `wiki/related_work.md` for 36+ annotated papers
- **"Page limit"** → Body must stay ≤8pp. Compress or move content to appendix
- **"Expand on Y"** → Add to appendix (unlimited), reference from body

## Known Constraints

- Gemini free tier: 20 req/day/model. IAA v4 script has resume support (`--only gemini_flash`)
- LangSmith/Braintrust: need platform account + credentials for n=100 re-eval
- Paper body must stay ≤8 pages
- Claude CLI and Codex CLI needed for IAA (frontier model annotators)

## Key Files

```
paper/atfd.tex                          # the paper
results/iaa_v4/summary.json             # IAA v4 κ values
results/iaa_v4/{claude,gpt5,gemini}.json # per-annotator labels
results/annotations/sample_manifest.json # 50-trajectory IAA sample
scripts/run_llm_iaa_v4.py              # IAA v4 (improved prompts, per-annotator mode)
scripts/run_llm_iaa_v3.py              # IAA v3 (kept for reference)
scripts/compute_all_metrics.py          # DR/FPR computation
scripts/compute_real_domain_ca.py       # real-domain CA
scripts/generate_heatmap.py             # heatmap + cost scatter
docs/superpowers/plans/2026-05-15-atfd-v5-kappa-and-reviewer-fixes.md  # session 8 plan
```
