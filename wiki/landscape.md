# Agent Monitoring Tool Landscape

*Last updated: May 2026. Research compiled for ATFD v2.*

## Key Insight for the ATFD Paper

None of the tools below automatically detect trajectory-level failures without user configuration. Every tool requires operators to (a) define what "failure" means via custom scorers/rules/evals, or (b) manually review traces. The sole partial exception is Galileo's Insights Engine (announced July 2025), which performs automatic root-cause clustering but still requires user-supplied evaluation rubrics to surface semantic failures. Galea's heuristic pass/degraded/fail approach is the only system that produces an unprompted verdict without pre-configuration. This gap — between passive trace storage and active failure detection — is precisely what ATFD measures.

---

## Comparison Matrix

| Tool | Open Source | Auto Failure Detection | Trajectory-Level? | API Available | Pricing Model |
|---|---|---|---|---|---|
| LangSmith | No | Partial (Insights Agent clusters) | No | Yes | Usage-based + seats |
| Langfuse | Yes (MIT core) | No | No | Yes (OpenAPI) | Free tier / Enterprise |
| Arize Phoenix | Yes (ELv2) | No | No | Yes | Free (OSS) / Enterprise |
| Braintrust | No | Partial (Loop agent) | No | Yes | Free tier / $249/mo Pro |
| DeepEval | Yes (Apache 2.0) | No (eval framework) | No | Via Confident AI | Free OSS / Confident AI paid |
| Patronus AI | No | Yes (Percival, 20+ modes) | Partial | Yes (pay-per-call) | $10–$20/1k API calls |
| Galileo | No | Yes (Insights Engine) | Partial | Yes | Free tier / $100/mo Pro |
| W&B Weave | No (Weave SDK is OSS) | No | No | Yes | Free credits + usage |
| Humanloop | No | No | No | Yes | **Shutting down Sept 2025** |
| Parea | No | No | No | Yes | Free tier |
| AgentOps | Yes (SDK) | No | No | Yes | Free / $40/mo Pro |
| PromptLayer | No | No | No | Yes | Free / $150/mo teams |
| Galea | No (closed beta) | Yes (heuristic investigator) | Yes | Yes (internal) | Early access |

---

## Tool Profiles

### LangSmith (LangChain)
**URL:** https://www.langchain.com/langsmith

**What it does:** LangSmith is the flagship observability platform for LangChain-based applications, but supports any LLM application via OpenTelemetry or native SDK. It captures full execution trees: every LLM call, tool invocation, retrieval step, and interstitial reasoning. The platform surfaces cost, latency, and token usage per run.

**Automatic failure detection:** LangSmith has an "Insights Agent" (released 2024–2025) that automatically clusters traces to reveal usage patterns and common failure modes. The embedded AI assistant "Polly" answers natural-language questions about traces (e.g., "Why did the agent enter this loop?"). However, neither feature detects failures without user-defined evaluation criteria — they surface patterns in traces but leave failure judgment to the operator. Alerts require manual rule configuration.

**Configuration required for evaluation:** Significant. Teams must author evaluators (Python functions or LLM-judge prompts) and attach them to datasets. Out-of-box detection is limited to hard crashes, timeouts, and empty outputs.

**Open source status:** Closed source SaaS. LangChain libraries are MIT-licensed, but LangSmith itself is proprietary.

**Pricing:**
- Developer: 1 seat, 5,000 base traces/month free
- Plus: $39/user/month, 10,000 traces included
- Extended trace retention: $5.00/1k traces (400-day) vs $2.50/1k (14-day)
- Enterprise: Contact sales

**API:** Full REST API and Python/TypeScript SDKs. Supports programmatic dataset management, evaluation runs, and trace queries.

**Gap for ATFD:** LangSmith requires operator-defined evaluators to detect semantic failures. A trajectory that silently returns wrong data passes through LangSmith without any automated verdict.

---

### Langfuse
**URL:** https://langfuse.com  
**GitHub:** https://github.com/langfuse/langfuse (MIT core, EE features separate)

**What it does:** Langfuse is one of the most widely adopted open-source LLM engineering platforms. It provides hierarchical trace capture (LLM calls, tool executions, retrievals, custom spans), prompt versioning, evaluation runs, human annotation queues, and a cost/latency dashboard. Integrates with OpenTelemetry, LangChain, OpenAI SDK, LiteLLM, and more.

