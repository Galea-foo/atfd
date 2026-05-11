# ATFD v2 — Handoff to Final Paper Session

## What This Project Is

ATFD (Agent Trajectory Failure Detection) is a **research benchmark for evaluating agent monitoring tools** — not agents themselves. Every existing benchmark (tau-bench, SWE-bench, etc.) evaluates whether agents complete tasks. ATFD evaluates whether **monitoring tools can detect when agents fail**.

This is novel. Nobody has benchmarked monitoring tools before.

## Current State

**Paper:** 30 pages, LaTeX, compiles clean at `paper/atfd.tex`. All results filled in — no placeholders.

**Code:** Full Python package at `src/atfd/` with 61 passing tests.

**Data:** 2,462 trajectories across 6 domains.

**Results:** Complete 7-system × 6-domain matrix with real experimental data.

## The Complete Results Matrix (DR%)

| System | Synthetic (50) | Retail (tau) | Airline (tau) | SWE-bench (100) | ATBench (200) | Toolathlon (100) |
|--------|:-:|:-:|:-:|:-:|:-:|:-:|
| Naive Heuristic | 14 | 25 | 41 | **100** | 0 | 0 |
| LangSmith (4 rules) | 22 | 0 | 64 | 100* | 0 | 0 |
| Braintrust (4 scorers) | 22 | 92* | 64 | 100* | 0 | 0 |
| Llama 4 Scout | **100** | 25 | 20 | 100* | 70 | 14 |
| Claude Sonnet 4 | **100** | **100** | 40 | **100** | **100** | **100*** |
| Galea Heuristic | 78 | **100** | **100** | 90 | 53 | 0 |

*high FPR (see paper for details)

Llama 3.3 70B: synthetic only (100%) — Groq free tier rate limited on all other domains.

## Key Findings

1. **No system dominates all cells** — the matrix reveals complementary detection profiles
2. **Claude Sonnet = best overall** — 100% DR on 4/6 domains, highest category alignment (0.489)
3. **Galea = best precision** — 100% DR on tau-bench with 0% FPR*, sub-100ms, zero config
4. **LLM judges collapse on real failures** — Llama: 100% synthetic → 20-25% retail/airline
5. **Rule platforms are bottlenecked by rules** — LangSmith and Braintrust with identical rules = identical 22% DR
6. **Domain difficulty spectrum** — SWE-bench (easy) → Synthetic → Retail → Airline → ATBench → Toolathlon (hardest)
7. **Galea FPR caveat** — 0% because it only emits warning severity, never error. DR counts warnings, FPR counts errors. Disclosed in paper.

## Datasets

| Dataset | Source | N | Domain | Agent Tested | Ground Truth |
|---------|--------|---|--------|-------------|-------------|
| tau-bench retail | Sierra Research | 456 | Customer service | GPT-4.1 | Reward labels |
| tau-bench airline | Sierra Research | 200 | Customer service | GPT-4.1 | Reward labels |
| tau-bench telecom | Sierra Research | 456 | Customer service | GPT-4.1 | Reward labels |
| SWE-bench | nebius/HuggingFace | 100 | Coding | Qwen3-Coder via OpenHands v0.54 | resolved flag |
| Synthetic | Hand-crafted | 50 | Mixed | N/A (constructed) | By design |
| ATBench | AI45Research | 200 (of 1,000) | Safety | N/A (constructed) | label field |
| Toolathlon | HKUST-NLP | 100 | Long-horizon tools | Claude 4 Sonnet | task_status.evaluation |

## Evaluated Systems

| System | Type | How it works | Config effort |
|--------|------|-------------|---------------|
| Naive Heuristic | Rules | Flags tool errors + loops (>5 calls) | 0 |
| LangSmith | Platform | 4 manual evaluator functions | 4 rules, ~80 LOC, ~15 min |
| Braintrust | Platform | 4 manual scorer functions | 4 scorers, ~60 LOC, ~15 min |
| Llama 3.3 70B | LLM Judge | Two-stage prompt via Groq free tier | 0 (prompt only) |
| Llama 4 Scout | LLM Judge | Two-stage prompt via Groq free tier | 0 (prompt only) |
| Claude Sonnet 4 | LLM Judge | Two-stage prompt via `claude -p` headless | 0 (prompt only) |
| Galea Heuristic | Auto-detect | Zero-config structural heuristics via Galea API | 0 |

## API Keys (env vars, not committed)

