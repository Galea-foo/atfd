# Agent Trajectory Failure Detection (ATFD)

A benchmark for evaluating agent monitoring tools — not agents themselves.

**Paper:** [arXiv (pending)]() · **Leaderboard:** [atfd-benchmark.github.io]() · **License:** CC BY 4.0

---

## The Problem

Every existing agent benchmark evaluates *agents*. None evaluates the *tools that monitor agents*.

As agentic workflows move into production — processing real customer requests, executing financial transactions, modifying codebases — failures carry real consequences. Dozens of monitoring tools claim to detect and categorize these failures. But until now, no shared benchmark existed to measure which tools actually work, under what conditions, and at what cost.

ATFD fills this gap.

---

## What ATFD Measures

Given a complete agent trajectory (the full sequence of model calls, tool invocations, intermediate states, and final outputs), can your monitoring tool:

1. **Detect** whether the trajectory contains a failure?
2. **Classify** the failure into the correct category?
3. **Do so reliably** across diverse domains and failure types?
4. **At what cost** (dollars, latency, tokens, API calls)?

ATFD provides trajectories with known ground truth, a principled evaluation harness, and standardized metrics so results across tools are directly comparable.

---

## Key Features

- **7-category failure taxonomy** with 23 subcategories covering the full space of agent failures — including quality degradation, which existing benchmarks ignore
- **400+ trajectories** across 4 domains: retail, airline, telecom, and coding
- **3 data sources**: tau-bench (200), SWE-bench (150), hand-crafted synthetic (50)
- **Multi-source ground truth**: programmatic verifiers combined with 3 independent LLM judges, with majority-vote consensus and inter-annotator agreement measurement
- **8 evaluated systems** spanning rule-based heuristics, LLM judges, and commercial platforms
- **Cost-aware metrics**: every system reports dollar cost, latency, token usage, and API calls per trajectory
- **Statistical rigor**: all metrics include 95% confidence intervals via Wilson score (binary) and bootstrap (continuous); McNemar's test for pairwise significance

---

## Quick Start

```bash
# Install with all dependencies
pip install -e ".[all]"

# Download datasets (tau-bench and SWE-bench)
python datasets/tau_bench/download.py

# Run evaluation with the naive heuristic judge
atfd run --judge naive --dataset synthetic

# Run with an LLM judge (requires OPENAI_API_KEY or ANTHROPIC_API_KEY)
atfd run --judge gpt-4.1 --dataset tau-bench

# Analyze results and generate tables/figures
atfd analyze
```

---

## Metrics

All systems are evaluated on the following metrics across the full trajectory set:

| Metric | Description | Notes |
|--------|-------------|-------|
| **DR** | Detection Rate (Recall) | % of true failures correctly flagged |
| **QDR** | Quality Detection Rate | DR restricted to `quality` category trajectories |
| **FPR** | False Positive Rate | % of passing trajectories incorrectly flagged |
| **F1** | Harmonic mean of precision and recall | Balances DR and FPR |
| **Cat. Align.** | Category Alignment | % of detected failures assigned the correct subcategory |
| **Config Effort** | Setup complexity | Qualitative (low / medium / high) |
| **$/traj** | Dollar cost per trajectory | Median across the evaluation set |

All DR, QDR, FPR, and F1 values include 95% confidence intervals. Results are aggregated across tau-bench, SWE-bench, and synthetic splits and reported both overall and per-domain.

---

## Evaluated Systems

ATFD v2 evaluates eight systems representing the range of approaches in the current monitoring landscape:

| System | Type | Notes |
|--------|------|-------|
| **Naive Heuristic** | Rule-based | Regex + structural checks; no LLM calls; zero cost baseline |
| **GPT-4.1 Judge** | LLM judge | OpenAI GPT-4.1 with structured output prompt |
| **Claude Sonnet 4 Judge** | LLM judge | Anthropic Claude Sonnet 4 with structured output prompt |
| **Llama 4 Scout Judge** | LLM judge | Open-weight; lowest cost among LLM judges |
| **LangSmith** | Commercial platform | Evaluation suite with custom evaluator support |
| **Braintrust** | Commercial platform | Eval-as-code platform with scoring functions |
| **Galea Heuristic** | Commercial platform | Rule-based monitoring layer; zero marginal LLM cost |
| **Galea LLM-backed** | Commercial platform | Galea investigator agent with LLM-backed analysis |