**Automatic failure detection:** None out of the box. The dashboard shows quality, cost, and latency metrics as time-series, but "failure" is not defined by the platform. Teams must attach custom evaluation functions or LLM-judge prompts to runs. There are no built-in trajectory-level analyzers.

**Configuration required for evaluation:** Moderate. Evals require authoring scorer functions and attaching them to trace data. Langfuse provides a Python SDK for running evals programmatically, and a UI for human review.

**Open source status:** Core is MIT-licensed and self-hostable. Enterprise features (RBAC, SSO, audit logs) are in a separate EE folder with a proprietary license. Cloud offering available.

**Pricing:**
- Free: 50,000 observations/month, no credit card
- Cloud Pro: scales with usage
- Enterprise: from $2,499/month
- Self-hosted: free (MIT)

**API:** Comprehensive OpenAPI spec with Postman collection. Typed Python and TypeScript SDKs. Supports bulk trace export, programmatic eval runs, and dataset management. Frequently used to build bespoke LLMOps pipelines.

**Gap for ATFD:** No automatic failure detection. Langfuse is a trace storage and analytics substrate; failure judgment is entirely user-defined.

---

### Arize Phoenix
**URL:** https://phoenix.arize.com  
**GitHub:** https://github.com/Arize-ai/phoenix (ELv2 license, 9k+ stars)

**What it does:** Phoenix is an open-source AI observability platform built on OpenTelemetry/OpenInference standards. It supports tracing every step of agent workflows — prompts, tool calls, retrievals, outputs — with a focus on multi-agent and RAG systems. Visualizes agent action graphs, function call chains, and supports a wide range of frameworks (OpenAI Agents SDK, Claude Agent SDK, LangGraph, CrewAI, LlamaIndex, DSPy, Mastra, Vercel AI SDK).

**Automatic failure detection:** No automatic detection. Phoenix allows teams to attach LLM-based evaluators, code-based checks, or human labels to traces/spans, but does not perform unsolicited failure detection. The platform "flags when and where models fail" but only when user-defined evaluators are configured. Hallucination detection is supported via custom evaluators.

**Configuration required for evaluation:** Moderate to significant. Evals require authoring scorer functions, selecting models for LLM-judge eval, and configuring what to score. Phoenix Evals SDK provides pre-built templates (hallucination, relevance, Q&A) as starting points.

**Open source status:** ELv2 license — free to self-host with no feature limitations. Data stays entirely within user infrastructure. Arize also offers a hosted cloud version and an enterprise on-premise product (Arize AX).

**Pricing:**
- Self-hosted: Free, no feature gates, no license fees
- Cloud: Free tier available
- Enterprise (Arize AX): Contact sales

**API:** Python SDK with OpenTelemetry instrumentation. Supports programmatic trace export and evaluation runs.

**Gap for ATFD:** No automatic failure detection. Phoenix is a best-in-class trace store and visualization layer, but failure judgment requires user-configured evaluators.

---

### Braintrust
**URL:** https://www.braintrust.dev

**What it does:** Braintrust positions itself as the only platform that integrates evaluation directly into observability. It supports tracing production AI (every LLM call, tool invocation, span), scoring traces with customizable metrics, and tracking quality/cost/latency in real-time. Notable features: an AI agent named Loop that autonomously analyzes production logs, identifies failure patterns, and suggests optimizations.

**Automatic failure detection:** Partial. Loop analyzes production logs to identify failure patterns, but requires initial eval configuration (scorers, datasets) to know what to analyze. Alerts can be configured for quality degradation. The platform does not issue unsolicited failure verdicts on raw traces without user-defined scoring criteria.

**Configuration required for evaluation:** Moderate. Scorers must be defined by the team (LLM-judge or custom function). Braintrust offers a playground and pre-built scorer templates to reduce setup time.

