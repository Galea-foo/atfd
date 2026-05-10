# Design Decisions Log

*Rationale for key ATFD v2 benchmark design choices. Maintained alongside the implementation.*

---

## D1: Three-Tier Outcome (pass/degraded/fail) vs. Binary

**Decision:** ATFD uses a three-tier outcome — `pass`, `degraded`, and `fail` — rather than binary pass/fail.

**Alternatives considered:**
- **Binary (pass/fail):** Simple, well-understood, aligns with most existing benchmarks (SWE-bench, tau-bench pass^k, WebArena). Easy to interpret.
- **Continuous score (0.0–1.0):** Maximum granularity; better for threshold tuning. Used in G-Eval, AlpacaEval. Difficult to interpret without calibration; harder to establish ground truth via consensus.
- **Five-tier rubric:** More expressive; too fine-grained for reliable inter-annotator agreement on agent trajectories.

**Rationale:**
Binary outcomes misrepresent a large class of real failures. An agent that completes 80% of a task correctly but fails on one critical step is not the same as an agent that hallucinates completely or takes a destructive action. AgentBoard's NeurIPS 2024 paper demonstrates that fine-grained progress metrics reveal meaningful performance differences hidden by binary success rates. In enterprise deployment, the cost of a `degraded` outcome (partial task completion, quality below bar) is often closer to `pass` than to `fail` — but monitoring tools should still detect and flag it.

The three-tier system provides a natural mapping:
- `pass`: Task completed correctly within acceptable bounds
- `degraded`: Task technically completed but with quality, efficiency, or completeness issues that would require human review in production
- `fail`: Task failed, wrong action taken, critical error, or safety violation

Three tiers are sufficient for reliable human annotation (kappa > 0.7 is achievable; five or more tiers degrades reliability sharply). Continuous scores require calibration data that does not exist for novel agent failure types.

**Risks:**
- The boundary between `degraded` and `fail` is sometimes ambiguous (addressed by multi-source consensus in D2)
- Some tools report binary verdicts internally; mapping to three tiers requires calibration (addressed in the judge adapter interface, which requires tools to report confidence/severity alongside the verdict)

**Prior work:** AgentBoard (Ma NeurIPS 2024), tau-bench pass^k (Yao ICLR 2025), CLEAR framework (arXiv:2511.14136)

---

## D2: Multi-Source Consensus vs. Single Ground Truth

**Decision:** ATFD ground truth is established via consensus across multiple sources: (1) automated environment verification where available (tau-bench database state, SWE-bench test suites), (2) LLM-judge annotation with structured rubrics, and (3) human expert annotation for a held-out calibration set.

**Alternatives considered:**
- **Single automated verifier:** Clean and reproducible. Only available for benchmarks with deterministic ground truth (SWE-bench tests, tau-bench database state). Not applicable to quality, process, or safety failures.
- **Single LLM judge:** Scalable and fast. Subject to known biases (position, verbosity, self-enhancement; see Zheng NeurIPS 2023). A single judge's errors become the benchmark's errors.
- **Majority vote among multiple LLM judges:** Reduces individual judge bias. Still susceptible to correlated errors across judges from the same model family.
- **Pure human annotation:** Gold standard. Not scalable to 1,000+ trajectories at reasonable cost. Used for calibration subset only.

**Rationale:**
No single ground truth source is sufficient for the full failure space:
- Automated environment verification is the most reliable but only covers action and state failures in domains with checkable outcomes
- LLM judges are scalable but require structured rubrics to achieve reliable alignment (G-Eval methodology, Liu EMNLP 2023); multi-judge consensus mitigates individual bias
- Human annotation is ground truth but expensive; reserved for the calibration set used to measure judge calibration

The consensus approach mirrors how production monitoring should work: multiple signals (automated checks, LLM evaluation, human review) are stronger together than any single signal.

"Beyond Agreement" (arXiv:2508.00143) warns that high inter-annotator agreement does not imply correctness. ATFD addresses this by validating the consensus mechanism against the human expert calibration set, and by reporting inter-source agreement as a metric alongside detection performance.

