from __future__ import annotations

from decimal import Decimal
from typing import Any

from runner.classifier import classify_error
from runner.db import run_db_check
from runner.jsonpath import JsonPathError, get_json_path
from runner.models import ApiResult, CheckResult, DbCheck, EnvConfig, ExpectedResponse, FailureType


def validate_response(expected: ExpectedResponse, api: ApiResult) -> list[CheckResult]:
    checks: list[CheckResult] = []

    if api.error:
        failure_type = classify_error(api.error, api.status_code)
        checks.append(
            CheckResult(
                name="api_request",
                passed=False,
                message=api.error,
                failure_type=failure_type,
                observed=api.error,
            )
        )
        return checks

    if expected.status_code is not None:
        passed = api.status_code == expected.status_code
        msg = f"Expected status {expected.status_code}, observed {api.status_code}"
        checks.append(
            CheckResult(
                name="status_code",
                passed=passed,
                message="Status code matched" if passed else msg,
                failure_type=None if passed else classify_error(msg, api.status_code),
                expected=expected.status_code,
                observed=api.status_code,
            )
        )

    body = api.body
    for header_name, expected_value in expected.headers.items():
        observed = api.headers.get(header_name.lower()) or api.headers.get(header_name)
        passed = observed == expected_value
        msg = f"Expected header {header_name}={expected_value!r}, observed {observed!r}"
        checks.append(
            CheckResult(
                name=f"header:{header_name}",
                passed=passed,
                message="Header matched" if passed else msg,
                failure_type=None if passed else FailureType.VALIDATION_FAILURE,
                expected=expected_value,
                observed=observed,
            )
        )

    if expected.json:
        if not isinstance(body, dict):
            checks.append(
                CheckResult(
                    name="json_body",
                    passed=False,
                    message="Expected JSON object response body",
                    failure_type=FailureType.VALIDATION_FAILURE,
                    expected="object",
                    observed=body,
                )
            )
        else:
            for key, expected_value in expected.json.items():
                observed = body.get(key)
                passed = _normalize(observed) == _normalize(expected_value)
                msg = f"Expected JSON field {key}={expected_value!r}, observed {observed!r}"
                checks.append(
                    CheckResult(
                        name=f"json:{key}",
                        passed=passed,
                        message="JSON field matched" if passed else msg,
                        failure_type=None if passed else FailureType.VALIDATION_FAILURE,
                        expected=expected_value,
                        observed=observed,
                    )
                )

    for field in expected.required_fields:
        passed = isinstance(body, dict) and field in body
        msg = f"Required field missing: {field}"
        checks.append(
            CheckResult(
                name=f"required_field:{field}",
                passed=passed,
                message="Required field present" if passed else msg,
                failure_type=None if passed else FailureType.VALIDATION_FAILURE,
                expected="present",
                observed="present" if passed else "missing",
            )
        )

    for item in expected.json_paths:
        try:
            observed = get_json_path(body, item.path)
            if item.exists is not None:
                passed = bool(item.exists)
                msg = f"Path {item.path} exists"
            elif item.equals is not None:
                passed = _normalize(observed) == _normalize(item.equals)
                msg = f"Expected {item.path}={item.equals!r}, observed {observed!r}"
            else:
                passed = True
                msg = f"Path {item.path} exists"
        except JsonPathError as exc:
            observed = None
            passed = False
            msg = str(exc)
        checks.append(
            CheckResult(
                name=f"json_path:{item.path}",
                passed=passed,
                message="JSON path matched" if passed else msg,
                failure_type=None if passed else FailureType.VALIDATION_FAILURE,
                expected=item.equals if item.equals is not None else "exists",
                observed=observed,
            )
        )

    return checks


def validate_database(env: EnvConfig, db_checks: list[DbCheck]) -> list[CheckResult]:
    results: list[CheckResult] = []
    if not db_checks:
        return results
    if not env.database_url:
        return [
            CheckResult(
                name="database_config",
                passed=False,
                message="database_url missing in environment config",
                failure_type=FailureType.DB_MISMATCH,
            )
        ]

    for check in db_checks:
        try:
            rows = run_db_check(env.database_url, check)
            results.extend(_validate_db_rows(check, rows))
        except Exception as exc:  # noqa: BLE001 - report framework must capture DB failures clearly
            results.append(
                CheckResult(
                    name=f"db:{check.name}",
                    passed=False,
                    message=f"Database check failed: {exc}",
                    failure_type=FailureType.DB_MISMATCH,
                    observed=str(exc),
                )
            )
    return results


def _validate_db_rows(check: DbCheck, rows: list[dict[str, Any]]) -> list[CheckResult]:
    results: list[CheckResult] = []
    if check.expect_empty:
        passed = len(rows) == 0
        results.append(
            CheckResult(
                name=f"db:{check.name}",
                passed=passed,
                message="No rows returned" if passed else f"Expected no rows, observed {len(rows)} rows",
                failure_type=None if passed else FailureType.DB_MISMATCH,
                expected=0,
                observed=len(rows),
            )
        )
        return results

    if check.expect_many_count is not None:
        passed = len(rows) == check.expect_many_count
        results.append(
            CheckResult(
                name=f"db:{check.name}:count",
                passed=passed,
                message="Row count matched" if passed else f"Expected {check.expect_many_count} rows, observed {len(rows)}",
                failure_type=None if passed else FailureType.DB_MISMATCH,
                expected=check.expect_many_count,
                observed=len(rows),
            )
        )

    if check.expect_one is not None:
        if len(rows) != 1:
            results.append(
                CheckResult(
                    name=f"db:{check.name}",
                    passed=False,
                    message=f"Expected exactly one row, observed {len(rows)}",
                    failure_type=FailureType.DB_MISMATCH,
                    expected=1,
                    observed=len(rows),
                )
            )
            return results
        row = rows[0]
        for column, expected_value in check.expect_one.items():
            observed = row.get(column)
            passed = _normalize(observed) == _normalize(expected_value)
            results.append(
                CheckResult(
                    name=f"db:{check.name}:{column}",
                    passed=passed,
                    message="DB value matched" if passed else f"Expected DB column {column}={expected_value!r}, observed {observed!r}",
                    failure_type=None if passed else FailureType.DB_MISMATCH,
                    expected=expected_value,
                    observed=observed,
                )
            )
    return results


def _normalize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, float):
        return round(value, 6)
    return value
