# Annotated Bibliography: Related Work

*30+ papers curated for ATFD v2. Last updated May 2026.*

Papers are grouped by research area. Each entry includes: full citation, one-sentence summary, relevance to ATFD, key finding to cite, and BibTeX key.

---

## 1. Agent Benchmarks

### tau-bench / tau2-bench
**Citation:** Yao, S., et al. "τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains." ICLR 2025. arXiv:2406.12045.

**Summary:** tau-bench simulates dynamic conversations between a user (LLM-simulated) and a customer-service agent given API tools and policy guidelines in retail and airline domains; it introduces the pass^k metric to measure reliability across multiple trials.

**Relevance to ATFD:** tau-bench is one of ATFD's three source datasets. Its retail and airline trajectories provide ground-truth action sequences against which ATFD judges can be evaluated. The pass^k metric motivates ATFD's multi-trial reliability measurement.

**Key finding:** State-of-the-art agents (GPT-4o) succeed on fewer than 50% of tasks; pass^8 drops below 25% in retail, revealing that single-trial benchmarks mask unreliability.

```bibtex
@inproceedings{yao2025taubench,
  title={$\tau$-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains},
  author={Yao, Shunyu and others},
  booktitle={The Thirteenth International Conference on Learning Representations},
  year={2025},
  url={https://arxiv.org/abs/2406.12045}
}
```

---

### tau2-bench / tau3-bench
**Citation:** Sierra Research. "τ²-Bench: Evaluating Conversational Agents in a Dual-Role Setting." arXiv:2506.07982, 2025.

**Summary:** tau2-bench extends the original with a banking domain, voice evaluation modality, and 75+ task quality fixes; tau3-bench adds further domain expansion.

**Relevance to ATFD:** The expanded domains in tau2/tau3 informed ATFD's domain coverage decisions. The quality fixes (removing incorrect expected actions, fixing impossible constraints) are directly relevant to ATFD's multi-source consensus design.

**Key finding:** Task quality issues in tau-bench (incorrect expected actions, ambiguous instructions) inflate failure rates; careful ground-truth curation is essential for any agent benchmark.

```bibtex
@article{sierra2025tau2bench,
  title={$\tau^2$-Bench: Evaluating Conversational Agents in a Dual-Role Setting},
  author={Sierra Research},
  journal={arXiv preprint arXiv:2506.07982},
  year={2025}
}
```

---

### SWE-bench
**Citation:** Jimenez, C.E., Yang, J., Wettig, A., Yao, S., Pei, K., Press, O., and Narasimhan, K.R. "SWE-bench: Can Language Models Resolve Real-world Github Issues?" ICLR 2024. arXiv:2310.06770.

**Summary:** SWE-bench evaluates language models on 2,294 software engineering tasks drawn from real GitHub issues and pull requests across 12 Python repositories, using automated test suites as ground truth.

**Relevance to ATFD:** SWE-bench is one of ATFD's three source datasets. Its coding trajectories (tool calls, file edits, test execution) represent a distinct failure mode space from tau-bench's conversational/transactional tasks. SWE-bench's automated test-suite ground truth is the gold standard that ATFD's consensus mechanism tries to match for non-code domains.

**Key finding:** Task completion rates for leading models remained below 20% on the original benchmark; subsequent SWE-bench Verified reduced annotation noise and showed that benchmark quality matters more than raw task count.

```bibtex
@inproceedings{jimenez2024swebench,
  title={{SWE}-bench: Can Language Models Resolve Real-world Github Issues?},
  author={Carlos E Jimenez and John Yang and Alexander Wettig and Shunyu Yao and Kexin Pei and Ofir Press and Karthik R Narasimhan},
  booktitle={The Twelfth International Conference on Learning Representations},
  year={2024},
  url={https://openreview.net/forum?id=VTF8yNQM66}
}
```

---

### AgentBench
**Citation:** Liu, X., Yu, H., Zhang, H., Xu, Y., Lei, X., Lai, H., Gu, Y., et al. "AgentBench: Evaluating LLMs as Agents." ICLR 2024. arXiv:2308.03688.

**Summary:** AgentBench is the first comprehensive benchmark evaluating LLMs as agents across 8 diverse environments (web browsing, code execution, database, OS, knowledge graph, card games, lateral thinking, household tasks) with multi-turn open-ended evaluation.

**Relevance to ATFD:** Establishes the multi-environment evaluation paradigm that ATFD inherits. The finding that poor long-term reasoning and instruction following are main obstacles motivates ATFD's process and communication failure categories.

**Key finding:** Significant performance disparity between top commercial LLMs and 70B open-source models; poor long-term reasoning and instruction following are the dominant failure modes.

```bibtex
@inproceedings{liu2024agentbench,
  title={AgentBench: Evaluating LLMs as Agents},
  author={Xiao Liu and Hao Yu and Hanchen Zhang and Yifan Xu and Xuanyu Lei and Hanyu Lai and Yu Gu and Hangliang Ding and Kaiwen Men and Kejuan Yang and Shudan Zhang and Xiang Deng and Aohan Zeng and Zhengxiao Du and Chenhui Zhang and Sheng Shen and Tianjun Zhang and Yu Su and Huan Sun and Minlie Huang and Yuxiao Dong and Jie Tang},
  booktitle={The Twelfth International Conference on Learning Representations},
  year={2024},
  url={https://openreview.net/forum?id=zAdUB0aCTQ}
}
```

---

### AgentBoard
**Citation:** Ma, C., Zhang, J., Zhu, Z., Yang, C., Yang, Y., Jin, Y., Lan, Z., Kong, L., and He, J. "AgentBoard: An Analytical Evaluation Board of Multi-turn LLM Agents." NeurIPS 2024 (Oral). arXiv:2401.13178.

