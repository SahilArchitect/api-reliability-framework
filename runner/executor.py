from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from runner.classifier import dominant_failure_type
from runner.models import ApiResult, CheckResult, EnvConfig, TestCase, TestResult
from runner.reporting import build_defect_summary
from runner.validators import validate_database, validate_response

logger = logging.getLogger(__name__)


def execute_case(case: TestCase, env: EnvConfig) -> TestResult:
    started = time.perf_counter()
    logger.info("starting test case", extra={"case_id": case.id, "method": case.method, "path": case.path})
    api = _execute_request(case, env)
    checks: list[CheckResult] = []
    checks.extend(validate_response(case.expected, api))

    if not api.error and all(check.passed for check in checks):
        checks.extend(validate_database(env, case.db))

    passed = all(check.passed for check in checks)
    failure_type = dominant_failure_type(checks)
    duration_ms = (time.perf_counter() - started) * 1000
    result = TestResult(
        case_id=case.id,
        case_name=case.name,
        method=case.method,
        path=case.path,
        passed=passed,
        duration_ms=round(duration_ms, 2),
        failure_type=failure_type,
        checks=checks,
        api=api,
    )
    if not passed:
        result.defect_summary = build_defect_summary(case, result)
    logger.info(
        "finished test case",
        extra={
            "case_id": case.id,
            "method": case.method,
            "path": case.path,
            "duration_ms": result.duration_ms,
            "failure_type": result.failure_type.value if result.failure_type else None,
        },
    )
    return result


def _execute_request(case: TestCase, env: EnvConfig) -> ApiResult:
    url = f"{env.base_url}{case.path}"
    headers = {**env.headers, **case.headers}
    timeout_seconds = float(case.timeout_seconds or env.timeout_seconds)
    attempts = max(1, env.retry.attempts)
    last_error: str | None = None
    started = time.perf_counter()

    for attempt in range(1, attempts + 1):
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.request(
                    case.method,
                    url,
                    headers=headers,
                    params=case.query,
                    json=case.json,
                )
            elapsed_ms = response.elapsed.total_seconds() * 1000
            try:
                body: Any = response.json()
            except ValueError:
                body = response.text
            logger.info("api response received", extra={"case_id": case.id, "method": case.method, "path": case.path, "status_code": response.status_code})
            return ApiResult(
                status_code=response.status_code,
                elapsed_ms=round(elapsed_ms, 2),
                body=body,
                headers={str(k).lower(): str(v) for k, v in response.headers.items()},
            )
        except httpx.TimeoutException as exc:
            last_error = f"Request timeout after {timeout_seconds}s on attempt {attempt}: {exc}"
        except httpx.RequestError as exc:
            last_error = f"API request failed on attempt {attempt}: {exc}"

        if attempt < attempts and env.retry.backoff_seconds > 0:
            time.sleep(env.retry.backoff_seconds)

    elapsed_ms = (time.perf_counter() - started) * 1000
    return ApiResult(
        status_code=None,
        elapsed_ms=round(elapsed_ms, 2),
        body=None,
        headers={},
        error=last_error or "API request failed",
    )