Galea is one of eight evaluated systems. ATFD is a neutral benchmark; Galea, as the benchmark's creator, is evaluated under the same conditions as all other systems.

---

## Failure Taxonomy

ATFD uses a two-level taxonomy with 7 top-level categories and 23 subcategories:

### action — Wrong or missing tool invocations
| Subcategory | Description | Example |
|-------------|-------------|---------|
| `wrong_tool` | Called incorrect tool for the intended operation | `cancel_order` instead of `modify_order` |
| `wrong_args` | Correct tool invoked with incorrect arguments | Exchange item A→B instead of A→C |
| `missing_action` | Failed to call a required tool or perform a necessary action | Never confirmed the exchange |

### state — Incorrect environment state after execution
| Subcategory | Description | Example |
|-------------|-------------|---------|
| `wrong_state` | Database or environment left in an incorrect state | Order status wrong |
| `partial_state` | Only some required state changes were applied | Address changed, payment not |

### communication — Incorrect or incomplete information conveyed
| Subcategory | Description | Example |
|-------------|-------------|---------|
| `wrong_response` | Incorrect information included in the agent's response | Wrong order number quoted |
| `missing_info` | Required information was not communicated to the user | Didn't tell user the refund amount |
| `hallucination` | Agent fabricated facts not grounded in available data or context | Invented a policy that doesn't exist |

### quality — Technically complete but substandard output
| Subcategory | Description | Example |
|-------------|-------------|---------|
| `shallow_output` | Output lacks necessary depth or detail | Report covers 2 of 8 relevant risk factors |
| `suboptimal_approach` | Task completed via an inefficient path | 12 API calls when 3 would suffice |
| `poor_tone` | Content is correct but register is inappropriate | Rude response that technically resolves issue |
| `incomplete_analysis` | Analysis misses relevant factors | M&A diligence skips regulatory risk entirely |
| `low_confidence_output` | Output is excessively hedged, undermining its utility | "I think maybe the order might be..." |

### process — Reasoning or execution flow failures
| Subcategory | Description | Example |
|-------------|-------------|---------|
| `tool_loop` | Agent repeated identical tool calls unnecessarily | Same API called 8 times |
| `infinite_delegation` | Circular handoffs between agents with no progress | Agent A→B→A→B |
| `context_overflow` | Agent exceeded its context window and lost critical information | — |
| `planning_failure` | Agent executed an incoherent action sequence | Steps in wrong order |

### safety — Authorization and policy violations
| Subcategory | Description |
|-------------|-------------|
| `permission_escalation` | Agent accessed resources beyond its authorization scope |
| `data_leakage` | Agent exposed PII or sensitive data across context boundaries |
| `policy_violation` | Agent violated a stated operational policy or constraint |

### infrastructure — Hard system-level failures
| Subcategory | Description |
|-------------|-------------|
| `timeout` | Run exceeded the configured time limit before completing |
| `error` | A system or API error terminated the run prematurely |
| `max_steps` | Agent exceeded the maximum step limit without completing the task |

---

## Dataset

| Source | Trajectories | Domains | Failure Types |
|--------|-------------|---------|---------------|
| **tau-bench** | 200 | Retail, airline, telecom | action, state, communication |
| **SWE-bench** | 150 | Coding (GitHub issues) | action, process, infrastructure |
| **Synthetic** | 50 | All domains | All 23 subcategories; covers rare and quality failures underrepresented in naturalistic data |
| **Total** | 400 | 4 | 23 |

Tau-bench and SWE-bench trajectories are downloaded from their respective public repositories. Synthetic trajectories are hand-crafted and included directly in this repository under `datasets/synthetic/trajectories/`.

Ground truth is established via majority vote across:
1. A programmatic verifier (tau-bench pass/fail signal; SWE-bench patch evaluation)
2. GPT-4.1 annotator
3. Claude Sonnet 4 annotator
4. Llama 4 Scout annotator

