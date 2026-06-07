<p align="center">
  <h1 align="center">ATFD</h1>
  <p align="center">
    <strong>Agent Trajectory Failure Detection</strong><br>
    A benchmark for evaluating agent monitoring tools — not agents themselves.
  </p>
  <p align="center">
    <a href="https://creativecommons.org/licenses/by/4.0/"><img src="https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg" alt="License"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-≥3.9-blue.svg" alt="Python"></a>
    <a href="#evaluated-systems"><img src="https://img.shields.io/badge/systems_evaluated-7-green.svg" alt="Systems"></a>
    <a href="#dataset"><img src="https://img.shields.io/badge/trajectories-2%2C577-orange.svg" alt="Trajectories"></a>
  </p>
</p>

---

## Why ATFD?

Every existing agent benchmark evaluates *agents*. None evaluates the **tools that monitor agents**.

As agentic workflows move into production — processing customer requests, executing transactions, modifying codebases — failures carry real consequences. Monitoring tools claim to detect and categorize these failures, but no shared benchmark existed to measure which tools actually work, under what conditions, and at what cost.

ATFD fills this gap. Given a complete agent trajectory (the full sequence of model calls, tool invocations, intermediate states, and final outputs), ATFD measures whether your monitoring tool can:

1. **Detect** whether the trajectory contains a failure
2. **Classify** the failure into the correct category
3. **Do so reliably** across diverse domains and failure types
4. **At what cost** — dollars, latency, tokens, API calls

## Key Results

> **DR%** = Detection Rate (recall — % of true failures caught) · **FPR%** = False Positive Rate (% of passing trajectories incorrectly flagged) · **CA** = Category Alignment (% of detected failures assigned the correct subcategory) · **$/traj** = Median dollar cost per trajectory

| System | Type | DR% | FPR% | CA | $/traj |
|--------|------|----:|-----:|---:|-------:|
| **Claude Sonnet 4** | LLM judge | 67–96 | 0–10 | 0.545 | ~$0.05 |
| **GPT-5 (Codex)** | LLM judge | 86–100 | 30–52 | — | ~$0.08 |
| **Llama 4 Scout** | LLM judge | 40–75 | 5–15 | — | ~$0.001 |
| **Naive Heuristic** | Rule-based | 70–98 | 10–30 | — | $0 |
| **LangSmith** | Platform | 98.6 | 100.0 | — | — |
| **Braintrust** | Platform | 98.6 | 96.4 | — | — |

No single system dominates all cells. LLM judges detect semantic failures that heuristics miss; heuristics catch structural failures at zero cost; configured platforms are bottlenecked by their authored rules. Claude Sonnet 4 is the only system with non-zero quality degradation detection (QDR = 20.6%).

## Failure Taxonomy

ATFD defines a two-level taxonomy — **7 categories, 24 subcategories** — covering the full space of agent failures:

| Category | What it covers | Subcategories |
|----------|---------------|:---:|
| **action** | Wrong or missing tool invocations | 3 |
| **state** | Incorrect environment state after execution | 2 |
| **communication** | Incorrect or incomplete information conveyed | 3 |
| **quality** | Technically complete but substandard output | 5 |
| **process** | Reasoning or execution flow failures | 4 |
| **safety** | Authorization and policy violations | 3 |
| **infrastructure** | Hard system-level failures | 4 |

<details>
<summary>Full subcategory breakdown</summary>

### action
| Subcategory | Example |
|-------------|---------|
| `wrong_tool` | `cancel_order` instead of `modify_order` |
| `wrong_args` | Exchange item A→B instead of A→C |
| `missing_action` | Never confirmed the exchange |

### state
| Subcategory | Example |
|-------------|---------|
| `wrong_state` | Order status left incorrect |
| `partial_state` | Address changed, payment not |

### communication
| Subcategory | Example |
|-------------|---------|
| `wrong_response` | Wrong order number quoted |
| `missing_info` | Didn't tell user the refund amount |
| `hallucination` | Invented a policy that doesn't exist |

### quality
| Subcategory | Example |
|-------------|---------|
| `shallow_output` | Report covers 2 of 8 relevant factors |
| `suboptimal_approach` | 12 API calls when 3 would suffice |
| `poor_tone` | Rude response that technically resolves issue |
| `incomplete_analysis` | Diligence skips regulatory risk entirely |
| `low_confidence_output` | "I think maybe the order might be..." |

### process
| Subcategory | Example |
|-------------|---------|
| `tool_loop` | Same API called 8 times |
| `infinite_delegation` | Circular handoffs A→B→A→B |
| `context_overflow` | Lost critical info past context window |
| `planning_failure` | Steps executed in wrong order |

### safety
| Subcategory | |
|-------------|---|
| `permission_escalation` | Accessed resources beyond authorization |
| `data_leakage` | Exposed PII across context boundaries |
| `policy_violation` | Violated operational policy |

### infrastructure
| Subcategory | |
|-------------|---|
| `timeout` | Exceeded time limit |
| `error` | System/API error terminated run |
| `max_steps` | Exceeded step limit |
| `prompt_injection` | External input hijacked agent behavior |

</details>

## Dataset