**Summary:** AgentBoard provides a fine-grained progress-rate metric and a comprehensive multi-turn evaluation framework across 9 task types with partially-observable environments, enabling analytical breakdown of agent performance.

**Relevance to ATFD:** AgentBoard's fine-grained progress rate metric (capturing incremental progress rather than binary pass/fail) directly motivates ATFD's three-tier outcome (pass/degraded/fail) rather than binary success. The 9-task framework informs ATFD's domain sampling strategy.

**Key finding:** Binary success metrics mask important performance variations; a fine-grained progress metric reveals that models often partially complete tasks, with meaningful signal in the partial completion space.

```bibtex
@inproceedings{ma2024agentboard,
  title={AgentBoard: An Analytical Evaluation Board of Multi-turn LLM Agents},
  author={Chang Ma and Junlei Zhang and Zhihao Zhu and Cheng Yang and Yujiu Yang and Yaohui Jin and Zhenzhong Lan and Lingpeng Kong and Junxian He},
  booktitle={The Thirty-eighth Annual Conference on Neural Information Processing Systems},
  year={2024},
  url={https://arxiv.org/abs/2401.13178}
}
```

---

### WebArena
**Citation:** Zhou, S., Xu, F.F., Zhu, H., Zhou, X., Lo, R., Sridhar, A., Cheng, X., Bisk, Y., Fried, D., Alon, U., et al. "WebArena: A Realistic Web Environment for Building Autonomous Agents." ICLR 2024. arXiv:2307.13854.

**Summary:** WebArena provides a realistic, self-hosted web environment spanning four domains (e-commerce, social forums, software development, content management) for evaluating web-browsing agents on functional task completion.

**Relevance to ATFD:** WebArena's functional correctness evaluation methodology (checking final state rather than action sequence) informs ATFD's state failure category. Its domain coverage provides a benchmark for what constitutes realistic task diversity.

**Key finding:** Best-performing agents achieve only 10-14% task success on WebArena, with most failures arising from incorrect action selection and hallucinated web content.

```bibtex
@inproceedings{zhou2024webarena,
  title={WebArena: A Realistic Web Environment for Building Autonomous Agents},
  author={Shuyan Zhou and Frank F Xu and Hao Zhu and Xuhui Zhou and Robert Lo and Abishek Sridhar and Xianyi Cheng and Yonatan Bisk and Daniel Fried and Uri Alon and others},
  booktitle={The Twelfth International Conference on Learning Representations},
  year={2024},
  url={https://openreview.net/forum?id=oKn9c6ytLx}
}
```

---

### GAIA
**Citation:** Mialon, G., Fourrier, C., Swift, C., Wolf, T., LeCun, Y., and Scialom, T. "GAIA: a benchmark for General AI Assistants." ICLR 2024. arXiv:2311.12983.

**Summary:** GAIA proposes 466 real-world questions requiring reasoning, multi-modality, web browsing, and tool use, where humans score 92% but GPT-4 with plugins scores only 15%.

**Relevance to ATFD:** GAIA's dramatic human–AI performance gap on real-world tasks motivates the need for automated failure detection at scale. Its multi-capability task structure informs ATFD's taxonomy dimensions (quality, process, communication failures all appear in GAIA failures).

**Key finding:** The gap between human (92%) and best AI (15%) performance on real-world multi-step tasks is far larger than on narrowly-defined benchmarks, suggesting that capability benchmarks underestimate deployment failure rates.

```bibtex
@inproceedings{mialon2024gaia,
  title={{GAIA}: a benchmark for General AI Assistants},
  author={Gr{\'e}goire Mialon and Cl{\'e}mentine Fourrier and Craig Swift and Thomas Wolf and Yann LeCun and Thomas Scialom},
  booktitle={The Twelfth International Conference on Learning Representations},
  year={2024},
  url={https://openreview.net/forum?id=fibxvahvs3}
}
```

---

### ToolLLM / ToolBench
**Citation:** Qin, Y., Liang, S., Ye, Y., Zhu, K., Yan, L., Lu, Y., Lin, Y., Cong, X., Tang, X., Qian, B., et al. "ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs." ICLR 2024 (Spotlight). arXiv:2307.16789.

**Summary:** ToolLLM introduces ToolBench (instruction-tuning dataset for 16,464 APIs), a depth-first search decision tree algorithm for multi-step tool use, and ToolEval (an automatic tool-use evaluator); fine-tuning LLaMA on ToolBench achieves ChatGPT-level tool use.

**Relevance to ATFD:** ToolLLM directly motivates ATFD's action failure categories (wrong_tool, wrong_args, missing_action). ToolEval's automatic evaluation methodology is a related work to ATFD's LLM-judge evaluation approach.

**Key finding:** Teaching models to use 16k+ real APIs via instruction tuning and structured search achieves ChatGPT-level performance, but failure analysis reveals that incorrect argument formatting and API selection are the dominant error modes.

```bibtex
@inproceedings{qin2024toolllm,
  title={ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs},
  author={Yujia Qin and Shihao Liang and Yining Ye and Kun Zhu and Lan Yan and Yaxi Lu and Yankai Lin and Xin Cong and Xiangru Tang and Bill Qian and Siyuan Zhao and Lauren Hong and Runchu Tian and Ruobing Xie and Jie Zhou and Mark Gerstein and Dahai Li and Zhiyuan Liu and Maosong Sun},
  booktitle={The Twelfth International Conference on Learning Representations},
  year={2024},
  url={https://openreview.net/forum?id=dHng2O0Jjr}
}
```

---

## 2. LLM-as-Judge

### MT-Bench / Chatbot Arena
**Citation:** Zheng, L., Chiang, W.L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D., Xing, E.P., Zhang, H., Gonzalez, J.E., and Stoica, I. "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena." NeurIPS 2023. arXiv:2306.05685.

