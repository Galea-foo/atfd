"""Core Pydantic schema models for the ATFD benchmark.

Defines trajectories, findings, cost reports, quality assessments,
and all supporting enumerations used throughout the benchmark.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Outcome(str, Enum):
    """Overall outcome of a trajectory."""

    PASS = "pass"
    DEGRADED = "degraded"
    FAIL = "fail"


class Severity(str, Enum):
    """Severity level of a finding."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class EventType(str, Enum):
    """Type of event in a trajectory."""

    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SYSTEM = "system"


class Infrastructure(str, Enum):
    """Infrastructure tier used by a judge."""

    NONE = "none"
    API_KEY = "api_key"
    HOSTED_SERVICE = "hosted_service"
    GPU_REQUIRED = "gpu_required"


class Consensus(str, Enum):
    """Confidence level of the ground-truth label."""

    GOLD = "gold"
    MAJORITY = "majority"
    DISPUTED = "disputed"


class Source(str, Enum):
    """Dataset source for a trajectory."""

    TAU_BENCH = "tau-bench"
    SWE_BENCH = "swe-bench"
    SYNTHETIC = "synthetic"


# ---------------------------------------------------------------------------
# Trajectory models
# ---------------------------------------------------------------------------


class Event(BaseModel):
    """A single event within an agent trajectory."""

    type: EventType
    timestamp: str
    content: str
    metadata: dict = Field(default_factory=dict)


class SourceLabel(BaseModel):
    """Label contributed by a single human annotator or automated source."""

    outcome: Outcome
    failure_categories: list[str] = Field(default_factory=list)
    quality_categories: list[str] = Field(default_factory=list)
    reasoning: str = ""


class GroundTruth(BaseModel):
    """Aggregated ground-truth label for a trajectory."""

    outcome: Outcome
    failure_categories: list[str] = Field(default_factory=list)
    quality_categories: list[str] = Field(default_factory=list)
    source_labels: dict[str, SourceLabel] = Field(default_factory=dict)
    consensus: Consensus


class Trajectory(BaseModel):
    """A complete agent trajectory with events and ground-truth labels."""

    trajectory_id: str
    source: Source
    domain: str
    events: list[Event] = Field(default_factory=list)
    ground_truth: GroundTruth
    task_description: str = ""


# ---------------------------------------------------------------------------
# Judge output models
# ---------------------------------------------------------------------------


class Finding(BaseModel):
    """A single finding produced by a judge."""

    severity: Severity
    category: str
    description: str
    attribution: Optional[str] = None


class CostReport(BaseModel):
    """Resource costs incurred by a judge while processing a trajectory."""

    dollar_cost: float
    latency_seconds: float
    total_tokens: int
    api_calls: int
    infrastructure: Infrastructure


class JudgeOutput(BaseModel):
    """Full output from a judge for a single trajectory."""

    trajectory_id: str
    has_failure: bool
    findings: list[Finding] = Field(default_factory=list)
    cost: CostReport


# ---------------------------------------------------------------------------
# Quality assessment models
# ---------------------------------------------------------------------------


class QualityDimension(BaseModel):
    """Score on a single quality dimension (0–2 scale)."""

    score: int = Field(ge=0, le=2)
    explanation: str


class QualityAssessment(BaseModel):
    """Multi-dimensional quality assessment for a trajectory."""

    dimensions: dict[str, QualityDimension] = Field(default_factory=dict)
    quality_categories: list[str] = Field(default_factory=list)
    overall_quality: Outcome
    reasoning: str = ""
