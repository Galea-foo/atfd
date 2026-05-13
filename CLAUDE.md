# CLAUDE.md — ATFD Benchmark

## What is this
ATFD (Agent Trajectory Failure Detection) is a **research benchmark for evaluating agent monitoring tools** — not agents themselves. It measures whether monitoring tools (heuristics, LLM judges, observability platforms, auto-detect systems) can detect failures in agent trajectories and categorize them.

**Key distinction from related work:** TRAIL benchmarks LLM trace analysis capability; TrajAD trains detector models; AgentRx diagnoses failures. ATFD uniquely evaluates *heterogeneous production monitoring tools* with cost and configuration effort as first-class metrics.

**Author:** Saisohan Shingade, sshingade@ucsd.edu

## Key commands
```bash
source .venv/bin/activate          # Python 3.13 venv
python -m pytest tests/ -v         # run all tests (92)
pip install -e ".[all]"            # install with all deps

# Compile paper
cd paper && pdflatex atfd.tex && bibtex atfd && pdflatex atfd.tex && pdflatex atfd.tex

# Run a judge against a dataset
PYTHONPATH=src python -c "
import sys; sys.argv=['atfd','run','--judge','naive','--dataset','synthetic','--output-dir','results/raw/test']
from atfd.cli import main; main()
"

# Available judges: naive, groq-llama4-scout, groq-llama-70b, claude-headless, galea
# Available datasets: tau-bench, swe-bench, synthetic (ATBench/Toolathlon/AgentRx need direct adapter use)

# Start Galea API (for galea judge)
cd /Users/sohan/Documents/galea-org/galea/apps/api
GALEA_DEV_NO_AUTH=1 /opt/homebrew/bin/python3.11 -m uvicorn app.main:app --port 8002
```

## Architecture
```
src/atfd/
├── schema.py         ← Pydantic models (Trajectory, Event, Finding, JudgeOutput, CostReport)
├── taxonomy.py       ← Failure taxonomy (7 categories, 24 subcategories)
├── metrics.py        ← DR, FPR, F1, CA, Wilson CI, bootstrap, McNemar, Fleiss' kappa
├── consensus.py      ← Multi-source ground truth voting
├── harness.py        ← Benchmark runner
├── cli.py            ← `atfd run/download/ablation`
├── ground_truth.py   ← Multi-model labeling pipeline
├── adapters/
│   ├── base.py           ← Abstract DatasetAdapter
│   ├── tau_bench.py      ← tau-bench (retail, airline, telecom)
│   ├── swe_bench.py      ← SWE-bench (OpenHands)
│   ├── synthetic.py      ← Hand-crafted synthetic trajectories
│   ├── atbench.py        ← ATBench safety trajectories
│   ├── toolathlon.py     ← Toolathlon long-horizon
│   └── agentrx.py        ← AgentRx diagnostic trajectories (Microsoft)
└── judges/
    ├── naive.py          ← Rule-based baseline
    ├── llm_judge.py      ← LLM judge (Groq, OpenRouter)
    ├── claude_headless.py ← Claude Sonnet 4 judge
    ├── galea.py          ← Galea heuristic (zero-config)
    ├── langsmith.py      ← LangSmith platform (4-rule config)
    └── braintrust.py     ← Braintrust platform (4-scorer config)
```

## Failure taxonomy (7 categories, 24 subcategories)
- **Action** (3): wrong_tool, wrong_args, missing_action
- **State** (2): wrong_state, partial_state
- **Communication** (3): wrong_response, missing_info, hallucination
- **Quality** (5): shallow_output, suboptimal_approach, poor_tone, incomplete_analysis, low_confidence_output
- **Process** (4): tool_loop, infinite_delegation, context_overflow, planning_failure
- **Safety** (4): permission_escalation, data_leakage, policy_violation, prompt_injection
- **Infrastructure** (3): timeout, error, max_steps

## Datasets
| Dataset | Source | N | Domain | Ground Truth |
|---------|--------|---|--------|-------------|
| tau-bench retail | Sierra Research | 456 | Customer service | State comparison |
| tau-bench airline | Sierra Research | 200 | Customer service | State comparison |
| tau-bench telecom | Sierra Research | 456 | Customer service | State comparison |
| SWE-bench | nebius/HuggingFace | 100 | Coding | Test suite |
| Synthetic | Hand-crafted | 150 | Mixed | By design |
| ATBench | AI45Research | 1,000 | Safety | Label field |
| Toolathlon | HKUST-NLP | 100 | Long-horizon tools | task_status |
| AgentRx | Microsoft Research | 115 | Multi-domain diagnostics | Step-level annotation |

## Evaluated systems
| System | Type | Config Effort |
|--------|------|---------------|
| Naive Heuristic | Rules | 0 |
| Galea Heuristic | Auto-detect | 0 |
| Llama 3.3 70B | LLM Judge (Groq free) | 0 |
| Llama 4 Scout | LLM Judge (Groq free) | 0 |
| Claude Sonnet 4 | LLM Judge (Anthropic API) | 0 |
| LangSmith (4-rule config) | Platform | 4 rules, ~15 min |
| Braintrust (4-scorer config) | Platform | 4 scorers, ~15 min |

## Rules
- This is a **research benchmark**, NOT a Galea product. Galea is one of many evaluated systems.
- All metrics must include 95% confidence intervals.
- Every judge adapter must report cost (dollar, latency, tokens, API calls).
- Tests required for all core modules.
- **No oracle leakage**: judges receive only trajectory + task description. Never ground truth, expected state, or labels.
- **Symmetric metrics**: DR and FPR must use the same severity threshold. Report both error-only and warning-or-error levels.
- **Don't overclaim**: say "initial evaluation" not "complete evaluation". Qualify small-N results as preliminary.
- LangSmith and Braintrust are evaluated as "4-rule configurations", not as platforms — their performance reflects rule coverage, not platform capability.

## Concurrent/related work (cite all of these)
- **TRAIL** (Deshpande et al., arXiv:2505.08638) — benchmarks LLM trace analysis capability (148 traces)
- **TrajAD** (Liu et al., arXiv:2602.06443) — trains anomaly detector on 60k trajectories
- **Silent Failures** (Pathak et al., arXiv:2511.04032) — ML classifiers on 4,275 multi-agent trajectories
- **AgentRx** (Barke et al., arXiv:2602.02475) — diagnostic framework, 115 failed trajectories, 3 domains
- **ATBench** (AI45Research) — trajectory-level safety benchmark with human-audited labels

## Paper status
- **File**: paper/atfd.tex (compiles with pdflatex + bibtex)
- **Current state**: under revision after reviewer feedback
- **Key issues being addressed**: dataset arithmetic, overclaims, symmetric FPR, quality degradation evaluation, expanded synthetic data

## Wiki
`wiki/` contains research notes:
- `related_work.md` — 36+ annotated papers
- `landscape.md` — monitoring tool landscape
- `failure_examples.md` — real-world incident catalog
- `design_decisions.md` — benchmark design rationale

Update wiki when discovering new papers, tools, or incidents.