**Summary:** Introduces LLM-as-judge methodology using GPT-4 to evaluate multi-turn conversations and validates it against human preferences via Chatbot Arena's crowdsourced ELO system.

**Relevance to ATFD:** The LLM-as-judge methodology underpins ATFD's LLM-judge baseline and is the theoretical foundation for using LLM verdicts as ground truth. The paper's analysis of position bias, verbosity bias, and self-enhancement bias directly informs ATFD's judge reliability metrics.

**Key finding:** GPT-4-as-judge achieves >80% agreement with human experts on single-answer grading and >80% on pairwise grading; biases (position, verbosity, self-enhancement) exist but can be mitigated with calibration.

```bibtex
@inproceedings{zheng2023judging,
  title={Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena},
  author={Lianmin Zheng and Wei-Lin Chiang and Ying Sheng and Siyuan Zhuang and Zhanghao Wu and Yonghao Zhuang and Zi Lin and Zhuohan Li and Dacheng Li and Eric P. Xing and Hao Zhang and Joseph E. Gonzalez and Ion Stoica},
  booktitle={Advances in Neural Information Processing Systems 36},
  year={2023},
  url={https://papers.nips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html}
}
```

---

### G-Eval
**Citation:** Liu, Y., Iter, D., Xu, Y., Wang, S., Xu, R., and Zhu, C. "G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment." EMNLP 2023. arXiv:2303.16634.

**Summary:** G-Eval uses chain-of-thought reasoning and a form-filling paradigm with GPT-4 to evaluate NLG outputs, achieving a Spearman correlation of 0.514 with human judgments on summarization — outperforming all prior automated metrics.

**Relevance to ATFD:** G-Eval's form-filling paradigm (structured criteria → numerical scores) is the template for ATFD's domain-specific quality rubrics. The paper's demonstration that rubric structure improves LLM-judge alignment with humans motivates ATFD's D3 design decision (domain-specific rubrics).

**Key finding:** Structured chain-of-thought evaluation rubrics substantially improve LLM-judge alignment with human judgments; the approach also reveals a bias toward LLM-generated content that evaluators should account for.

```bibtex
@inproceedings{liu2023geval,
  title={{G-Eval}: NLG Evaluation using GPT-4 with Better Human Alignment},
  author={Yang Liu and Dan Iter and Yichong Xu and Shuohang Wang and Ruochen Xu and Chenguang Zhu},
  booktitle={Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing},
  year={2023},
  url={https://aclanthology.org/2023.emnlp-main.153/}
}
```

---

### AlpacaEval / Length-Controlled AlpacaEval
**Citation:** Dubois, Y., Galambosi, B., Liang, P., and Hashimoto, T. "Length-Controlled AlpacaEval: A Simple Way to Debias Automatic Evaluators." COLM 2024. arXiv:2404.04475.

**Summary:** Introduces a regression-based debiasing approach for LLM evaluators, specifically targeting length bias in AlpacaEval, showing that controlling for response length substantially improves correlation with human preferences.

**Relevance to ATFD:** ATFD's judge evaluation must account for length bias: a verbose-but-wrong agent trajectory may score better than a concise-but-correct one on naive LLM judges. Length-Controlled AlpacaEval provides the methodology for detecting and correcting this bias in ATFD's judge evaluations.

**Key finding:** LLM-based auto-annotators have systematic length bias that inflates win rates for longer responses; a simple regression control removes this bias and improves correlation with human preferences.

```bibtex
@inproceedings{dubois2024alpacaeval,
  title={Length-Controlled AlpacaEval: A Simple Way to Debias Automatic Evaluators},
  author={Yann Dubois and Bal{\'a}zs Galambosi and Percy Liang and Tatsunori B. Hashimoto},
  booktitle={First Conference on Language Modeling},
  year={2024},
  url={https://arxiv.org/abs/2404.04475}
}
```

---

### LLMs-as-Judges Survey
**Citation:** Gu, J., et al. "LLMs-as-Judges: A Comprehensive Survey on LLM-based Evaluation Methods." arXiv:2412.05579, 2024.

**Summary:** A comprehensive survey cataloging LLM-as-judge approaches across NLG, code, reasoning, and agentic tasks, with a taxonomy of bias types and mitigation strategies.

**Relevance to ATFD:** Provides the theoretical framework for understanding when and why LLM judges succeed or fail — directly applicable to ATFD's LLM-judge baseline evaluation and the analysis of judge reliability.

**Key finding:** LLM judges exhibit at least 8 distinct bias types (position, verbosity, self-enhancement, primacy/recency, format, cultural, sycophancy, and hallucination); multi-judge consensus mitigates most of these.

```bibtex
@article{gu2024llmjudge,
  title={{LLMs}-as-Judges: A Comprehensive Survey on LLM-based Evaluation Methods},
  author={Gu, Jiawei and others},
  journal={arXiv preprint arXiv:2412.05579},
  year={2024}
}
```

---

## 3. Agent Safety and Failure Analysis

### Concrete Problems in AI Safety
**Citation:** Amodei, D., Olah, C., Steinhardt, J., Christiano, P., Schulman, J., and Mané, D. "Concrete Problems in AI Safety." arXiv:1606.06565, 2016.

**Summary:** Seminal paper framing five practical research problems in AI safety — avoiding side effects, avoiding reward hacking, scalable oversight, safe exploration, and distributional shift — with concrete proposals for each.

**Relevance to ATFD:** ATFD's safety failure category (permission_escalation, data_leakage, policy_violation) maps directly to the "avoiding side effects" and "reward hacking" problems defined here. The paper provides the intellectual lineage for treating agent safety failures as a distinct category from task failures.

**Key finding:** Current ML systems can fail in unexpected ways when deployed in complex environments; the five problems identified remain active research challenges nearly a decade later.

