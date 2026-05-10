"""Metrics module for the ATFD benchmark.

Provides detection rate, false positive rate, F1, Wilson CI, bootstrap CI,
McNemar's test, Fleiss' kappa, category alignment, and cost summary.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
from scipy.stats import chi2

from atfd.schema import JudgeOutput, Outcome, Severity


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class MetricResult:
    """A metric value with optional confidence interval and sample count."""

    value: Optional[float]
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    n: int = 0


@dataclass
class BenchmarkResults:
    """Aggregated benchmark results for a single system."""

    system_name: str
    detection: MetricResult
    quality_detection: MetricResult
    fpr: MetricResult
    f1: float
    alignment: dict = field(default_factory=dict)
    cost: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_error_or_warning(output: JudgeOutput) -> bool:
    """Return True if the output contains at least one error or warning finding."""
    return any(
        f.severity in (Severity.ERROR, Severity.WARNING) for f in output.findings
    )


def _has_error(output: JudgeOutput) -> bool:
    """Return True if the output contains at least one error-severity finding."""
    return any(f.severity == Severity.ERROR for f in output.findings)


def _has_quality_finding(output: JudgeOutput) -> bool:
    """Return True if the output contains a quality.* category finding."""
    return any(f.category.startswith("quality.") for f in output.findings)


# ---------------------------------------------------------------------------
# Confidence intervals
# ---------------------------------------------------------------------------


def wilson_ci(
    successes: int,
    trials: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Compute the Wilson score confidence interval for a proportion.

    Parameters
    ----------
    successes:
        Number of successes.
    trials:
        Total number of trials.
    confidence:
        Confidence level (default 0.95).

    Returns
    -------
    (lo, hi) tuple clamped to [0, 1].
    """
    if trials == 0:
        return (0.0, 1.0)

    alpha = 1.0 - confidence
    # Two-tailed z for the given confidence level
    from scipy.stats import norm
    z = norm.ppf(1.0 - alpha / 2.0)

    p_hat = successes / trials
    n = trials

    centre = (p_hat + z * z / (2 * n)) / (1 + z * z / n)
    margin = (z / (1 + z * z / n)) * math.sqrt(
        p_hat * (1 - p_hat) / n + z * z / (4 * n * n)
    )

    lo = max(0.0, centre - margin)
    hi = min(1.0, centre + margin)
    # Clamp floating-point edge cases to exact 0/1 when appropriate
    if successes == 0:
        lo = 0.0
    if successes == trials:
        hi = 1.0
    return (lo, hi)


