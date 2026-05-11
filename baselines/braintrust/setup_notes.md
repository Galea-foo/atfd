# Braintrust Baseline Setup

## Configuration
- **Account:** Braintrust Starter plan (free), Galea-Research org
- **Setup time:** ~15 minutes (writing scorer functions)
- **Number of scorers:** 4
- **Lines of config code:** ~60 (scorer functions only)

## Results
- **Synthetic:** DR=22.0%, FPR=N/A (all failures)
- **Retail:** DR=91.7%, FPR=71.1% — event count threshold fires on normal long conversations

## Scorers Written

### Scorer 1: Tool Error
```python
def tool_error_scorer(output, expected=None):
    events = output.get("events", [])
    errors = [e for e in events if e.get("type") == "tool_result" and e.get("metadata", {}).get("error")]
    return 0 if errors else 1
```

### Scorer 2: Tool Loop
```python
def tool_loop_scorer(output, expected=None):
    events = output.get("events", [])
    counts = {}
    for e in events:
        if e.get("type") == "tool_call":
            name = e.get("metadata", {}).get("tool_name", e.get("content", "unknown"))
            counts[name] = counts.get(name, 0) + 1
    return 0 if any(v > 5 for v in counts.values()) else 1
```

### Scorer 3: Abnormal Termination
```python
def termination_scorer(output, expected=None):
    events = output.get("events", [])
    has_error = any(e.get("type") == "tool_result" and e.get("metadata", {}).get("error") for e in events)
    return 0 if has_error else 1
```

### Scorer 4: Excessive Event Count
```python
def event_count_scorer(output, expected=None):
    return 0 if len(output.get("events", [])) > 20 else 1
```

## Key Observations
1. **Same rules → same synthetic detection (22%)** as LangSmith — proves the result is about the rules, not the platform
2. **Retail FPR of 71.1%** — the event count threshold (>20) triggers on normal tau-bench conversations. Demonstrates that rule thresholds need domain-specific calibration
3. **Braintrust SDK API changed** — `braintrust.Score(scorer=...)` no longer works in v0.3.x. Had to run evaluation locally instead of through the Braintrust Eval API. This is a real friction point for users
4. **No built-in failure detection** — every scorer must be hand-written, same as LangSmith