```bibtex
@article{amodei2016concrete,
  title={Concrete Problems in AI Safety},
  author={Dario Amodei and Chris Olah and Jacob Steinhardt and Paul Christiano and John Schulman and Dan Man{\'e}},
  journal={arXiv preprint arXiv:1606.06565},
  year={2016}
}
```

---

### Why Do Multi-Agent LLM Systems Fail? (MAST)
**Citation:** Cemri, M., Pan, M.Z., Yang, S., Agrawal, L.A., Chopra, B., Tiwari, R., Keutzer, K., Parameswaran, A., Klein, D., Ramchandran, K., Zaharia, M., Gonzalez, J.E., and Stoica, I. "Why Do Multi-Agent LLM Systems Fail?" NeurIPS 2025 (Spotlight). arXiv:2503.13657.

**Summary:** Introduces MAST (Multi-Agent System Failure Taxonomy) with 14 failure modes across 3 categories (system design issues, inter-agent misalignment, task verification), validated on 1,600+ annotated traces across 7 MAS frameworks.

**Relevance to ATFD:** MAST is the closest prior work to ATFD's taxonomy. ATFD's 7-category taxonomy extends MAST by adding infrastructure failures, distinguishing communication from state failures, and covering single-agent as well as multi-agent scenarios. MAST's inter-annotator agreement methodology (kappa=0.88) informs ATFD's annotation protocol.

**Key finding:** Specification ambiguity and unstructured coordination protocols account for 79% of multi-agent system failures in production, with failure rates of 41–87% across frameworks.

```bibtex
@inproceedings{cemri2025mast,
  title={Why Do Multi-Agent LLM Systems Fail?},
  author={Mert Cemri and Melissa Z. Pan and Shuyi Yang and Lakshya A Agrawal and Bhavya Chopra and Rishabh Tiwari and Kurt Keutzer and Aditya Parameswaran and Dan Klein and Kannan Ramchandran and Matei Zaharia and Joseph E. Gonzalez and Ion Stoica},
  booktitle={Advances in Neural Information Processing Systems 38},
  year={2025},
  url={https://arxiv.org/abs/2503.13657}
}
```

---

### How Do LLMs Fail In Agentic Scenarios?
**Citation:** Anonymous. "How Do LLMs Fail In Agentic Scenarios?" arXiv:2512.07497, 2025.

**Summary:** Analyzes 900 execution traces across filesystem, text extraction, CSV analysis, and SQL scenarios using the Kamiwaza Agentic Merit Index (KAMI) benchmark, identifying that failure to recover from tool call errors is the dominant failure pattern.

**Relevance to ATFD:** Provides empirical support for ATFD's process failure category (tool_loop, planning_failure) and the infrastructure failure category (error). The finding that suboptimal strategies (e.g., reading more lines than needed) constitute a distinct failure mode maps to ATFD's quality.suboptimal_approach subcategory.

**Key finding:** In failed agentic traces, the dominant pattern is inability to recover from tool errors; in successful traces, models frequently use suboptimal strategies that still produce correct outputs.

```bibtex
@article{kami2025fail,
  title={How Do LLMs Fail In Agentic Scenarios?},
  author={Anonymous},
  journal={arXiv preprint arXiv:2512.07497},
  year={2025}
}
```

---

### Agent-SafetyBench
**Citation:** Zhang, X., et al. "Agent-SafetyBench: Evaluating the Safety of LLM Agents." arXiv:2412.14470, 2024.

**Summary:** A safety-focused benchmark with 349 interaction environments and 2,000 test cases evaluating 8 categories of safety risks and 10 failure modes in agent interactions.

**Relevance to ATFD:** Agent-SafetyBench directly covers ATFD's safety category. Its 10 failure modes overlap with ATFD's permission_escalation, data_leakage, and policy_violation subcategories. The benchmark's methodology (interaction environments rather than static trajectories) informs ATFD's trajectory collection approach.

**Key finding:** Current LLMs exhibit significant safety vulnerabilities in agentic scenarios; safety failure rates remain high even on frontier models.

```bibtex
@article{zhang2024agentsafetybench,
  title={Agent-SafetyBench: Evaluating the Safety of LLM Agents},
  author={Zhang, Xin and others},
  journal={arXiv preprint arXiv:2412.14470},
  year={2024}
}
```

---

### Taxonomy of Failures in Tool-Augmented LLMs
**Citation:** Winston, C., et al. "A Taxonomy of Failures in Tool-Augmented LLMs." AST 2025. https://homes.cs.washington.edu/~rjust/publ/tallm_testing_ast_2025.pdf

**Summary:** Proposes a taxonomy of tool-use failures in LLMs across categories including incorrect invocation, argument errors, missing invocations, and cascading failures; presents a testing methodology for systematic discovery.

**Relevance to ATFD:** ATFD's action category (wrong_tool, wrong_args, missing_action) maps directly to this taxonomy, providing prior-work grounding for these subcategory definitions. The testing methodology is related to ATFD's trajectory collection for the synthetic dataset.

**Key finding:** Tool failures in LLM agents follow predictable patterns amenable to systematic testing; argument errors are the most common tool failure type.

```bibtex
@inproceedings{winston2025taxonomy,
  title={A Taxonomy of Failures in Tool-Augmented LLMs},
  author={Cailin Winston and others},
  booktitle={IEEE/ACM International Workshop on Automated Software Testing},
  year={2025},
  url={https://homes.cs.washington.edu/~rjust/publ/tallm_testing_ast_2025.pdf}
}
```

---

### AgentSafe / AGENTSAFE
**Citation:** Anonymous. "AGENTSAFE: A Unified Framework for Ethical Assurance and Governance in Agentic AI." arXiv:2512.03180, 2025.

**Summary:** Proposes a governance framework for LLM-based agentic systems operationalizing the AI Risk Repository into design, runtime, and audit controls.

