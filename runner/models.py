from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class FailureType(StrEnum):
    API_FAILURE = "API_FAILURE"
    DB_MISMATCH = "DB_MISMATCH"
    TIMEOUT = "TIMEOUT"
    VALIDATION_FAILURE = "VALIDATION_FAILURE"
    AUTH_FAILURE = "AUTH_FAILURE"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


@dataclass(slots=True)
class RetryConfig:
    attempts: int = 1
    backoff_seconds: float = 0.0


@dataclass(slots=True)
class EnvConfig:
    base_url: str
    database_url: str | None = None
    timeout_seconds: float = 5.0
    retry: RetryConfig = field(default_factory=RetryConfig)
    headers: dict[str, str] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class JsonPathExpectation:
    path: str
    equals: Any | None = None
    exists: bool | None = None


@dataclass(slots=True)
class ExpectedResponse:
    status_code: int | None = None
    headers: dict[str, Any] = field(default_factory=dict)
    json: dict[str, Any] = field(default_factory=dict)
    json_paths: list[JsonPathExpectation] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DbCheck:
    name: str
    query: str
    params: dict[str, Any] = field(default_factory=dict)
    expect_one: dict[str, Any] | None = None
    expect_many_count: int | None = None
    expect_empty: bool = False


@dataclass(slots=True)
class TestCase:
    id: str
    name: str
    method: str
    path: str
    headers: dict[str, str] = field(default_factory=dict)
    query: dict[str, Any] = field(default_factory=dict)
    json: dict[str, Any] | None = None
    expected: ExpectedResponse = field(default_factory=ExpectedResponse)
    db: list[DbCheck] = field(default_factory=list)
    timeout_seconds: float | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Suite:
    name: str
    version: str
    description: str
    tags: list[str]
    cases: list[TestCase]


@dataclass(slots=True)
class CheckResult:
    name: str
    passed: bool
    message: str
    failure_type: FailureType | None = None
    expected: Any | None = None
    observed: Any | None = None


@dataclass(slots=True)
class ApiResult:
    status_code: int | None
    elapsed_ms: float
    body: Any | None
    headers: dict[str, str]
    error: str | None = None


@dataclass(slots=True)
class TestResult:
    case_id: str
    case_name: str
    method: str
    path: str
    passed: bool
    duration_ms: float
    failure_type: FailureType | None
    checks: list[CheckResult]
    api: ApiResult | None = None
    defect_summary: str | None = None

# Prevent pytest from mistaking framework data models for test classes when imported in tests.
TestCase.__test__ = False
TestResult.__test__ = False