- `GROQ_API_KEY` — for Llama judges (free tier, 100k tokens/day limit)
- `OPENROUTER_API_KEY` — for free models (rate limited)
- `LANGSMITH_API_KEY` — for LangSmith dataset/eval API
- `BRAINTRUST_API_KEY` — for Braintrust
- Claude Sonnet uses `claude -p` (Claude Code headless) — no separate key needed
- Galea API runs locally on port 8002: `cd /Users/sohan/Documents/galea-org/galea/apps/api && GALEA_DEV_NO_AUTH=1 uvicorn app.main:app --port 8002`

## Repo Structure

```
atfd/
├── paper/
│   ├── atfd.tex          ← 30-page LaTeX paper (main artifact)
│   ├── atfd.bib          ← 43 citations
│   └── atfd.pdf          ← Compiled PDF
├── src/atfd/
│   ├── schema.py         ← Pydantic models
│   ├── taxonomy.py       ← 7 categories, 23 subcategories
│   ├── metrics.py        ← DR, FPR, F1, Wilson CI, bootstrap, McNemar, Fleiss' kappa
│   ├── consensus.py      ← Multi-source ground truth voting
│   ├── harness.py        ← Benchmark runner
│   ├── cli.py            ← `atfd run/download/ablation`
│   ├── ground_truth.py   ← Multi-model labeling pipeline
│   ├── adapters/         ← tau_bench, swe_bench, synthetic, atbench, toolathlon
│   └── judges/           ← naive, llm_judge, claude_headless, galea, langsmith, braintrust
├── datasets/synthetic/trajectories/  ← 50 hand-crafted JSONs
├── data/                 ← Downloaded datasets (gitignored)
│   ├── tau_bench/        ← symlink to datasets/tau_bench
│   ├── swe_bench/openhands/  ← 100 OpenHands trajectories
│   ├── atbench/test.json     ← 1,000 ATBench trajectories
│   └── toolathlon/           ← 100 Toolathlon trajectories
├── baselines/
│   ├── langsmith/        ← Eval script + setup notes
│   └── braintrust/       ← Eval script + setup notes
├── wiki/                 ← Research wiki (36 papers, 23 incidents, 13 tools)
├── leaderboard/          ← Static page + submission schema
├── results/analysis/     ← Figure generation, statistical tests
├── tests/                ← 61 tests
├── old/                  ← Archived v1 code
├── .venv/                ← Python 3.13 venv
└── docs/superpowers/     ← Design spec + implementation plan
```

## What the Next Session Should Do

### 1. Paper Polish
- Read the full paper end-to-end for coherence
- Fix any inconsistencies between sections (numbers, system counts, domain counts)
- Ensure abstract matches conclusion
- Check all table numbers match the text
- Fix duplicate section numbering if any
- Verify all 43 citations are used
- Remove line numbers (review mode → camera ready)

### 2. Figures
- Run `results/analysis/figures.py` to generate:
  - Cost-performance frontier (DR vs $/trajectory)
  - Category confusion matrix
  - Failure distribution by domain
  - Domain difficulty heatmap (the 7×6 matrix as a visual)
- Add figures to paper

### 3. Galea FPR Fix Decision
- Currently Galea's 0% FPR is a severity artifact (all findings are warnings, FPR only counts errors)
- Options: (a) report both warning-level and error-level FPR, (b) standardize DR and FPR to same threshold, (c) keep as-is with disclosure
- Paper currently discloses the artifact — decide if methodology should change

### 4. Missing Evaluations
- Telecom domain: only naive baseline run. Could add Galea + Claude.
- Llama 3.3 70B: only synthetic (rate limited). Try again or drop from paper.
- ATBench: expand from 200 to full 1,000 sample for Galea/Claude.

### 5. Ground Truth Consensus
- `src/atfd/ground_truth.py` exists but was never run
- Would improve paper rigor: run 3 LLM judges on all trajectories, compute Fleiss' kappa
- Requires API budget

### 6. Author Info
- Replace "Anonymous Authors" with real author info for arXiv
- Add affiliations, ORCID

### 7. arXiv Submission
- Final pdflatex compile
- Check arXiv formatting requirements
- Submit

## Commands

