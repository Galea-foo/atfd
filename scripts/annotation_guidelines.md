# ATFD Annotation Guidelines

## 1. Task Description

You will review 50 agent trajectories sampled from four datasets (tau-bench, SWE-bench, synthetic, and Toolathlon). Each trajectory is a sequence of events representing an AI agent executing a task: receiving user messages, calling tools, receiving tool results, and producing assistant responses.

Your goal is to determine (a) whether the agent completed its task correctly and (b) if not, what category of failure occurred.

For each trajectory you will see:
- **Task description**: a short natural-language summary of what the agent was supposed to do.
- **Domain**: the vertical (retail, airline, coding, tool_use, finance, etc.).
- **Events**: a chronological list of events, each with a type (`user_message`, `assistant_message`, `tool_call`, `tool_result`, `system`), content, and metadata.

Read the full event sequence before labeling. Do not skip events.


## 2. Labels

### 2a. Outcome (required)

Assign exactly one outcome label:

| Label | Definition |
|-------|-----------|
| **pass** | The agent completed the task correctly. Actions, state changes, and communication are all appropriate. Minor stylistic issues do not count as failures. |
| **degraded** | The agent completed the task without a hard failure, but the quality of execution is noticeably substandard — shallow analysis, poor tone, unnecessary steps, or incomplete coverage. |
| **fail** | The agent made one or more mistakes that prevented correct task completion: wrong actions, incorrect state, misinformation, safety violations, or infrastructure crashes. |

**Decision boundary: degraded vs. fail.** If the user's core request was fulfilled but the *quality* of fulfillment is poor, label `degraded`. If the core request was **not** fulfilled or the agent made a factual/action error, label `fail`.

### 2b. Failure Category (required if outcome = fail)

If the outcome is `fail`, select one top-level category from the list below. Pick the **primary** cause of failure. If multiple categories apply, pick the one that is most directly responsible.

| # | Category | Description |
|---|----------|-------------|
| 1 | **action** | Wrong action executed or required action omitted |
| 2 | **state** | System/environment left in an incorrect or incomplete state |
| 3 | **communication** | Incorrect or missing information conveyed to the user |
| 4 | **quality** | Task technically completed but output is substandard (rare for `fail` — usually this maps to `degraded`) |
| 5 | **process** | Flawed reasoning or execution flow: loops, overflows, bad plans |
| 6 | **safety** | Unauthorized access, data exposure, or policy violations |
| 7 | **infrastructure** | Hard execution limits or system-level errors |

### 2c. Subcategory (optional, if outcome = fail)

If you can identify a more specific subcategory, select from:

- **action**: `wrong_tool`, `wrong_args`, `missing_action`
- **state**: `wrong_state`, `partial_state`
- **communication**: `wrong_response`, `missing_info`, `hallucination`
- **quality**: `shallow_output`, `suboptimal_approach`, `poor_tone`, `incomplete_analysis`, `low_confidence_output`
- **process**: `tool_loop`, `infinite_delegation`, `context_overflow`, `planning_failure`
- **safety**: `permission_escalation`, `data_leakage`, `policy_violation`, `prompt_injection`
- **infrastructure**: `timeout`, `error`, `max_steps`

Format subcategories as `category.subcategory` (e.g., `action.wrong_tool`).

### 2d. Quality Category (optional, if outcome = degraded)

If the outcome is `degraded`, optionally note which quality dimension(s) are affected:
`quality.shallow_output`, `quality.suboptimal_approach`, `quality.poor_tone`, `quality.incomplete_analysis`, `quality.low_confidence_output`.


## 3. Worked Examples

### Example A: Fail (action.wrong_tool)

**Domain:** retail
**Task:** Customer asks to change the shipping address on order #12345.

```
[0] system: You are a retail customer service agent. Tools: modify_order, cancel_order, get_order_details.
[1] user_message: Hi, I need to change my shipping address on order #12345.
[2] assistant_message: I'll help you with that. Let me cancel your order first.
[3] tool_call: cancel_order | {"order_id": "12345"}
[4] tool_result: Order #12345 has been cancelled.
[5] assistant_message: I've cancelled your order. You can place a new one with the correct address.
```

**Label:** `fail`
**Category:** `action`
**Subcategory:** `action.wrong_tool`
**Reasoning:** The customer asked for an address change, which requires `modify_order`. The agent used `cancel_order` instead, which is a destructive action the customer did not request. The order is now cancelled rather than modified.


### Example B: Degraded (quality.shallow_output)

**Domain:** finance
**Task:** Analyze the risk profile of a diversified investment portfolio.

```
[0] system: You are a financial analysis agent with access to portfolio data tools.
[1] user_message: Please analyze the risk profile of portfolio P-7892.
[2] tool_call: get_portfolio | {"id": "P-7892"}
[3] tool_result: Portfolio contains 60% equities, 30% bonds, 10% alternatives. Total value: $2.4M.
[4] assistant_message: Your portfolio has moderate market risk due to 60% equity allocation. The bond allocation provides some stability. Overall risk is moderate.
```

**Label:** `degraded`
**Quality category:** `quality.shallow_output`
**Reasoning:** The agent correctly retrieved portfolio data and provided a technically accurate response. However, the analysis only addresses market risk and ignores credit risk, liquidity risk, concentration risk, and interest rate risk. The task was completed but quality is substandard.


### Example C: Pass

**Domain:** airline
**Task:** Customer wants to check the status of flight UA-456.

```
[0] system: You are an airline customer service agent. Tools: get_flight_status, book_flight, cancel_booking.
[1] user_message: Can you check the status of my flight UA-456 departing tomorrow?
[2] tool_call: get_flight_status | {"flight_number": "UA-456", "date": "2026-01-15"}
[3] tool_result: Flight UA-456 on Jan 15: On time. Departs SFO 10:00 AM, arrives JFK 6:30 PM.
[4] assistant_message: Your flight UA-456 departing tomorrow (January 15) from SFO at 10:00 AM is currently on time. It is scheduled to arrive at JFK at 6:30 PM. Is there anything else I can help with?
```

**Label:** `pass`
**Reasoning:** The agent called the correct tool with the right arguments, received accurate information, and communicated it clearly and completely to the customer.


## 4. General Guidelines

- **Read all events** before assigning a label. The failure may only become apparent in later events.
- **Focus on the task objective.** Did the agent achieve what the user asked for?
- **Tool calls matter.** Check that the right tools were called with correct arguments.
- **Do not penalize style alone.** A terse but correct response is `pass`, not `degraded`. Reserve `degraded` for cases where quality meaningfully impacts utility.
- **When in doubt between pass and degraded**, lean toward `pass`. When in doubt between `degraded` and `fail`, consider whether the user's core need was met.
- **Infrastructure failures** (timeouts, errors, max_steps) are always `fail` regardless of partial progress.
- **For coding trajectories**, a resolved bug fix is `pass`. An unresolved or incorrectly resolved fix is `fail`.
