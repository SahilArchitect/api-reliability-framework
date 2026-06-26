from runner.models import CheckResult, FailureType, TestCase, TestResult
from runner.reporting import build_defect_summary


def test_defect_summary_contains_actionable_fields():
    case = TestCase(id="c1", name="Case one", method="GET", path="/health")
    result = TestResult(
        case_id="c1",
        case_name="Case one",
        method="GET",
        path="/health",
        passed=False,
        duration_ms=10,
        failure_type=FailureType.VALIDATION_FAILURE,
        checks=[
            CheckResult(
                name="json:status",
                passed=False,
                message="Expected JSON field status='ok', observed 'down'",
                failure_type=FailureType.VALIDATION_FAILURE,
            )
        ],
    )
    summary = build_defect_summary(case, result)
    assert "Title:" in summary
    assert "Repro Steps:" in summary
    assert "VALIDATION_FAILURE" in summary
