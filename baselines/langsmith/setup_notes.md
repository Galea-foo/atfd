# LangSmith Baseline Setup

## Configuration
- **Account:** LangSmith Personal (free tier), sohanshingade@gmail.com
- **Setup time:** ~15 minutes (writing evaluator functions + debugging)
- **Number of eval rules:** 4
- **Lines of config code:** ~80 (evaluator functions only)
- **Total script lines:** 273 (including dataset upload + harness)

## Results
- **Detection Rate:** 22.0% (11/50 synthetic trajectories)
- **False Positive Rate:** N/A (all synthetic trajectories are failures)
- **Detected types:** tool_loop (6/10), excessive_events via event count (5/50)
- **Missed types:** hallucination (0/10), permission_escalation (0/5), data_leakage (0/5), infinite_delegation (0/5), context_overflow (0/5), planning_failure (0/10)

## Eval Rules Written

### Rule 1: Tool Error Detection
Checks if any `tool_result` event has `metadata.error=True`.
```python
def tool_error_evaluator(outputs, reference_outputs=None):
    events = outputs.get("events", [])
    errors = [e for e in events if e.get("type") == "tool_result" and e.get("metadata", {}).get("error")]
    return {"key": "tool_error", "score": 0 if errors else 1}
```

### Rule 2: Tool Loop Detection
Checks if any tool is called more than 5 times.
```python
def tool_loop_evaluator(outputs, reference_outputs=None):
    events = outputs.get("events", [])
    tool_counts = {}
    for e in events:
        if e.get("type") == "tool_call":
            name = e.get("metadata", {}).get("tool_name", e.get("content", "unknown"))
            tool_counts[name] = tool_counts.get(name, 0) + 1
    loops = {k: v for k, v in tool_counts.items() if v > 5}
    return {"key": "tool_loop", "score": 0 if loops else 1}
```

### Rule 3: Abnormal Termination Detection
Checks for infrastructure-level failures.
```python
def termination_evaluator(outputs, reference_outputs=None):
    events = outputs.get("events", [])
    has_error = any(e.get("type") == "tool_result" and e.get("metadata", {}).get("error") for e in events)
    return {"key": "abnormal_termination", "score": 0 if has_error else 1}
```

### Rule 4: Excessive Event Count
Flags trajectories with >20 events.
```python
def event_count_evaluator(outputs, reference_outputs=None):
    count = len(outputs.get("events", []))
    return {"key": "excessive_events", "score": 0 if count > 20 else 1}
```

## Key Observations
1. **LangSmith has no built-in trajectory failure detection.** Every evaluator must be written from scratch.
2. **Structural patterns are easy to write rules for** (loops, errors, event counts) but semantic failures (hallucination, planning, data leakage) require LLM-backed evaluators — which LangSmith supports but adds cost and complexity.
3. **The dataset upload API is straightforward** — `create_dataset` + `create_example` per trajectory.
4. **The `evaluate()` function is clean** — pass a predict function + evaluators, get results in the UI.
5. **Detection rate ceiling with rule-based evaluators is ~30-40%** for our failure taxonomy. Semantic failures require either LLM-backed evaluators or domain-specific heuristics that are hard to generalize.