**Relevance to ATFD:** AGENTSAFE's runtime control framework is a design alternative to ATFD's passive monitoring approach, providing context for why monitoring/detection tooling like ATFD's benchmark is needed as a complement to governance frameworks.

**Key finding:** Most existing agent safety approaches focus on design-time or post-hoc controls; runtime monitoring of agent trajectories remains an open problem.

```bibtex
@article{agentsafe2025,
  title={{AGENTSAFE}: A Unified Framework for Ethical Assurance and Governance in Agentic AI},
  author={Anonymous},
  journal={arXiv preprint arXiv:2512.03180},
  year={2025}
}
```

---

### Microsoft Failure Mode Taxonomy
**Citation:** Microsoft. "Taxonomy of Failure Mode in Agentic AI Systems." Microsoft Technical Whitepaper, 2025. https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Taxonomy-of-Failure-Mode-in-Agentic-AI-Systems-Whitepaper.pdf

**Summary:** Microsoft's industry whitepaper categorizing failure modes unique to agentic AI systems, covering planning, execution, coordination, and safety dimensions.

**Relevance to ATFD:** Provides industry validation of ATFD's failure taxonomy. ATFD's 7 categories overlap substantially with Microsoft's dimensions, with ATFD providing more granular subcategories and an empirical evaluation framework.

**Key finding:** Agentic AI systems introduce failure modes not present in static LLM deployments, particularly in multi-step planning and tool coordination.

```bibtex
@techreport{microsoft2025taxonomy,
  title={Taxonomy of Failure Mode in Agentic AI Systems},
  author={{Microsoft}},
  institution={Microsoft},
  year={2025},
  url={https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Taxonomy-of-Failure-Mode-in-Agentic-AI-Systems-Whitepaper.pdf}
}
```

---

### Why AI Agents Fail — Vadlamudi (SSRN)
**Citation:** Vadlamudi, S. "Why AI Agents Fail: A Taxonomy of Failure Modes in Autonomous LLM-Based Systems." SSRN:6572478, 2026.

**Summary:** Proposes a four-dimensional taxonomy of LLM agent failure modes organized around: reasoning/planning, tool use/action execution, memory/context management, and multi-agent orchestration.

**Relevance to ATFD:** Recent independent taxonomy work that validates ATFD's design choices. The four dimensions map to ATFD's process, action, state, and communication categories respectively.

**Key finding:** Agent failures cluster into four functional module categories, suggesting that monitoring tools should instrument each module independently rather than treating the agent as a black box.

```bibtex
@article{vadlamudi2026taxonomy,
  title={Why AI Agents Fail: A Taxonomy of Failure Modes in Autonomous LLM-Based Systems},
  author={Suresh Vadlamudi},
  journal={SSRN},
  number={6572478},
  year={2026},
  url={https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6572478}
}
```

---

## 4. Runtime Monitoring and Process Mining

### Beyond Black-Box Benchmarking
**Citation:** Moshkovich, D., Mulian, H., Zeltyn, S., Eder, N., Skarbovsky, I., and Abitbol, R. "Beyond Black-Box Benchmarking: Observability, Analytics, and Optimization of Agentic Systems." KDD 2025. arXiv:2503.06745.

**Summary:** Proposes extending standard observability frameworks with taxonomies for expected analytics outcomes (discovered flows and issues) built from agent runtime logs, introducing a non-black-box benchmarking approach for agent evaluation systems.

**Relevance to ATFD:** The closest prior work in the agent observability space to ATFD's contribution. The paper argues for moving beyond black-box benchmarking — exactly ATFD's thesis. Key difference: ATFD provides a concrete benchmark for evaluating monitoring tools, while this paper proposes a framework for how such tools should work.

**Key finding:** 79% of users agree that non-deterministic agent flow is a major challenge for evaluation; current black-box benchmarking approaches fail to capture the quality of monitoring tools themselves.

```bibtex
@inproceedings{moshkovich2025beyond,
  title={Beyond Black-Box Benchmarking: Observability, Analytics, and Optimization of Agentic Systems},
  author={Dany Moshkovich and Hadar Mulian and Sergey Zeltyn and Natti Eder and Inna Skarbovsky and Roy Abitbol},
  booktitle={Proceedings of the 31st ACM SIGKDD Conference on Knowledge Discovery and Data Mining},
  year={2025},
  url={https://arxiv.org/abs/2503.06745}
}
```

---

### Process Mining: Discovery, Conformance and Enhancement
**Citation:** van der Aalst, W.M.P. "Process Mining: Discovery, Conformance and Enhancement of Business Processes." Springer, 2011. (2nd ed. 2016)

**Summary:** The foundational textbook for process mining, covering process discovery (extracting process models from event logs), conformance checking (comparing observed vs. expected behavior), and enhancement (improving process models from log data).

**Relevance to ATFD:** Agent trajectory analysis is a specific instance of process mining. ATFD's failure detection task is analogous to conformance checking: comparing an observed agent trajectory against expected behavior. The process mining literature provides formal foundations for ATFD's evaluation methodology.

**Key finding:** Conformance checking can systematically detect deviations between observed event logs and reference process models — a methodology directly applicable to agent trajectory failure detection.

```bibtex
@book{vanderaalst2016process,
  title={Process Mining: Discovery, Conformance and Enhancement of Business Processes},
  author={van der Aalst, Wil M. P.},
  publisher={Springer},
  edition={2},
  year={2016}
}
```

---

### Evaluating LLMs on Business Process Modeling
**Citation:** Berti, A., Kourani, H., and van der Aalst, W. "Evaluating Large Language Models on Business Process Modeling: Framework, Benchmark, and Self-Improvement Analysis." Software and Systems Modeling, 2025.

**Summary:** Evaluates LLMs on process mining tasks (discovery, conformance checking) via PM-LLM benchmark, showing that LLMs can support conformance checking with appropriate prompting.