def bootstrap_ci(
    data: list,
    stat_fn: Callable[[list], float],
    n_resamples: int = 10_000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Compute a bootstrap confidence interval for an arbitrary statistic.

    Parameters
    ----------
    data:
        Sample data.
    stat_fn:
        Function that takes a list and returns a scalar statistic.
    n_resamples:
        Number of bootstrap resamples.
    confidence:
        Confidence level (default 0.95).
    seed:
        Random seed for reproducibility.

    Returns
    -------
    (lo, hi) tuple.
    """
    rng = np.random.default_rng(seed)
    arr = np.array(data)
    n = len(arr)
    boot_stats = np.empty(n_resamples)
    for i in range(n_resamples):
        sample = arr[rng.integers(0, n, size=n)]
        boot_stats[i] = stat_fn(sample.tolist())

    alpha = 1.0 - confidence
    lo = float(np.percentile(boot_stats, 100 * alpha / 2))
    hi = float(np.percentile(boot_stats, 100 * (1 - alpha / 2)))
    return (lo, hi)


# ---------------------------------------------------------------------------
# Core detection metrics
# ---------------------------------------------------------------------------


def detection_rate(
    gt_outcomes: list[Outcome],
    outputs: list[JudgeOutput],
) -> MetricResult:
    """Compute Detection Rate (DR): recall on FAIL trajectories.

    A trajectory is considered detected if the judge produced at least one
    error or warning finding.

    Parameters
    ----------
    gt_outcomes:
        Ground-truth outcome for each trajectory, aligned with *outputs*.
    outputs:
        Judge outputs, one per trajectory.

    Returns
    -------
    MetricResult with value=None when there are no failure trajectories.
    """
    assert len(gt_outcomes) == len(outputs), "gt_outcomes and outputs must be the same length"

    fail_indices = [i for i, o in enumerate(gt_outcomes) if o == Outcome.FAIL]
    n = len(fail_indices)

    if n == 0:
        return MetricResult(value=None, n=0)

    successes = sum(1 for i in fail_indices if _has_error_or_warning(outputs[i]))
    rate = successes / n
    lo, hi = wilson_ci(successes, n)
    return MetricResult(value=rate, ci_low=lo, ci_high=hi, n=n)


def quality_detection_rate(
    gt_outcomes: list[Outcome],
    outputs: list[JudgeOutput],
) -> MetricResult:
    """Compute Quality Detection Rate (QDR): recall on DEGRADED trajectories.

    A trajectory is considered detected if the judge produced at least one
    finding with a category starting with ``quality.``.

    Parameters
    ----------
    gt_outcomes:
        Ground-truth outcome for each trajectory, aligned with *outputs*.
    outputs:
        Judge outputs, one per trajectory.

    Returns
    -------
    MetricResult with value=None when there are no degraded trajectories.
    """
    assert len(gt_outcomes) == len(outputs)

    degraded_indices = [i for i, o in enumerate(gt_outcomes) if o == Outcome.DEGRADED]
    n = len(degraded_indices)

    if n == 0:
        return MetricResult(value=None, n=0)

    successes = sum(1 for i in degraded_indices if _has_quality_finding(outputs[i]))
    rate = successes / n
    lo, hi = wilson_ci(successes, n)
    return MetricResult(value=rate, ci_low=lo, ci_high=hi, n=n)


def false_positive_rate(
    gt_outcomes: list[Outcome],
    outputs: list[JudgeOutput],
) -> MetricResult:
    """Compute False Positive Rate (FPR): error alerts on PASS trajectories.

    A false positive is a PASS trajectory for which the judge raised at least
    one error-severity finding.

    Parameters
    ----------
    gt_outcomes:
        Ground-truth outcome for each trajectory.
    outputs:
        Judge outputs, aligned with *gt_outcomes*.

    Returns
    -------
    MetricResult with value=None when there are no pass trajectories.
    """
    assert len(gt_outcomes) == len(outputs)

    pass_indices = [i for i, o in enumerate(gt_outcomes) if o == Outcome.PASS]
    n = len(pass_indices)

    if n == 0:
        return MetricResult(value=None, n=0)

    false_positives = sum(1 for i in pass_indices if _has_error(outputs[i]))
    rate = false_positives / n
    lo, hi = wilson_ci(false_positives, n)
    return MetricResult(value=rate, ci_low=lo, ci_high=hi, n=n)


def f1_score(
    gt_outcomes: list[Outcome],
    outputs: list[JudgeOutput],
) -> float:
    """Compute the F1 score for binary failure detection.

    Treats FAIL as positive and PASS/DEGRADED as negative.  A judge
    prediction is positive when ``has_failure`` is True.

    Parameters
    ----------
    gt_outcomes:
        Ground-truth outcomes.
    outputs:
        Judge outputs.

    Returns
    -------
    F1 score in [0, 1], or 0.0 when precision + recall == 0.
    """
    assert len(gt_outcomes) == len(outputs)

    tp = fp = fn = 0
    for gt, out in zip(gt_outcomes, outputs):
        predicted_positive = out.has_failure
        actual_positive = gt == Outcome.FAIL
        if predicted_positive and actual_positive:
            tp += 1
        elif predicted_positive and not actual_positive:
            fp += 1
        elif not predicted_positive and actual_positive:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    denom = precision + recall
    return (2 * precision * recall / denom) if denom > 0 else 0.0


# ---------------------------------------------------------------------------
# Statistical tests
# ---------------------------------------------------------------------------


def mcnemar_test(
    system_a_correct: list[bool],
    system_b_correct: list[bool],
) -> tuple[float, float]:
    """McNemar's test with continuity correction for paired binary data.

    Tests whether two systems have significantly different error rates.

    Parameters
    ----------
    system_a_correct:
        Boolean vector — True when system A is correct on each sample.
    system_b_correct:
        Boolean vector — True when system B is correct on each sample.

    Returns
    -------
    (statistic, p_value) where statistic is the chi-squared value and
    p_value is the two-tailed p-value.
    """
    assert len(system_a_correct) == len(system_b_correct)

    # b = A correct, B wrong; c = A wrong, B correct
    b = sum(1 for a, bv in zip(system_a_correct, system_b_correct) if a and not bv)
    c = sum(1 for a, bv in zip(system_a_correct, system_b_correct) if not a and bv)

    # McNemar with continuity correction
    if b + c == 0:
        return (0.0, 1.0)

    stat = (abs(b - c) - 1) ** 2 / (b + c)
    p_value = float(chi2.sf(stat, df=1))
    return (float(stat), p_value)


def fleiss_kappa(ratings: list[list[str]]) -> float:
    """Compute Fleiss' kappa for inter-rater agreement.

    Parameters
    ----------
    ratings:
        A list of N items, each a list of K rater labels (strings).
        All inner lists must have the same length.

    Returns
    -------
    Fleiss' kappa in (-inf, 1].
    """
    n_items = len(ratings)
    n_raters = len(ratings[0])

    # Collect all unique categories
    categories = sorted({label for row in ratings for label in row})
    n_cats = len(categories)
    cat_idx = {c: i for i, c in enumerate(categories)}

    # Build count matrix (n_items x n_cats)
    counts = np.zeros((n_items, n_cats), dtype=float)
    for i, row in enumerate(ratings):
        for label in row:
            counts[i, cat_idx[label]] += 1

    # Proportion of rater pairs agreeing per item: P_i
    P_i = np.zeros(n_items)
    for i in range(n_items):
        agree = sum(counts[i, j] * (counts[i, j] - 1) for j in range(n_cats))
        P_i[i] = agree / (n_raters * (n_raters - 1))

    P_bar = float(np.mean(P_i))

    # Marginal proportions p_j
    p_j = counts.sum(axis=0) / (n_items * n_raters)

    # Expected agreement P_e
    P_e = float(np.sum(p_j ** 2))

    if P_e == 1.0:
        return 1.0

    kappa = (P_bar - P_e) / (1.0 - P_e)
    return float(kappa)


# ---------------------------------------------------------------------------
# Category alignment
# ---------------------------------------------------------------------------


def category_alignment(
    gt_categories: list[list[str]],
    predicted_categories: list[list[str]],
) -> dict:
    """Compute per-category precision, recall, F1, and macro-F1.

    Each item is treated as a multi-label classification problem.

    Parameters
    ----------
    gt_categories:
        Ground-truth category lists, one per trajectory.
    predicted_categories:
        Predicted category lists, one per trajectory.

    Returns
    -------
    dict with keys ``macro_f1`` and ``per_category`` (a dict of
    category -> {precision, recall, f1}).
    """
    assert len(gt_categories) == len(predicted_categories)

    # Gather all categories
    all_cats = sorted(
        {cat for cats in gt_categories + predicted_categories for cat in cats}
    )

    per_category: dict[str, dict[str, float]] = {}
    for cat in all_cats:
        tp = fp = fn = 0
        for gt_cats, pred_cats in zip(gt_categories, predicted_categories):
            in_gt = cat in gt_cats
            in_pred = cat in pred_cats
            if in_gt and in_pred:
                tp += 1
            elif not in_gt and in_pred:
                fp += 1
            elif in_gt and not in_pred:
                fn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        denom = precision + recall
        f1 = (2 * precision * recall / denom) if denom > 0 else 0.0
        per_category[cat] = {"precision": precision, "recall": recall, "f1": f1}

    macro_f1 = (
        float(np.mean([v["f1"] for v in per_category.values()]))
        if per_category
        else 0.0
    )

    return {"macro_f1": macro_f1, "per_category": per_category}


# ---------------------------------------------------------------------------
# Cost summary
# ---------------------------------------------------------------------------


def cost_summary(outputs: list[JudgeOutput]) -> dict:
    """Compute cost statistics across a set of judge outputs.

    Parameters
    ----------
    outputs:
        List of JudgeOutput objects.

    Returns
    -------
    dict with keys:
        - ``mean_dollar_cost``
        - ``total_dollar_cost``
        - ``p50_latency_seconds``
        - ``p95_latency_seconds``
        - ``mean_total_tokens``
    """
    if not outputs:
        return {
            "mean_dollar_cost": 0.0,
            "total_dollar_cost": 0.0,
            "p50_latency_seconds": 0.0,
            "p95_latency_seconds": 0.0,
            "mean_total_tokens": 0.0,
        }

    dollars = np.array([o.cost.dollar_cost for o in outputs])
    latencies = np.array([o.cost.latency_seconds for o in outputs])
    tokens = np.array([o.cost.total_tokens for o in outputs])

    return {
        "mean_dollar_cost": float(np.mean(dollars)),
        "total_dollar_cost": round(float(np.sum(dollars)), 10),
        "p50_latency_seconds": float(np.percentile(latencies, 50)),
        "p95_latency_seconds": float(np.percentile(latencies, 95)),
        "mean_total_tokens": float(np.mean(tokens)),
    }