**Open source status:** Closed source SaaS. SDKs (Python, TypeScript, Go, Ruby, C#, and more) are open source.

**Pricing:**
- Free: 1M spans, 10k scores, unlimited users
- Pro: $249/month, unlimited spans and scores
- Enterprise: Custom pricing, self-hosting option

**API:** Full REST API and multi-language SDKs. Supports programmatic experiment runs, trace queries, and scorer execution. MCP server available.

**Gap for ATFD:** Loop performs pattern detection, but "failure" detection requires pre-defined scorers. A novel failure type not covered by configured evals will not be surfaced automatically.

---

### DeepEval (Confident AI)
**URL:** https://deepeval.com  
**GitHub:** https://github.com/confident-ai/deepeval (Apache 2.0, 10k+ stars)

**What it does:** DeepEval is an open-source LLM evaluation framework, conceptually similar to pytest for LLMs. It provides 50+ plug-and-play metrics (hallucination, answer relevance, faithfulness, tool correctness, contextual recall, etc.) for testing AI applications in CI/CD pipelines and during development. It does not provide trace capture on its own — it is an evaluation layer that integrates with monitoring platforms like Langfuse or the companion Confident AI SaaS.

**Automatic failure detection:** No. DeepEval provides evaluation primitives; the developer configures which metrics to run and on which data. Confident AI (the commercial companion) provides production monitoring with alerts for quality drift, cost anomalies, and user sentiment shifts — but this requires integration setup and threshold configuration.

**Configuration required for evaluation:** Low to moderate for the framework itself (metrics are plug-and-play). Significant if integrating Confident AI for production monitoring, as teams must configure which metrics to track, set thresholds, and connect data pipelines.

**Open source status:** Apache 2.0, fully open source. Confident AI is a separate closed-source SaaS.

**Pricing:**
- DeepEval framework: Free (Apache 2.0)
- Confident AI: Paid (pricing not published, contact sales)

**API:** Python-first API. Integrates with LangSmith, Langfuse, Braintrust for trace-level evaluation. REST API via Confident AI.

**Gap for ATFD:** DeepEval is a metric library, not a monitoring tool. It requires explicit test authoring for every eval dimension. No automatic trajectory-level failure detection.

---

### Patronus AI
**URL:** https://www.patronus.ai

**What it does:** Patronus AI provides an end-to-end evaluation and monitoring platform for production LLM applications. It specializes in hallucination detection (flagship model: Lynx, which outperforms GPT-4o on RAG hallucination), safety checking, and agent failure detection. The platform includes Percival, an "intelligent AI agent debugger" that automatically detects 20+ failure modes in agentic traces.

**Automatic failure detection:** Yes — the most capable of the non-Galea tools for this. Percival detects agent planning mistakes, incorrect tool use, context misunderstanding, and other agentic failure modes automatically when given a trace. It also learns from user annotations to provide domain-specific evaluation. However, the detection is still oriented toward pre-defined failure mode categories rather than novel trajectory-level failures.

**Configuration required for evaluation:** Low to moderate. Percival works out of the box on agent traces; the hallucination detector (Lynx) requires minimal setup. Domain customization via annotation learning requires annotation investment.

**Open source status:** Closed source. Self-serve API and pay-per-call model.

**Pricing:**
- $5 in free credits to start
- Pay-as-you-go: $10/1,000 API calls (smaller evaluators), $20/1,000 (larger evaluators)
- Enterprise: Custom pricing, higher rate limits, custom models, webhooks

**API:** Yes — industry-first self-serve REST API for AI evaluation (launched Nov 2024). Also available on AWS Marketplace.

**Gap for ATFD:** Percival's 20+ failure mode categories cover substantial ground but are a fixed taxonomy. ATFD's 7-category, 23-subcategory taxonomy may surface failures Percival's categories miss. Critical gap: no domain-specific quality rubrics without annotation investment.

---

### Galileo
**URL:** https://galileo.ai

**What it does:** Galileo is an AI observability and evaluation platform powered by its Luna evaluation model suite. It targets RAG and agentic workflows with built-in guardrails, real-time safety monitoring, and custom metrics. In July 2025, Galileo announced a free "Agent Reliability Platform" specifically targeting multi-agent systems, featuring: a Graph Engine (visualizes decision paths and bottlenecks), an Insights Engine (automatic failure detection with root cause analysis), scalable agentic metrics, and real-time guardrails. Luna-2 models run at sub-200ms latency at ~$0.02/1M tokens.

**Automatic failure detection:** Yes (partial). The Insights Engine performs automatic failure detection and root cause analysis. However, it still operates within Galileo's evaluation framework — teams choose which metrics/evals to apply; the system then detects violations automatically at scale. Novel failure types outside configured evals are not detected.

**Configuration required for evaluation:** Moderate. 20+ out-of-box evals for RAG, agents, safety, and security. Custom evaluators can encode domain expertise. Luna-2 models can be distilled from user-defined evals for cost-effective production monitoring.

**Open source status:** Closed source.

**Pricing:**
- Free tier: Includes Agent Reliability Platform features
- Pro: $100/month
- Enterprise: Contact sales

**API:** Yes. REST API and Python SDK. Luna-2 models accessible via API.

**Gap for ATFD:** Galileo is the closest commercial tool to automatic failure detection, but the Insights Engine requires metric configuration. The platform cannot detect novel failure patterns without an eval to score them against.

---

### Weights & Biases Weave
**URL:** https://wandb.ai/site/weave  
**GitHub:** https://github.com/wandb/weave

**What it does:** W&B Weave is an observability and evaluation toolkit for AI applications, extending W&B's established ML experiment tracking to the LLM/agent domain. It automatically logs all inputs, outputs, code, and metadata using the `@weave.op` decorator, capturing costs, latency, and evaluation metrics without manual instrumentation of standard patterns. Supports tracing and monitoring, prompt experimentation (LLM Playground), and systematic evaluation with custom or pre-built scorers.

**Automatic failure detection:** No. Weave provides a unified substrate for tracing and evaluation but requires user-defined scorers to define what constitutes failure. No unsolicited failure verdicts.

**Configuration required for evaluation:** Moderate. Scorers must be authored. Pre-built scorers are available. W&B's ecosystem (sweeps, artifacts) integrates with Weave for more complex eval workflows.

**Open source status:** Weave SDK is open source. W&B platform is closed source SaaS with a self-hosted enterprise option.

**Pricing:**
- Free: Included credits
- Usage-based pricing beyond free tier
- Enterprise: Custom (self-hosted available)

**API:** Python and TypeScript SDKs. REST API via W&B. Full programmatic access to traces, evals, and experiments.

**Gap for ATFD:** No automatic failure detection. Weave is a premium trace storage and evaluation substrate for teams already in the W&B ecosystem.

---

### Humanloop
**URL:** https://humanloop.com  
**Status: SHUTTING DOWN September 8, 2025**

**What it did:** Humanloop was an LLM evals platform for enterprises, providing prompt management, observability, and evaluation. It offered real-time monitoring with configurable alerts and threshold-based notifications.

**Automatic failure detection:** No. User-configured alert thresholds required.

**Pricing (historical):** Free tier, Pro at $50/user/month, enterprise custom.

**Note for ATFD:** Humanloop is excluded from the benchmark evaluation suite because it is shutting down. It may appear in related work discussions as a historical data point on market consolidation.

---

### Parea AI
**URL:** https://www.parea.ai

**What it does:** Parea is a developer platform for debugging and monitoring LLM applications, integrating testing, evaluation, and observability. It provides code-level tracing, custom evaluation metrics (including a human-annotation bootstrapping method requiring as few as 20 samples), cost/latency/token tracking, and aggregated dashboards.

**Automatic failure detection:** No. Evaluation requires user-defined metrics. The human-annotation bootstrapping approach reduces annotation effort for custom evals.

**Configuration required for evaluation:** Low to moderate. Pre-built eval metrics available; custom metrics require some configuration.

**Open source status:** Closed source SaaS. Free Builder plan available.

**Pricing:**
- Free Builder plan (no credit card required)
- Paid tiers: See https://www.parea.ai/#pricing (not publicly listed)

**API:** Python SDK. REST API. Supports programmatic trace ingestion and eval execution.

**Gap for ATFD:** No automatic failure detection. Positioned as a lightweight alternative for smaller teams.

---

### AgentOps
**URL:** https://www.agentops.ai  
**GitHub:** https://github.com/AgentOps-AI/agentops

**What it does:** AgentOps is an open-source SDK and SaaS platform purpose-built for agent monitoring. Key differentiator: Session Replays — recording and replaying agent runs to inspect exactly what happened. Also features Time Travel Debugging (precise recall of individual agent run states), LLM cost tracking across 400+ LLMs, and multi-agent interaction tracing. Integrates with CrewAI, Agno, OpenAI Agents SDK, LangChain, AutoGen, AG2, CamelAI, LlamaIndex, Google ADK.

**Automatic failure detection:** No. AgentOps captures session data comprehensively but does not issue failure verdicts. Teams must review replays and traces manually, or configure custom alerts.

**Configuration required for evaluation:** Low for instrumentation (SDK wraps most frameworks automatically). Evaluation of failures requires manual review or external eval tooling.

**Open source status:** SDK is open source. SaaS dashboard is closed source.

**Pricing:**
- Basic: Free, up to 5,000 events/month
- Pro: $40/month, unlimited events and log retention
- Enterprise: Custom pricing, compliance, self-hosting, SLA

**API:** Python SDK. REST API. Supports programmatic session query and replay data export.

**Gap for ATFD:** No automatic failure detection. Session replays are valuable for manual debugging but cannot scale to systematic trajectory-level failure assessment.

---

### PromptLayer
**URL:** https://www.promptlayer.com

**What it does:** PromptLayer focuses on prompt management and versioning with LLM observability as a secondary capability. It automatically captures and versions every LLM call, provides cost/latency/token analytics, and supports A/B testing based on user segments. Positioned for non-technical team members (AI product managers, domain experts) as well as engineers.

**Automatic failure detection:** No. Monitoring is metrics-based (latency, token count, custom key-value pairs); there is no semantic failure detection. Alerts for threshold violations (e.g., latency > X ms) can be configured.

**Configuration required for evaluation:** Moderate for custom evals; the platform leans more toward prompt management than failure detection.

**Open source status:** Closed source SaaS.

**Pricing:**
- Free tier for individuals
- Teams: $150/month for 5 users
- Enterprise: Custom

**API:** REST API and Python SDK. Supports programmatic prompt retrieval, trace logging, and analytics export.

**Gap for ATFD:** PromptLayer is primarily a prompt management tool with observability features. No semantic failure detection.

---

### Galea
**URL:** https://galea.foo (early access)

**What it does:** Galea is the investigation layer for agent workflows. Unlike all other tools in this landscape, Galea is explicitly designed to detect failures — not to be a passive trace store. It sits above any agent orchestration runtime (Mercury, LangGraph, OpenAI Agents SDK, Claude Agent SDK, CrewAI, Temporal) and provides: (1) trace ingest via framework adapters/SDKs, (2) an investigator agent that walks each workflow with operators and flags concerns scoped to company-specific priority axes, (3) optimization recommendations (evals, retrieval, alerts, review requirements, guardrails), (4) monitoring against per-project baselines, and (5) signed audit export.

**Automatic failure detection:** Yes. The core value proposition is active failure detection without user-configured rules. The investigator agent uses a heuristic approach: it reads the trace, company context, and 10 priority axes (`correctness`, `audit`, `regulatory_compliance`, `cost`, `latency`, `throughput`, `tool_safety`, `memory_safety`, `privacy_phi`, `privacy_pii`) and produces a narrative + findings. It outputs a three-tier verdict (pass/degraded/fail) without requiring pre-configured evaluators.

**Configuration required for evaluation:** Low. Company context and priority axes are configured once; the investigator then applies them automatically to every incoming trace. No per-trajectory rule authoring required.

**Open source status:** Closed source. Early access / closed beta.

**Pricing:** Early access pricing not public. Enterprise focus.

**API:** Internal API. Framework adapters available for major runtimes. Trace event model is the core schema.

**Gap for ATFD:** Galea is one of the evaluated systems in the benchmark (not just a comparison tool). Its heuristic approach avoids the user-configuration requirement that disqualifies other tools from "automatic" failure detection — but heuristic verdicts may still miss or misclassify failure categories, which is exactly what ATFD measures.

---

## Summary of the Gap

The entire landscape can be divided into two buckets:

**Passive trace stores** (LangSmith, Langfuse, Arize Phoenix, W&B Weave, AgentOps, Parea, PromptLayer): Capture rich execution data but require the operator to define failure. A trajectory that silently returns the wrong answer passes through undetected.

**Active but configuration-gated evaluators** (Braintrust Loop, Galileo Insights Engine, Patronus Percival, DeepEval + Confident AI): Move toward automatic detection but are bounded by user-defined eval coverage. Novel failure modes outside configured evals are invisible.

**Galea**: The only tool with an explicit heuristic investigator that issues verdicts without pre-configuration.

ATFD's contribution is a systematic measurement of this gap: given the same set of trajectories with known ground-truth failure labels, how well does each tool (including tools in both buckets) detect failures — and at what cost?
