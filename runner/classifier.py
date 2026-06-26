from __future__ import annotations

from runner.models import CheckResult, FailureType


def classify_error(message: str, status_code: int | None = None, check_name: str | None = None) -> FailureType:
    normalized = message.lower()
    check = (check_name or "").lower()

    if "timeout" in normalized or "timed out" in normalized or "readtimeout" in normalized:
        return FailureType.TIMEOUT
    if status_code in {401, 403} or "unauthorized" in normalized or "forbidden" in normalized:
        return FailureType.AUTH_FAILURE
    if "db" in check or "database" in normalized or "query" in normalized or "row" in normalized:
        return FailureType.DB_MISMATCH
    if "expected" in normalized or "json" in normalized or "header" in normalized or "required field" in normalized:
        return FailureType.VALIDATION_FAILURE
    if status_code is not None and status_code >= 500:
        return FailureType.API_FAILURE
    if "connection" in normalized or "network" in normalized or "request" in normalized:
        return FailureType.API_FAILURE
    return FailureType.UNKNOWN_FAILURE


def dominant_failure_type(checks: list[CheckResult]) -> FailureType | None:
    failures = [check.failure_type for check in checks if not check.passed and check.failure_type]
    if not failures:
        return None
    priority = [
        FailureType.TIMEOUT,
        FailureType.AUTH_FAILURE,
        FailureType.DB_MISMATCH,
        FailureType.API_FAILURE,
        FailureType.VALIDATION_FAILURE,
        FailureType.UNKNOWN_FAILURE,
    ]
    for item in priority:
        if item in failures:
            return item
    return failures[0]