| Source | Trajectories | Domains | Failure types |
|--------|:-----------:|---------|---------------|
| **τ-bench** | 200 | Retail, airline, telecom | action, state, communication |
| **SWE-bench** | 150 | Coding (GitHub issues) | action, process, infrastructure |
| **ATBench** | ~200 | Multi-domain | Varied |
| **Toolathlon** | ~100 | Tool-use tasks | action, process |
| **Synthetic** | 150 | All domains | All 24 subcategories |
| **AgentRx** | — | Clinical/diagnostic | safety, communication |
| **Total** | **2,577** | **6 domains** | **24 subcategories** |

Ground truth is established via majority vote across programmatic verifiers and 3 independent LLM annotators (GPT-5, Claude Sonnet 4, Gemini Flash). Inter-annotator agreement: binary κ = 0.769 (substantial), category κ = 0.608 (moderate, 95% CI [0.406, 0.781]).

## Quick Start

```bash
# Install
pip install -e ".[all]"

# Download datasets (τ-bench, SWE-bench)
python datasets/tau_bench/download.py

# Run with the naive heuristic (no API key needed)
atfd run --judge naive --dataset synthetic

# Run with an LLM judge
export OPENAI_API_KEY=sk-...
atfd run --judge gpt-4.1 --dataset tau-bench

# Run with Claude
export ANTHROPIC_API_KEY=sk-ant-...
atfd run --judge claude-sonnet-4 --dataset swe-bench

# Generate tables and figures
atfd analyze
```

## Metrics

| Metric | Description |
|--------|-------------|
| **DR** | Detection Rate (recall) — % of true failures correctly flagged |
| **QDR** | Quality Detection Rate — DR restricted to `quality` category |
| **FPR** | False Positive Rate — % of passing trajectories incorrectly flagged |
| **F1** | Harmonic mean of precision and recall |
| **CA** | Category Alignment — % of detected failures assigned correct subcategory |
| **$/traj** | Median dollar cost per trajectory evaluated |

All binary metrics include 95% Wilson confidence intervals. Category metrics use bootstrap CIs. Pairwise comparisons use McNemar's test.

## Evaluated Systems

| System | Type | Notes |
|--------|------|-------|
| Naive Heuristic | Rule-based | Regex + structural checks; zero cost |
| GPT-5 (Codex CLI) | LLM judge | Highest DR on τ-bench, high FPR |
| Claude Sonnet 4 | LLM judge | Best category alignment, lowest FPR among LLM judges |
| Llama 4 Scout | LLM judge | Open-weight; lowest cost |
| LangSmith | Platform | 4-rule evaluator configuration |
| Braintrust | Platform | 4-rule scoring configuration |
| Galea | Platform | Heuristic + LLM-backed investigator modes |

## Submitting Your Tool

To add your monitoring tool to the benchmark:

**1. Run against the evaluation set** — output JSON conforming to [`leaderboard/schema.json`](leaderboard/schema.json):

```json
{
  "trajectory_id": "synth_hallucination_001",
  "has_failure": true,
  "findings": [{
    "severity": "error",
    "category": "communication.hallucination",
    "description": "Agent invented a return policy that does not exist"
  }],
  "cost": {
    "dollar_cost": 0.0042,
    "latency_seconds": 1.23,
    "total_tokens": 1800,
    "api_calls": 1
  }
}
```

**2. Validate:** `python leaderboard/validate.py --submission your_results.json`

**3. Open a PR** with your results in `results/submissions/<your-system>.json`

## Repository Structure

```
atfd/
├── src/atfd/               # Core Python package
│   ├── schema.py            #   Pydantic models (Trajectory, Finding, Cost)
│   ├── taxonomy.py          #   Failure taxonomy (7 categories, 24 subcategories)
│   ├── metrics.py           #   DR, FPR, F1, Wilson CI, bootstrap CI, kappa
│   ├── consensus.py         #   Multi-source ground truth pipeline
│   ├── harness.py           #   Benchmark runner
│   ├── cli.py               #   `atfd` CLI
│   ├── adapters/            #   Dataset adapters (τ-bench, SWE-bench, synthetic)
│   └── judges/              #   Judge implementations
│       ├── naive.py         #     Rule-based heuristic
│       ├── llm_judge.py     #     LLM judges (OpenAI / Anthropic)
│       ├── langsmith.py     #     LangSmith adapter
│       ├── braintrust.py    #     Braintrust adapter
│       └── galea.py         #     Galea adapter
├── datasets/
│   ├── tau_bench/           # τ-bench download + trajectories
│   ├── swe_bench/           # SWE-bench download + trajectories
│   └── synthetic/           # 150 hand-crafted trajectories
├── results/
│   ├── analysis/            # Analysis scripts (tables, figures, stats)
│   ├── iaa_v4/              # Inter-annotator agreement data
│   └── submissions/         # Community submissions
├── paper/                   # LaTeX manuscript (NeurIPS format)
├── baselines/               # Platform baseline reproduction scripts
├── leaderboard/             # Submission schema + validator
├── wiki/                    # Landscape survey, related work, design decisions
└── tests/                   # 92 unit and integration tests
```

## Development

```bash
pip install -e ".[all]"
pytest
pytest --cov=atfd --cov-report=term-missing
```

## Citation

```bibtex
@article{shingade2026atfd,
  title   = {Agent Trajectory Failure Detection: A Benchmark for
             Evaluating Agent Monitoring Tools},
  author  = {Shingade, Saisohan},
  year    = {2026},
  url     = {https://github.com/Galea-foo/atfd}
}
```

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — free to share and adapt with attribution.
