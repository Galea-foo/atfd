import math
from atfd.metrics import (
    detection_rate,
    quality_detection_rate,
    false_positive_rate,
    f1_score,
    wilson_ci,
    bootstrap_ci,
    mcnemar_test,
    fleiss_kappa,
    category_alignment,
    cost_summary,
    BenchmarkResults,
)
from atfd.schema import CostReport, Finding, JudgeOutput, Outcome


def _jo(tid, has_failure, findings=None, dollar=0.0):
    return JudgeOutput(
        trajectory_id=tid, has_failure=has_failure, findings=findings or [],
        cost=CostReport(dollar_cost=dollar, latency_seconds=0.1, total_tokens=0, api_calls=0, infrastructure="none"),
    )

def _finding(sev="error", cat="action.wrong_tool"):
    return Finding(severity=sev, category=cat, description="test")


def test_detection_rate_perfect():
    gt = [Outcome.FAIL, Outcome.FAIL, Outcome.PASS]
    outputs = [_jo("t1", True, [_finding()]), _jo("t2", True, [_finding()]), _jo("t3", False)]
    rate = detection_rate(gt, outputs)
    assert rate.value == 1.0

def test_detection_rate_partial():
    gt = [Outcome.FAIL, Outcome.FAIL, Outcome.PASS]
    outputs = [_jo("t1", True, [_finding()]), _jo("t2", False), _jo("t3", False)]
    rate = detection_rate(gt, outputs)
    assert rate.value == 0.5

def test_detection_rate_no_failures():
    gt = [Outcome.PASS, Outcome.PASS]
    outputs = [_jo("t1", False), _jo("t2", False)]
    rate = detection_rate(gt, outputs)
    assert rate.value is None

def test_false_positive_rate_zero():
    gt = [Outcome.FAIL, Outcome.PASS, Outcome.PASS]
    outputs = [_jo("t1", True, [_finding()]), _jo("t2", False), _jo("t3", False)]
    rate = false_positive_rate(gt, outputs)
    assert rate.value == 0.0

def test_false_positive_rate_nonzero():
    gt = [Outcome.PASS, Outcome.PASS]
    outputs = [_jo("t1", True, [_finding("error")]), _jo("t2", False)]
    rate = false_positive_rate(gt, outputs)
    assert rate.value == 0.5

def test_f1_score_perfect():
    gt = [Outcome.FAIL, Outcome.PASS]
    outputs = [_jo("t1", True, [_finding()]), _jo("t2", False)]
    f1 = f1_score(gt, outputs)
    assert f1 == 1.0

def test_wilson_ci_basic():
    lo, hi = wilson_ci(successes=8, trials=10, confidence=0.95)
    assert 0.4 < lo < 0.8
    assert 0.85 < hi < 1.0

def test_wilson_ci_zero():
    lo, hi = wilson_ci(successes=0, trials=10, confidence=0.95)
    assert lo == 0.0
    assert hi > 0.0

def test_wilson_ci_all():
    lo, hi = wilson_ci(successes=10, trials=10, confidence=0.95)
    assert lo < 1.0
    assert hi == 1.0

def test_bootstrap_ci_returns_tuple():
    data = [0.8, 0.9, 0.7, 0.85, 0.95, 0.6, 0.75, 0.88, 0.92, 0.81]
    lo, hi = bootstrap_ci(data, stat_fn=lambda x: sum(x)/len(x), n_resamples=1000)
    assert lo < hi
    assert 0.5 < lo < 0.9
    assert 0.75 < hi < 1.0

def test_mcnemar_returns_pvalue():
    system_a = [True]*8 + [False, False]
    system_b = [True]*7 + [False, True, False]
    stat, p = mcnemar_test(system_a, system_b)
    assert 0.0 <= p <= 1.0

def test_fleiss_kappa_perfect_agreement():
    ratings = [["fail","fail","fail"], ["fail","fail","fail"], ["pass","pass","pass"], ["pass","pass","pass"], ["fail","fail","fail"]]
    kappa = fleiss_kappa(ratings)
    assert kappa == 1.0

def test_fleiss_kappa_no_agreement():
    ratings = [["pass","fail","degraded"], ["fail","degraded","pass"], ["degraded","pass","fail"]]
    kappa = fleiss_kappa(ratings)
    assert kappa < 0.1

def test_cost_summary():
    outputs = [_jo("t1", True, [_finding()], dollar=0.04), _jo("t2", True, [_finding()], dollar=0.06), _jo("t3", False, [], dollar=0.02)]
    summary = cost_summary(outputs)
    assert abs(summary["mean_dollar_cost"] - 0.04) < 0.001
    assert summary["total_dollar_cost"] == 0.12

def test_category_alignment():
    gt_cats = [["action.wrong_tool"], ["state.wrong_state"], ["process.tool_loop"]]
    pred_cats = [["action.wrong_tool"], ["action.wrong_args"], ["process.tool_loop"]]
    result = category_alignment(gt_cats, pred_cats)
    assert "macro_f1" in result
    assert "per_category" in result
    assert 0.0 <= result["macro_f1"] <= 1.0