**Risks:**
- Consensus may obscure legitimate disagreement (e.g., whether a `degraded` output is a significant quality failure depends on the domain)
- Correlated errors across LLM judges from the same model family inflate apparent consensus reliability
- Human annotation cost limits the calibration set to ~200 trajectories; extrapolation to the full 1,000-trajectory dataset introduces uncertainty

**Prior work:** Zheng NeurIPS 2023 (multi-judge consensus), G-Eval (structured rubrics), AgentBoard (progress metrics), "Counting on Consensus" (arXiv:2603.06865)

---

## D3: Domain-Specific Quality Rubrics vs. Generic

**Decision:** Quality evaluation uses domain-specific rubrics rather than a single generic quality rubric. Each domain in the benchmark (retail, airline, software development, M&A due diligence, healthcare, DevOps) has a rubric specifying required output elements, completeness criteria, tone standards, and any mandatory disclaimers or safety caveats.

**Alternatives considered:**
- **Generic quality rubric:** Single rubric covering fluency, coherence, relevance, completeness, safety. Simpler to implement; lower domain expertise requirement for rubric authors. Proven to miss domain-critical failures (see failure examples: M&A diligence agent skips regulatory risk; medical agent gives incorrect dosage).
- **No quality rubric (LLM free-form judgment):** Maximum flexibility; completely unreliable without structured prompting (G-Eval demonstrates this).
- **User-defined rubrics (require benchmark users to supply rubrics):** Shifts labor to benchmark users; defeats the purpose of a standard benchmark.

**Rationale:**
G-Eval (Liu EMNLP 2023) demonstrates that structured rubrics substantially improve LLM-judge alignment with human judgments. Generic rubrics fail because "completeness" means different things in different domains:
- A complete retail refund conversation must confirm the refund amount, timeline, and updated order status
- A complete M&A due diligence report must cover financial, regulatory, anti-trust, data privacy, and operational risk
- A complete medical recommendation must include dosage qualifications for patient weight, contraindications, and evidence grounding

Without domain-specific rubrics, monitoring tools pass outputs that domain experts would flag. ATFD's benchmark value comes partly from encoding this domain expertise in rubrics that tool providers cannot easily replicate.

Rubric development is a research contribution in itself. ATFD ships domain rubrics for the included domains as part of the benchmark artifact.

**Risks:**
- Rubric development is time-consuming and requires domain expertise; this is a bottleneck for adding new domains
- Rubrics may encode biases of their authors; inter-rater reliability testing on rubric-based scoring is required
- Tools optimized for ATFD's specific rubrics may overfit to benchmark performance without generalizing

**Prior work:** G-Eval (Liu EMNLP 2023), AlpacaEval LC (Dubois COLM 2024), domain-specific AI safety literature, Galileo's Luna-2 domain adaptation

---

## D4: Tool-Agnostic Benchmark vs. Galea-Specific

**Decision:** ATFD is explicitly tool-agnostic. It evaluates any system that implements the judge adapter interface (`JudgeAdapter` in `src/atfd/judges/`). Galea is one of eight evaluated systems, not the benchmark's purpose.

**Alternatives considered:**
- **Galea-specific benchmark:** Faster to implement; directly serves Galea's product development. Conflicts of interest are obvious and would undermine external credibility.
- **LangSmith-specific benchmark:** Same conflict-of-interest problem from the other direction.
- **Two-way benchmark (only Galea vs. one baseline):** Minimal external credibility; not publishable as a research contribution.

**Rationale:**
The benchmark's credibility depends on its neutrality. If ATFD were designed as a Galea evaluation tool:
- Academic and industry adoption would be zero (perceived conflict of interest)
- Competitors would design their own benchmarks to counter it
- The research contribution claim ("measuring the gap in agent failure detection") would be undermined

Tool-agnosticism is essential for the paper's contribution to be accepted. The benchmark must be usable by LangSmith, Langfuse, Patronus, Galileo, and any future tool. Galea's competitive advantage in the benchmark should come from its actual detection performance, not from benchmark design.