**Relevance to ATFD:** Demonstrates that LLM-based approaches can perform conformance checking — directly validating ATFD's LLM-judge baseline design. The benchmark methodology informs ATFD's evaluation harness design.

**Key finding:** LLMs achieve moderate performance on process mining tasks but benefit substantially from structured prompting; conformance checking is within LLM capability for well-structured process descriptions.

```bibtex
@article{berti2025llmprocess,
  title={Evaluating Large Language Models on Business Process Modeling: Framework, Benchmark, and Self-Improvement Analysis},
  author={Berti, Alessandro and Kourani, Humam and van der Aalst, Wil M. P.},
  journal={Software and Systems Modeling},
  year={2025},
  publisher={Springer}
}
```

---

## 5. Evaluation Methodology and Benchmarking

### A Review of Agent Data Evaluation (2025)
**Citation:** Anonymous. "A Review of Agent Data Evaluation: Status, Challenges, and Future Prospects as of 2025." Scientific Research, 2025.

**Summary:** Surveys the state of agent data evaluation methodology, identifying challenges including non-determinism, multi-step dependencies, and the need for domain-specific quality rubrics.

**Relevance to ATFD:** Provides a systematic review of the challenges ATFD addresses. The paper's identification of non-determinism and multi-step dependencies as key challenges directly motivates ATFD's multi-source consensus design and three-tier outcome metric.

**Key finding:** Existing agent evaluation methods struggle with non-determinism and lack domain-specific quality rubrics; automated evaluation tools are needed to scale human-quality assessment.

```bibtex
@article{review2025agent,
  title={A Review of Agent Data Evaluation: Status, Challenges, and Future Prospects as of 2025},
  author={Anonymous},
  journal={Scientific Research},
  year={2025}
}
```

---

### Counting on Consensus (Inter-Annotator Agreement)
**Citation:** Anonymous. "Counting on Consensus: Selecting the Right Inter-annotator Agreement Metric for NLP Annotation and Evaluation." arXiv:2603.06865, 2026.

**Summary:** A methodological guide for selecting inter-annotator agreement metrics in NLP evaluation, covering Cohen's kappa, Krippendorff's alpha, and ordinal agreement metrics with recommendations for different task types.

**Relevance to ATFD:** ATFD's multi-source consensus mechanism requires a principled approach to measuring annotator agreement. This paper provides the methodology for selecting and reporting agreement metrics in ATFD's ground-truth construction.