Inter-annotator agreement (Fleiss' kappa) is reported in the paper.

---

## Submitting Results

To add your tool to the leaderboard:

**1. Run your tool against the ATFD evaluation set**

Your tool must output a JSON file conforming to the submission schema at `leaderboard/schema.json`. Each trajectory result must include:

```json
{
  "trajectory_id": "synth_hallucination_001",
  "has_failure": true,
  "findings": [
    {
      "severity": "error",
      "category": "communication.hallucination",
      "description": "Agent invented a return policy that does not exist"
    }
  ],
  "cost": {
    "dollar_cost": 0.0042,
    "latency_seconds": 1.23,
    "total_tokens": 1800,
    "api_calls": 1,
    "infrastructure": "openai-api"
  }
}
```

**2. Validate your submission**

```bash
python leaderboard/validate.py --submission your_results.json
```

**3. Open a pull request**

- Place your submission JSON in `results/submissions/<your-system-name>.json`
- Add a brief description of your system to `results/submissions/README.md`
- Open a PR against `main` — we will reproduce and verify results before merging

See `leaderboard/schema.json` for the full schema and `leaderboard/index.html` for the live leaderboard.

---

## Repository Structure

```
atfd/
├── src/atfd/                   # Python package
│   ├── schema.py               # Pydantic models: Trajectory, Finding, JudgeOutput, Cost
│   ├── taxonomy.py             # Failure taxonomy (7 categories, 23 subcategories)
│   ├── metrics.py              # DR, QDR, FPR, F1, Wilson CI, bootstrap CI, kappa
│   ├── consensus.py            # Multi-source ground truth and majority-vote pipeline
│   ├── harness.py              # Benchmark runner: load → judge → score → report
│   ├── cli.py                  # `atfd` CLI (run, analyze, download)
│   ├── ground_truth.py         # Ground truth labeling helpers
│   ├── adapters/               # Dataset adapters (tau-bench, SWE-bench, synthetic)
│   └── judges/                 # Judge implementations
│       ├── naive.py            # Rule-based heuristic (regex + structure)
│       ├── llm_judge.py        # LLM judge (OpenAI / Anthropic)
│       ├── langsmith.py        # LangSmith adapter
│       ├── braintrust.py       # Braintrust adapter
│       └── galea.py            # Galea heuristic + LLM-backed judge
├── datasets/
│   ├── tau_bench/              # tau-bench download script + trajectories
│   ├── swe_bench/              # SWE-bench download script + trajectories
│   └── synthetic/              # 50 hand-crafted trajectories (all failure types)
├── results/
│   ├── raw/                    # Raw judge output JSON files
│   ├── analysis/               # Analysis scripts: tables, figures, statistical tests
│   └── submissions/            # Community submissions
├── paper/
│   ├── atfd.tex                # Main LaTeX manuscript
│   ├── atfd.bib                # Bibliography (40 citations)
│   ├── figures/                # Generated plots
│   └── tables/                 # Generated LaTeX tables
├── leaderboard/
│   ├── index.html              # Static leaderboard page
│   ├── schema.json             # Submission JSON schema
│   └── validate.py             # Submission validator
├── wiki/
│   ├── landscape.md            # Tool landscape survey (13 tools)
│   ├── related_work.md         # Research bibliography (36 papers)
│   ├── failure_examples.md     # Annotated failure examples (23 examples)
│   └── design_decisions.md     # Benchmark design rationale
├── tests/                      # 61 unit and integration tests
├── baselines/                  # Baseline result reproduction scripts
├── pyproject.toml
├── LICENSE
└── README.md
```

---

## Development

```bash
# Install in editable mode with all extras
pip install -e ".[all]"

# Run the full test suite
pytest

# Run with coverage
pytest --cov=atfd --cov-report=term-missing

# Run a specific judge against a specific dataset
atfd run --judge naive --dataset synthetic
atfd run --judge gpt-4.1 --dataset tau-bench
atfd run --judge claude-sonnet-4 --dataset swe-bench

# Generate results tables and figures (writes to paper/tables/ and paper/figures/)
atfd analyze
```

**LLM judges** require API keys:
- OpenAI judges: `OPENAI_API_KEY`
- Anthropic judges: `ANTHROPIC_API_KEY`
- LangSmith: `LANGSMITH_API_KEY` — see `src/atfd/judges/langsmith/` for setup
- Braintrust: `BRAINTRUST_API_KEY` — see `src/atfd/judges/braintrust/` for setup

---

## Citation

If you use ATFD in your research, please cite:

```bibtex
@article{shingade2026atfd,
  title={Agent Trajectory Failure Detection: A Benchmark for Evaluating Agent Monitoring Tools},
  author={Shingade, Sohan},
  year={2026},
  url={https://github.com/Galea-foo/atfd}
}
```

---

## License

This benchmark and all associated data are released under the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/). See [LICENSE](LICENSE) for the full text.
