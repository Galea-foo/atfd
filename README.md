# Agent Trajectory Failure Detection (ATFD)

A benchmark for evaluating agent monitoring tools — not agents themselves.

**Paper:** [arXiv (pending)]() · **Results:** [Leaderboard](#leaderboard)

## The problem

Every agent benchmark (tau-bench, SWE-bench, AgentBench) evaluates how well *agents* complete tasks. No benchmark evaluates how well *the tools that monitor agents* detect failures.

ATFD fills this gap. Given a complete agent trajectory, can your monitoring tool automatically detect that something went wrong?

## Task

**Input:** A complete agent trajectory — messages, tool calls, tool results, termination reason.

**Output:** Findings — did the trajectory fail? What type of failure? Which agent/tool is responsible?

**Ground truth:** tau-bench's reward labels (pass/fail) and reward breakdown (wrong action, wrong state, missing information).

## Metrics

| Metric | Description | Direction |
|--------|-------------|-----------|
| Detection Rate | % of failed trajectories flagged | ↑ higher is better |
| False Positive Rate | % of successful trajectories incorrectly flagged as errors | ↓ lower is better |
| Category Alignment | % of failure types correctly identified | ↑ higher is better |
| Config Effort | Number of eval rules / scorers user must write | ↓ lower is better |

## Leaderboard

| Tool | Detection Rate | FP Rate | Category Alignment | Config Effort | 
|------|---------------|---------|-------------------|---------------|
| **Galea** (heuristic) | **94.4%** | **0.0%** | **79.0%** | **0 rules** |

*Submit your results via PR — see [Submitting Results](#submitting-results).*

## Dataset

150 pre-recorded GPT-4.1 agent trajectories from [tau-bench](https://github.com/sierra-research/tau2-bench) (Sierra Research):

- **Retail** (100 trajectories): product exchanges, order cancellations, address modifications
- **Airline** (50 trajectories): reservation changes, cancellations, certificate issuance

Failure rate: 24% (36/150 trajectories have reward < 1.0).

## Quick Start

```bash
# Download tau-bench trajectory data
python download_data.py

# Run your tool against the trajectories, then evaluate
# Example with Galea:
python run_benchmark.py --domain retail --limit 100 --api-url http://localhost:8002
python run_benchmark.py --domain airline --limit 50 --api-url http://localhost:8002
```

## Reproducing Galea Results

```bash
# Clone Galea and start the API
git clone https://github.com/Galea-foo/Galea
cd Galea/apps/api
GALEA_DEV_NO_AUTH=1 uvicorn app.main:app --port 8002 &

# Run benchmark
cd ../../..
git clone https://github.com/Galea-foo/atfd
cd atfd
python download_data.py
python run_benchmark.py --domain retail --limit 100 --api-url http://localhost:8002
python run_benchmark.py --domain airline --limit 50 --api-url http://localhost:8002
```

## Submitting Results

1. Run your monitoring tool against the same 150 trajectories
2. Create a JSON file:

```json
{
  "tool_name": "Your Tool",
  "version": "1.0.0",
  "config_effort": 0,
  "results": {
    "retail": {
      "n": 100,
      "detection_rate": 0.909,
      "false_positive_rate": 0.0,
      "category_alignment": 0.762
    },
    "airline": {
      "n": 50,
      "detection_rate": 1.0,
      "false_positive_rate": 0.0,
      "category_alignment": 0.85
    }
  },
  "methodology": "How the tool was configured (if at all)",
  "reproduction_url": "Link to code"
}
```

3. Open a PR adding your submission to `submissions/`

## Files

```
atfd/
├── README.md              ← This file
├── converter.py           ← tau-bench SimulationRun → normalized trace events
├── run_benchmark.py       ← Benchmark runner + scoring
├── download_data.py       ← Downloads tau-bench trajectory data
├── pyproject.toml         ← Python dependencies
├── paper/
│   ├── atfd.tex           ← LaTeX source
│   ├── atfd.pdf           ← Compiled paper
│   └── galea-submission.json
└── submissions/
    └── galea.json
```

## Citation

```bibtex
@article{shingade2026atfd,
  title={Agent Trajectory Failure Detection: A Benchmark for Evaluating Agent Monitoring Tools},
  author={Shingade, Sohan},
  year={2026},
  url={https://github.com/Galea-foo/atfd}
}
```

## License

CC BY 4.0
