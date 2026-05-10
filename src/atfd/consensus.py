"""Multi-source ground truth consensus computation for the ATFD benchmark.

Given labels from N sources (programmatic checks, LLM judges, human annotators),
computes a single consensus outcome using gold/majority/disputed voting rules.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from atfd.schema import Outcome, SourceLabel


@dataclass
class ConsensusResult:
    """Result of consensus computation across multiple labeling sources."""

    outcome: Outcome
    consensus: str  # "gold" | "majority" | "disputed"
    failure_categories: list[str] = field(default_factory=list)
    quality_categories: list[str] = field(default_factory=list)
    disagreeing_sources: list[str] = field(default_factory=list)
    source_outcomes: dict[str, Outcome] = field(default_factory=dict)


def compute_consensus(labels: dict[str, SourceLabel]) -> ConsensusResult:
    """Compute consensus outcome from a mapping of source name -> SourceLabel.

    Voting rules:
    - Gold     — all sources agree on the same outcome.
    - Majority — strictly more than 50% of sources agree on one outcome.
    - Disputed — no outcome reaches a strict majority.

    Category merging: failure_categories and quality_categories are collected
    from all sources whose outcome is fail or degraded, deduplicated while
    preserving first-seen insertion order.
    """
    if not labels:
        raise ValueError("labels must not be empty")

    n_sources = len(labels)

    # Map each source to its Outcome enum value.
    source_outcomes: dict[str, Outcome] = {
        name: Outcome(label.outcome) for name, label in labels.items()
    }

    outcome_counts: Counter[Outcome] = Counter(source_outcomes.values())
    winner_outcome, winner_count = outcome_counts.most_common(1)[0]

    # Determine consensus level.
    if winner_count == n_sources:
        consensus = "gold"
    elif winner_count > n_sources / 2:
        consensus = "majority"
    else:
        consensus = "disputed"

    # Identify disagreeing sources (those that did not vote for the winner).
    disagreeing_sources: list[str] = [
        name
        for name, outcome in source_outcomes.items()
        if outcome != winner_outcome
    ]

    # Merge categories from all sources that labeled fail or degraded.
    # Preserve first-seen insertion order while deduplicating.
    seen_failure: set[str] = set()
    failure_categories: list[str] = []
    seen_quality: set[str] = set()
    quality_categories: list[str] = []

    for name, label in labels.items():
        src_outcome = source_outcomes[name]
        if src_outcome in (Outcome.FAIL, Outcome.DEGRADED):
            for cat in label.failure_categories:
                if cat not in seen_failure:
                    seen_failure.add(cat)
                    failure_categories.append(cat)
            for cat in label.quality_categories:
                if cat not in seen_quality:
                    seen_quality.add(cat)
                    quality_categories.append(cat)

    return ConsensusResult(
        outcome=winner_outcome,
        consensus=consensus,
        failure_categories=failure_categories,
        quality_categories=quality_categories,
        disagreeing_sources=disagreeing_sources,
        source_outcomes=source_outcomes,
    )