**Key finding:** The choice of agreement metric substantially impacts reported reliability; ordinal tasks (like ATFD's three-tier outcome) require ordinal agreement metrics rather than nominal kappa.

```bibtex
@article{consensus2026,
  title={Counting on Consensus: Selecting the Right Inter-annotator Agreement Metric for NLP Annotation and Evaluation},
  author={Anonymous},
  journal={arXiv preprint arXiv:2603.06865},
  year={2026}
}
```

---

### Beyond Agreement: Rethinking Ground Truth
**Citation:** Anonymous. "Beyond Agreement: Rethinking Ground Truth in Educational AI Annotation." arXiv:2508.00143, 2025.

**Summary:** Challenges the assumption that high inter-annotator agreement implies correct ground truth, arguing that high agreement can obscure systematic annotation errors while disagreement may indicate productive ambiguity.

**Relevance to ATFD:** Critical methodology paper for ATFD's ground-truth construction. ATFD must acknowledge that high consensus among its human/LLM annotators does not guarantee correctness, especially for novel failure types not covered by the taxonomy.

**Key finding:** High annotator agreement can be achieved on incorrect labels; validation against external criteria (task completion tests, domain expert review) is necessary to establish true ground truth.

```bibtex
@article{groundtruth2025,
  title={Beyond Agreement: Rethinking Ground Truth in Educational AI Annotation},
  author={Anonymous},
  journal={arXiv preprint arXiv:2508.00143},
  year={2025}
}
```

---

### Evaluation and Benchmarking of LLM Agents: A Survey
**Citation:** Anonymous. "Evaluation and Benchmarking of LLM Agents: A Survey." arXiv:2507.21504, 2025.

**Summary:** A comprehensive survey of LLM agent evaluation methodologies, categorizing approaches by evaluation target (capability, safety, reliability), ground truth source (automated, human, LLM), and task domain.

**Relevance to ATFD:** ATFD is positioned within the landscape this survey describes. The survey's categorization of evaluation targets and ground truth sources provides a framework for locating ATFD's contribution: monitoring-tool evaluation (a currently missing category) using multi-source consensus ground truth.

**Key finding:** No existing work evaluates the performance of monitoring/observability tools on agent trajectories — identifying exactly the gap ATFD addresses.

```bibtex
@article{survey2025eval,
  title={Evaluation and Benchmarking of LLM Agents: A Survey},
  author={Anonymous},
  journal={arXiv preprint arXiv:2507.21504},
  year={2025}
}
```

---

## 6. Agent Reliability and Production Observations

### What 1,200 Production Deployments Reveal About LLMOps
**Citation:** ZenML. "What 1,200 Production Deployments Reveal About LLMOps in 2025." ZenML Blog, 2025. https://www.zenml.io/blog/what-1200-production-deployments-reveal-about-llmops-in-2025

**Summary:** Industry report analyzing 1,200 production LLM deployments, finding that multi-agent systems fail at 41–87% rates and that most failures arise from specification ambiguity and coordination breakdowns.

**Relevance to ATFD:** Provides real-world motivation for ATFD's benchmark. The failure rates reported here are the deployment context within which ATFD's benchmark tools must operate.

**Key finding:** Multi-agent LLM systems fail at 41–87% rates in production; distributed tracing, token accounting, automated evals, and human feedback loops are now baseline requirements for production-ready LLMOps.

```bibtex
@misc{zenml2025production,
  title={What 1,200 Production Deployments Reveal About LLMOps in 2025},
  author={{ZenML}},
  year={2025},
  url={https://www.zenml.io/blog/what-1200-production-deployments-reveal-about-llmops-in-2025}
}
```

---

### The Reliability Gap: Agent Benchmarks for Enterprise
**Citation:** Simmering, P. "The Reliability Gap: Agent Benchmarks for Enterprise." Blog, 2025. https://simmering.dev/blog/agent-benchmarks/

**Summary:** Analysis of the gap between benchmark performance and enterprise deployment reliability for AI agents, arguing that existing benchmarks measure capability rather than reliability.

**Relevance to ATFD:** Motivates ATFD's focus on detection reliability over agent capability. The reliability gap argument supports ATFD's inclusion of pass^k-style reliability metrics.

**Key finding:** Enterprise deployment requires reliability over many runs, but most benchmarks report single-trial performance; the reliability gap between benchmarks and deployment is substantial.

```bibtex
@misc{simmering2025reliability,
  title={The Reliability Gap: Agent Benchmarks for Enterprise},
  author={Paul Simmering},
  year={2025},
  url={https://simmering.dev/blog/agent-benchmarks/}
}
```

---

### AgentLeak: Privacy Leakage in Multi-Agent LLM Systems
**Citation:** Anonymous. "AgentLeak: A Full-Stack Benchmark for Privacy Leakage in Multi-Agent LLM Systems." arXiv:2602.11510, 2026.

**Summary:** Benchmarks privacy leakage patterns in multi-agent systems, documenting PII in task prompts, financial profiles passed between agents, and compliance check failures that mirror production deployment patterns.

**Relevance to ATFD:** Directly motivates ATFD's safety.data_leakage and safety.policy_violation subcategories. The benchmark methodology (injecting PII into multi-agent workflows and measuring leakage) is directly applicable to ATFD's synthetic dataset generation for safety trajectories.

**Key finding:** Secrets stored in LLM context have a 78% probability of eventual exposure through prompt injection, hallucination, or logging failures across a multi-agent pipeline.

```bibtex
@article{agentleak2026,
  title={{AgentLeak}: A Full-Stack Benchmark for Privacy Leakage in Multi-Agent LLM Systems},
  author={Anonymous},
  journal={arXiv preprint arXiv:2602.11510},
  year={2026}
}
```

---

### Multi-Dimensional Evaluation of Enterprise Agentic AI
**Citation:** Anonymous. "Beyond Accuracy: A Multi-Dimensional Framework for Evaluating Enterprise Agentic AI Systems." arXiv:2511.14136, 2025.

**Summary:** Proposes the CLEAR framework (Cost, Latency, Efficacy, Assurance, Reliability) for evaluating enterprise agent deployments, with empirical evidence that domain-specific agents achieve 82.7% accuracy vs. 59–63% for general LLMs.

**Relevance to ATFD:** CLEAR directly motivates ATFD's D7 design decision (cost as first-class metric). The framework's five dimensions map to ATFD's metrics (cost, latency are explicit; efficacy maps to detection rate; assurance maps to false positive rate; reliability maps to consistency across trials).

**Key finding:** Enterprise agent evaluation requires five dimensions beyond accuracy; cost and latency are enterprise-critical but often excluded from academic benchmarks.

```bibtex
@article{clear2025,
  title={Beyond Accuracy: A Multi-Dimensional Framework for Evaluating Enterprise Agentic AI Systems},
  author={Anonymous},
  journal={arXiv preprint arXiv:2511.14136},
  year={2025}
}
```

---

### ToolFuzz
**Citation:** ETH SRI. "ToolFuzz: Fuzzing Framework for LLM Agent Tools." GitHub, 2025. https://github.com/eth-sri/ToolFuzz

**Summary:** A fuzzing framework that dynamically generates test prompts for LLM agent tools, combining fuzzing techniques with LLM-generated inputs to test tool correctness and robustness systematically.

**Relevance to ATFD:** ToolFuzz's test generation methodology informs ATFD's synthetic dataset generation for the action category (wrong_tool, wrong_args, missing_action). The framework demonstrates that systematic tool failure injection is feasible.

**Key finding:** Systematic fuzzing reveals tool failures that manual testing misses; combining LLM-based and traditional fuzzing techniques is more effective than either alone.

```bibtex
@misc{toolfuzz2025,
  title={{ToolFuzz}: Fuzzing Framework for LLM Agent Tools},
  author={{ETH SRI}},
  year={2025},
  url={https://github.com/eth-sri/ToolFuzz}
}
```

---

### Context Engineering: Why Agents Fail in Production
**Citation:** Inkeep. "Context Engineering: The Real Reason AI Agents Fail in Production." Blog, 2025. https://inkeep.com/blog/context-engineering-why-agents-fail

**Summary:** Analysis of how context management failures — context overflow, context rot, and early-signal degradation — are a leading cause of agent failures in production, distinct from model capability failures.

**Relevance to ATFD:** Directly motivates ATFD's process.context_overflow subcategory. The paper's argument that context failures are underappreciated relative to model capability failures supports ATFD's taxonomy design decision to include a dedicated process category.

**Key finding:** Context management failures, not model capability, are the leading cause of agent failures in production workflows handling long conversations or large tool outputs.

```bibtex
@misc{inkeep2025context,
  title={Context Engineering: The Real Reason AI Agents Fail in Production},
  author={{Inkeep}},
  year={2025},
  url={https://inkeep.com/blog/context-engineering-why-agents-fail}
}
```

---

### Common AI Agent Failures (Arize)
**Citation:** Arize AI. "Why AI Agents Break: A Field Analysis of Production Failures." Arize Blog, 2024. https://arize.com/blog/common-ai-agent-failures/

**Summary:** Field analysis of the most common AI agent failure modes observed in production across Arize's customer base, categorizing failures by type and providing detection guidance.

**Relevance to ATFD:** Provides practitioner validation of ATFD's taxonomy from a monitoring tool vendor's perspective. The failure types identified overlap substantially with ATFD's 7 categories.

**Key finding:** Tool misuse, hallucination, and planning failures account for the majority of production agent failures; most failures are not detectable via simple threshold-based monitoring.

```bibtex
@misc{arize2024failures,
  title={Why AI Agents Break: A Field Analysis of Production Failures},
  author={{Arize AI}},
  year={2024},
  url={https://arize.com/blog/common-ai-agent-failures/}
}
```

---

### AI Safety Incidents of 2024
**Citation:** Responsible AI Labs. "AI Safety Incidents of 2024: Lessons from Real-World Cases." Blog, 2025. https://responsibleailabs.ai/knowledge-hub/articles/ai-safety-incidents-2024

**Summary:** Documents 233 AI safety incidents in 2024 (a 56.4% increase from 149 in 2023), with hallucinations accounting for 38% of incidents; includes domain breakdown and severity analysis.

**Relevance to ATFD:** Provides epidemiological data on real-world agent failure rates that motivates the benchmark. The 56.4% year-over-year increase in incidents underscores the urgency of automated detection tooling.

**Key finding:** AI safety incidents increased 56.4% from 2023 to 2024; hallucinations remain the leading cause (38%); incidents are increasingly affecting business-critical workflows.

```bibtex
@misc{responsibleai2025incidents,
  title={AI Safety Incidents of 2024: Lessons from Real-World Cases},
  author={{Responsible AI Labs}},
  year={2025},
  url={https://responsibleailabs.ai/knowledge-hub/articles/ai-safety-incidents-2024}
}
```

---

### OWASP Agentic AI Top 10
**Citation:** OWASP Foundation. "OWASP Agentic AI: Top 10 Risks." 2025. https://owasp.org (referenced in: "A Survey of Agentic AI and Cybersecurity," arXiv:2601.05293)

**Summary:** OWASP's extension of the LLM Top 10 to agentic AI systems, identifying the ten highest-impact risk categories including prompt injection, tool misuse, data exfiltration, and cascading agent failures.

**Relevance to ATFD:** OWASP's risk taxonomy provides an industry-standard framing for ATFD's safety category and partially motivates the process category (cascading failures). ATFD's taxonomy design should be cross-referenced against OWASP for safety coverage.

**Key finding:** Agentic AI systems introduce unique risks not present in static LLM deployments; prompt injection and tool misuse are the highest-priority risks by likelihood and impact.

```bibtex
@misc{owasp2025agentic,
  title={{OWASP} Agentic AI: Top 10 Risks},
  author={{OWASP Foundation}},
  year={2025},
  url={https://owasp.org}
}
```

---

## Summary Table

| # | Key | Area | Venue | Year |
|---|-----|------|-------|------|
| 1 | yao2025taubench | Agent benchmarks | ICLR | 2025 |
| 2 | sierra2025tau2bench | Agent benchmarks | arXiv | 2025 |
| 3 | jimenez2024swebench | Agent benchmarks | ICLR | 2024 |
| 4 | liu2024agentbench | Agent benchmarks | ICLR | 2024 |
| 5 | ma2024agentboard | Agent benchmarks | NeurIPS | 2024 |
| 6 | zhou2024webarena | Agent benchmarks | ICLR | 2024 |
| 7 | mialon2024gaia | Agent benchmarks | ICLR | 2024 |
| 8 | qin2024toolllm | Agent benchmarks | ICLR | 2024 |
| 9 | zheng2023judging | LLM-as-judge | NeurIPS | 2023 |
| 10 | liu2023geval | LLM-as-judge | EMNLP | 2023 |
| 11 | dubois2024alpacaeval | LLM-as-judge | COLM | 2024 |
| 12 | gu2024llmjudge | LLM-as-judge | arXiv | 2024 |
| 13 | amodei2016concrete | Agent safety | arXiv | 2016 |
| 14 | cemri2025mast | Agent safety | NeurIPS | 2025 |
| 15 | kami2025fail | Agent safety | arXiv | 2025 |
| 16 | zhang2024agentsafetybench | Agent safety | arXiv | 2024 |
| 17 | winston2025taxonomy | Agent safety | AST | 2025 |
| 18 | agentsafe2025 | Agent safety | arXiv | 2025 |
| 19 | microsoft2025taxonomy | Agent safety | Whitepaper | 2025 |
| 20 | vadlamudi2026taxonomy | Agent safety | SSRN | 2026 |
| 21 | moshkovich2025beyond | Runtime monitoring | KDD | 2025 |
| 22 | vanderaalst2016process | Runtime monitoring | Springer | 2016 |
| 23 | berti2025llmprocess | Runtime monitoring | SoSyM | 2025 |
| 24 | review2025agent | Eval methodology | SciRes | 2025 |
| 25 | consensus2026 | Eval methodology | arXiv | 2026 |
| 26 | groundtruth2025 | Eval methodology | arXiv | 2025 |
| 27 | survey2025eval | Eval methodology | arXiv | 2025 |
| 28 | zenml2025production | Production obs. | Blog | 2025 |
| 29 | simmering2025reliability | Production obs. | Blog | 2025 |
| 30 | agentleak2026 | Agent safety | arXiv | 2026 |
| 31 | clear2025 | Eval methodology | arXiv | 2025 |
| 32 | toolfuzz2025 | Agent safety | GitHub | 2025 |
| 33 | inkeep2025context | Production obs. | Blog | 2025 |
| 34 | arize2024failures | Production obs. | Blog | 2024 |
| 35 | responsibleai2025incidents | Production obs. | Blog | 2025 |
| 36 | owasp2025agentic | Agent safety | OWASP | 2025 |