```bash
# Activate venv
source .venv/bin/activate

# Run tests
python -m pytest tests/ -v

# Compile paper
cd paper && pdflatex atfd.tex && bibtex atfd && pdflatex atfd.tex && pdflatex atfd.tex

# Run a system against a dataset
PYTHONPATH=src python -c "
import sys; sys.argv=['atfd','run','--judge','naive','--dataset','synthetic','--output-dir','results/raw/test']
from atfd.cli import main; main()
"

# Available judges: naive, groq-llama4-scout, groq-llama-70b, claude-headless, galea
# Available datasets: tau-bench, swe-bench, synthetic (ATBench/Toolathlon need direct adapter use)

# Start Galea API
cd /Users/sohan/Documents/galea-org/galea/apps/api
GALEA_DEV_NO_AUTH=1 /opt/homebrew/bin/python3.11 -m uvicorn app.main:app --port 8002
```

## CRITICAL: Competing Work — "First" Claim Needs Qualification

Our abstract says ATFD is the first benchmark for monitoring tools. **Three competing works exist:**

### 1. TRAIL (PatronusAI, May 2025)
- **Paper:** arXiv:2505.08638
- **What:** 148 annotated traces (GAIA + SWE-Bench), 841 errors, 20+ error taxonomy
- **What it benchmarks:** Whether LLMs can debug traces (model-as-judge capability)
- **Key result:** Best model (Gemini-2.5-Pro) scores 11% joint accuracy
- **How we differ:** TRAIL benchmarks *model capability at trace analysis*. ATFD benchmarks *monitoring tool effectiveness* — including heuristic tools, configured platforms (LangSmith, Braintrust), and auto-detect systems (Galea). We evaluate tools, not models.
- **Action:** Cite TRAIL as related work. Position ATFD as evaluating *tools* (heterogeneous systems) vs TRAIL evaluating *models* (LLMs-as-judges only). Our 7-system heterogeneous evaluation is novel. Also: we have 2,462 trajectories vs their 148.

### 2. TrajAD / TrajBench (Feb 2025)
- **Paper:** arXiv:2602.06443
- **What:** 60,000 trajectories via perturb-and-complete on AgentBank. Trains a specialized detector (TrajAD, 85% F1).
- **How we differ:** TrajAD trains a detector model. ATFD evaluates existing tools. We use real agent trajectories (tau-bench, SWE-bench), not synthetic perturbations. We include configuration effort as a metric.
- **Action:** Cite as related work. Position ATFD as tool-evaluation vs TrajAD's detector-training.

### 3. "Detecting Silent Failures in Multi-Agentic AI Trajectories" (Nov 2025)
- **Paper:** arXiv:2511.04032
- **What:** 4,275 labeled multi-agent trajectories. XGBoost/SVDD reach 96-98% accuracy.
- **How we differ:** They train ML classifiers. We evaluate production monitoring tools.
- **Action:** Cite as related work.

### Revised claim for paper:
Instead of "first benchmark for evaluating agent monitoring tools," say:
> "the first benchmark that evaluates **heterogeneous monitoring systems** — spanning naive heuristics, configured observability platforms, LLM judges, and zero-config auto-detection tools — on a unified dataset with cost-aware metrics and configuration effort measurement."

The novelty is: (a) heterogeneous tool evaluation (not just LLMs), (b) configuration effort as metric, (c) real production tool comparison (LangSmith, Braintrust, Galea), (d) multi-domain multi-source dataset.

## Recent Agent Failure Incidents (Add to Motivation)

These are newer than what's in the paper:

- **Claude Code hijacking (Sep 2025):** Chinese state-sponsored group hijacked Claude Code instances for autonomous cyber espionage against ~30 defense/energy targets
- **Mexican government breach (Dec 2025-Feb 2026):** Single attacker used Claude Code + GPT-4.1 to breach 9 agencies, stealing 195M+ records
- **PocketOS database deletion:** Autonomous agent deleted production database, 30-hour outage
- **88% of enterprises** running AI agents reported security incidents in past year (2026 survey)

## New Observability Tools (Update Landscape)

Since our wiki was written:
- **Maxim AI** — end-to-end simulation + eval + observability, OTel support
- **ClawTrace** (Epsilla) — purpose-built for OpenClaw agents
- **New Relic Agentic AI Monitoring** — multi-agent focus
- **Datadog MCP tracing** — mid-2025
- **Langfuse** — went full MIT open-source
- **OpenTelemetry** — published AI agent observability standards (Feb 2026)

## Git State

- 41 commits on main
- Ahead of origin/main by 41 commits (not pushed)
- No uncommitted changes
- Branch: main
