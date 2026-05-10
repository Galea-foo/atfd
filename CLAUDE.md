# CLAUDE.md — ATFD Benchmark

## What is this
ATFD (Agent Trajectory Failure Detection) is a benchmark for evaluating agent monitoring tools.
It measures whether tools can detect failures in agent trajectories and categorize them.

## Key commands
- `pip install -e ".[all]"` — install with all deps
- `pytest` — run tests
- `atfd download` — download datasets
- `atfd run --judge naive --dataset tau-bench` — run a judge against a dataset
- `atfd analyze` — generate results tables and figures

## Architecture
- `src/atfd/schema.py` — Pydantic models for trajectories, findings, costs
- `src/atfd/taxonomy.py` — Failure taxonomy (7 categories, 23 subcategories)
- `src/atfd/metrics.py` — Detection rate, FPR, F1, category alignment, CIs, bootstrap
- `src/atfd/consensus.py` — Multi-source ground truth consensus
- `src/atfd/adapters/` — Dataset converters (tau-bench, SWE-bench, synthetic)
- `src/atfd/judges/` — Evaluated systems (naive, LLM, LangSmith, Braintrust, Galea)
- `src/atfd/harness.py` — Benchmark runner
- `tests/` — Full test suite

## Rules
- This is a research benchmark, NOT a Galea product. Galea is one of 8 evaluated systems.
- All metrics must include 95% confidence intervals.
- Every judge adapter must report cost (dollar, latency, tokens, API calls).
- Tests required for all core modules before implementation proceeds.
