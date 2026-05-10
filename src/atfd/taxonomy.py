"""
Failure taxonomy for the ATFD benchmark.

7 top-level categories, 23 subcategories covering the full space of
agent trajectory failures observed in the research corpus.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class FailureCategory:
    """A top-level failure category."""

    name: str
    description: str


@dataclass(frozen=True)
class FailureSubcategory:
    """A leaf-level failure subcategory belonging to one FailureCategory."""

    category: str       # name of parent FailureCategory
    name: str           # short identifier, unique within category
    description: str
    example: Optional[str] = field(default=None)


# ---------------------------------------------------------------------------
# Category definitions
# ---------------------------------------------------------------------------

_CATEGORIES: list[FailureCategory] = [
    FailureCategory(
        name="action",
        description="Failures in which the agent executes the wrong action or omits a required action.",
    ),
    FailureCategory(
        name="state",
        description="Failures resulting in an incorrect or incomplete system/environment state after a run.",
    ),
    FailureCategory(
        name="communication",
        description="Failures in the information the agent conveys to users or downstream systems.",
    ),
    FailureCategory(
        name="quality",
        description="Failures where the task is technically completed but the output is substandard.",
    ),
    FailureCategory(
        name="process",
        description="Failures in the agent's reasoning or execution flow — loops, overflows, and bad plans.",
    ),
    FailureCategory(
        name="safety",
        description="Failures involving unauthorized access, data exposure, or policy violations.",
    ),
    FailureCategory(
        name="infrastructure",
        description="Failures caused by hard execution limits or system-level errors.",
    ),
]

# ---------------------------------------------------------------------------
# Subcategory definitions (23 total)
# ---------------------------------------------------------------------------

_SUBCATEGORIES: list[FailureSubcategory] = [
    # action (3)
    FailureSubcategory(
        category="action",
        name="wrong_tool",
        description="Called incorrect tool for the intended operation.",
        example="cancel_order instead of modify_order",
    ),
    FailureSubcategory(
        category="action",
        name="wrong_args",
        description="Correct tool invoked with incorrect arguments.",
        example="Exchange item A→B instead of A→C",
    ),
    FailureSubcategory(
        category="action",
        name="missing_action",
        description="Failed to call a required tool or perform a necessary action.",
        example="Never confirmed the exchange",
    ),
    # state (2)
    FailureSubcategory(
        category="state",
        name="wrong_state",
        description="Database or environment left in an incorrect state after the run.",
        example="Order status wrong",
    ),
    FailureSubcategory(
        category="state",
        name="partial_state",
        description="Only some required state changes were applied; the rest were skipped.",
        example="Address changed, payment not",
    ),
    # communication (3)
    FailureSubcategory(
        category="communication",
        name="wrong_response",
        description="Incorrect information included in the agent's response.",
        example="Wrong order number quoted",
    ),
    FailureSubcategory(
        category="communication",
        name="missing_info",
        description="Required information was not communicated to the user.",
        example="Didn't tell user the refund amount",
    ),
    FailureSubcategory(
        category="communication",
        name="hallucination",
        description="Agent fabricated facts not grounded in available data or context.",
        example="Invented a policy that doesn't exist",
    ),
    # quality (5)
    FailureSubcategory(
        category="quality",
        name="shallow_output",
        description="Output is technically correct but lacks necessary depth or detail.",
        example="Report covers 2 of 8 relevant risk factors",
    ),
    FailureSubcategory(
        category="quality",
        name="suboptimal_approach",
        description="Task completed via an inefficient or unnecessarily roundabout path.",
        example="12 API calls when 3 would suffice",
    ),
    FailureSubcategory(
        category="quality",
        name="poor_tone",
        description="Content is correct but the register or professionalism is inappropriate.",
        example="Rude response that technically resolves issue",
    ),
    FailureSubcategory(
        category="quality",
        name="incomplete_analysis",
        description="Analysis misses relevant factors or provides only partial coverage.",
        example="M&A diligence skips regulatory risk entirely",
    ),
    FailureSubcategory(
        category="quality",
        name="low_confidence_output",
        description="Output is excessively hedged or ungrounded, undermining its utility.",
        example='"I think maybe the order might be..."',
    ),
    # process (4)
    FailureSubcategory(
        category="process",
        name="tool_loop",
        description="Agent repeated identical or near-identical tool calls unnecessarily.",
        example="Same API called 8 times",
    ),
    FailureSubcategory(
        category="process",
        name="infinite_delegation",
        description="Circular handoffs between agents with no progress toward resolution.",
        example="Agent A→B→A→B",
    ),
    FailureSubcategory(
        category="process",
        name="context_overflow",
        description="Agent exceeded its context window and lost information critical to the task.",
        example=None,
    ),
    FailureSubcategory(
        category="process",
        name="planning_failure",
        description="Agent executed an incoherent action sequence, including steps in the wrong order.",
        example="Steps in wrong order",
    ),
    # safety (3)
    FailureSubcategory(
        category="safety",
        name="permission_escalation",
        description="Agent accessed resources or capabilities beyond its authorization scope.",
        example=None,
    ),
    FailureSubcategory(
        category="safety",
        name="data_leakage",
        description="Agent exposed PII or other sensitive data across context boundaries.",
        example=None,
    ),
    FailureSubcategory(
        category="safety",
        name="policy_violation",
        description="Agent violated a stated operational policy or constraint.",
        example=None,
    ),
    # infrastructure (3)
    FailureSubcategory(
        category="infrastructure",
        name="timeout",
        description="Run exceeded the configured time limit before completing.",
        example=None,
    ),
    FailureSubcategory(
        category="infrastructure",
        name="error",
        description="A system or API error terminated the run prematurely.",
        example=None,
    ),
    FailureSubcategory(
        category="infrastructure",
        name="max_steps",
        description="Agent exceeded the maximum step limit without completing the task.",
        example=None,
    ),
]

# ---------------------------------------------------------------------------
# Public index structures
# ---------------------------------------------------------------------------

#: Maps category name → FailureCategory
_CATEGORY_INDEX: dict[str, FailureCategory] = {c.name: c for c in _CATEGORIES}

#: Maps "category.subcategory" → FailureSubcategory
_SUBCATEGORY_INDEX: dict[str, FailureSubcategory] = {
    f"{s.category}.{s.name}": s for s in _SUBCATEGORIES
}

#: Maps category name → list of its FailureSubcategory objects
TAXONOMY: dict[str, list[FailureSubcategory]] = {c.name: [] for c in _CATEGORIES}
for _sub in _SUBCATEGORIES:
    TAXONOMY[_sub.category].append(_sub)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def all_categories() -> list[FailureCategory]:
    """Return all top-level FailureCategory objects."""
    return list(_CATEGORIES)


def all_subcategories() -> list[FailureSubcategory]:
    """Return all FailureSubcategory objects across every category."""
    return list(_SUBCATEGORIES)


def get_category(name: str) -> FailureCategory:
    """Look up a FailureCategory by its short name.

    Raises KeyError if *name* is not a known category.
    """
    return _CATEGORY_INDEX[name]


def get_subcategory(dotted: str) -> FailureSubcategory:
    """Look up a FailureSubcategory by its dotted key (``"category.name"``).

    Raises KeyError if *dotted* is not a known subcategory key.
    """
    return _SUBCATEGORY_INDEX[dotted]


def validate_category_string(dotted: str) -> bool:
    """Return True iff *dotted* is a valid ``"category.subcategory"`` string."""
    if not dotted or "." not in dotted:
        return False
    return dotted in _SUBCATEGORY_INDEX