The `JudgeAdapter` interface (`src/atfd/judges/`) is the key implementation of this principle: every tool must implement the same interface, and every tool is evaluated on the same trajectories with the same metrics.

**CLAUDE.md rule:** "This is a research benchmark, NOT a Galea product. Galea is one of 8 evaluated systems."

**Risks:**
- Tool providers may decline to implement adapters if they view ATFD as adversarial
- The paper's authorship (from Galea organization) creates a perception of conflict of interest regardless of tool-agnosticism; mitigated by transparent methodology and open data release
- Galea's proprietary evaluation logic may not be fully exposable via the adapter interface

---

## D5: Multi-Dataset (tau-bench + SWE-bench + Synthetic) vs. Single Source

**Decision:** ATFD draws from three dataset sources: tau-bench (retail/airline conversational tasks), SWE-bench (software engineering tasks), and a synthetic dataset generated to cover failure categories underrepresented in the natural datasets.

**Alternatives considered:**
- **Single dataset (tau-bench only):** Simplest. tau-bench has the cleanest ground truth mechanism (database state verification). But it only covers conversational customer service tasks; process, safety, and infrastructure failures are underrepresented.
- **Single dataset (SWE-bench only):** Strong automated verification. But it only covers software engineering; communication and quality failures in other domains are absent.
- **Purely synthetic dataset:** Full control over failure type distribution; no real-world grounding. Synthetic failures may be unrepresentative of deployment failure modes.
- **Four or more datasets:** More comprehensive; diminishing returns and increasing maintenance burden.

**Rationale:**
Each source contributes distinct coverage:
- **tau-bench** provides real conversational trajectories with action and state ground truth (database verification). Strong coverage of action, state, and communication failures.
- **SWE-bench** provides coding trajectories with test-suite ground truth. Strong coverage of action, quality, and process failures in a technical domain.
- **Synthetic** fills gaps in safety, infrastructure, and edge cases (e.g., data_leakage, permission_escalation, context_overflow) that rarely appear in natural datasets at sufficient frequency for statistical reliability.

The three-source design mirrors the ATFD paper's core claim: the failure space is multi-dimensional and no single dataset covers it adequately. The benchmark's diversity is part of its contribution.

**Risks:**
- Dataset versioning: tau-bench has evolved through tau2 and tau3 with quality fixes; ATFD must track which version it uses and how fixes affect ground truth
- Synthetic data may be too clean (failures are more stereotyped than real failures); human review of synthetic trajectories is required before inclusion
- SWE-bench licensing: check OSS license compatibility for redistribution in the benchmark artifact

**Prior work:** tau-bench (Yao ICLR 2025), SWE-bench (Jimenez ICLR 2024), AgentBench (Liu ICLR 2024), AgentBoard (Ma NeurIPS 2024)

---

## D6: 7-Category Taxonomy Structure

**Decision:** ATFD uses a 7-category, 23-subcategory failure taxonomy: action (3), state (2), communication (3), quality (5), process (4), safety (3), infrastructure (3).

**Alternatives considered:**
- **4-category taxonomy (MAST-style):** System design, inter-agent misalignment, task verification, and coordination. Covers multi-agent failures well; misses single-agent quality and communication failures. MAST is the closest prior work (Cemri NeurIPS 2025).
- **OWASP Top 10 structure:** Security-focused; excellent for safety category but weak on quality, process, and state failures.
- **Microsoft taxonomy:** Industry-validated but not publicly detailed enough to serve as a research taxonomy.
- **5 dimensions (action, state, communication, process, safety):** Earlier draft; the quality and infrastructure categories were split out after reviewing real-world failures where the failure is neither an action error nor a process error but a quality judgment.

**Rationale:**
The 7-category structure was derived from bottom-up analysis of the real-world failure examples in `wiki/failure_examples.md` and cross-referenced with MAST, Microsoft's taxonomy, and OWASP Agentic AI:

- **action**: Covers the most common category of failures (wrong tool, wrong arguments, missing action) — well-supported by tau-bench and ToolLLM literature
- **state**: Required because action failures can be correct tools with wrong arguments that produce wrong state (distinct from wrong_tool)
- **communication**: Covers the most business-impactful failure mode (hallucination, wrong info, missing info) — well-documented in production incidents
- **quality**: Covers failures that are technically correct but below bar — not covered by action/state but representing a large fraction of enterprise AI complaints
- **process**: Covers trajectory-level failures (loops, overflows, bad planning) that require multi-step trace analysis — not detectable from single outputs
- **safety**: Covers authorization, data exposure, and policy failures — distinct from quality because they require remediation beyond quality improvement
- **infrastructure**: Covers hard limits (timeout, max_steps, error) — important for cost and reliability metrics even if failure cause is external

The taxonomy is implemented in `src/atfd/taxonomy.py` and is the primary artifact that ATFD's detection measurement is organized around.

**Risks:**
- Subcategory boundaries are sometimes ambiguous (e.g., missing_action vs. planning_failure; wrong_response vs. hallucination); inter-annotator agreement testing required
- The taxonomy may not generalize to future agent capabilities (e.g., embodied agents, audio agents); versioning required
- 7 categories × 23 subcategories may be too fine-grained for some tools to classify with statistical significance given 1,000 total trajectories

**Prior work:** MAST (Cemri NeurIPS 2025), Microsoft Taxonomy (2025), OWASP Agentic AI (2025), Vadlamudi (SSRN 2026), Winston AST 2025

---

## D7: Cost as First-Class Metric

**Decision:** ATFD treats cost as a first-class benchmark metric alongside detection rate, false positive rate, and category alignment. Every judge adapter must report: dollar cost per trajectory analyzed, latency (ms), token count (input + output), and API call count.

**Alternatives considered:**
- **Accuracy-only metrics:** Standard in academic benchmarks. Ignores the practical reality that monitoring tools impose their own costs on operators.
- **Cost as secondary metric (report but don't rank):** Reduces the emphasis on cost in the leaderboard; may be appropriate if cost varies by 2–3×. In practice, cost varies by 100–1,000× across tools (e.g., Galileo Luna-2 at $0.02/1M tokens vs. GPT-4 judge at $30/1M tokens).
- **Cost-per-correct-detection (composite):** Attractive for decision-making but requires fixing a weighting between accuracy and cost that is inherently value-laden.

**Rationale:**
The cost spread across monitoring tools is large enough to be determinative for production adoption decisions:
- A tool that costs $0.05 per trajectory to analyze with 80% detection rate may be preferred over a tool that costs $5.00 per trajectory with 85% detection rate, depending on traffic volume
- The GetOnStack multi-agent cost explosion case ($127 → $47,000) illustrates that a monitoring tool with a high cost may not be deployable on high-volume traffic
- The CLEAR framework (arXiv:2511.14136) empirically demonstrates that enterprise deployment requires multi-objective optimization across cost, latency, efficacy, assurance, and reliability

Reporting cost separately from accuracy allows benchmark users to construct their own cost-accuracy tradeoff curves rather than imposing a fixed weighting. The leaderboard shows a Pareto frontier rather than a single ranking.

**Implementation:** `src/atfd/schema.py` (`CostReport` model), `src/atfd/metrics.py` (cost aggregation), judge adapter interface requirement.

**Risks:**
- API pricing changes over time, making cost comparisons between benchmark runs stale; timestamps and model version must be recorded alongside cost
- Self-hosted tools (Arize Phoenix) have zero API cost but non-zero infrastructure cost; benchmark reports API cost only, with a note on infrastructure cost for self-hosted options
- Cost reporting requires tool providers to expose per-call cost data; some tools may not support this level of granularity

**Prior work:** CLEAR framework (arXiv:2511.14136), GetOnStack failure (Operator Collective, 2025), Galileo Luna-2 cost claims ($0.02/1M tokens), LLM observability cost tracking literature
