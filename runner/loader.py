from __future__ import annotations

from pathlib import Path
from typing import Any

from runner.config import load_yaml_or_json
from runner.models import DbCheck, ExpectedResponse, JsonPathExpectation, Suite, TestCase
from runner.substitution import substitute


def resolve_suite_path(suite: str) -> Path:
    candidate = Path(suite)
    if candidate.exists():
        return candidate
    shorthand = Path("suites") / f"{suite}.yaml"
    if shorthand.exists():
        return shorthand
    shorthand_json = Path("suites") / f"{suite}.json"
    if shorthand_json.exists():
        return shorthand_json
    raise FileNotFoundError(f"Suite not found: {suite}. Tried direct path and suites/{suite}.yaml")


def load_suite(path: str | Path, variables: dict[str, Any] | None = None) -> Suite:
    raw = load_yaml_or_json(path)
    variables = variables or {}
    raw = substitute(raw, variables)
    cases = [_parse_case(item) for item in raw.get("cases", [])]
    if not cases:
        raise ValueError(f"Suite {path} has no cases")
    return Suite(
        name=str(raw.get("name", Path(path).stem)),
        version=str(raw.get("version", "1.0")),
        description=str(raw.get("description", "")),
        tags=list(raw.get("tags", [])),
        cases=cases,
    )


def _parse_expected(raw: dict[str, Any] | None) -> ExpectedResponse:
    raw = raw or {}
    return ExpectedResponse(
        status_code=raw.get("status_code"),
        headers=dict(raw.get("headers") or {}),
        json=dict(raw.get("json") or {}),
        json_paths=[JsonPathExpectation(**item) for item in raw.get("json_paths", [])],
        required_fields=list(raw.get("required_fields") or []),
    )


def _parse_db_checks(raw: list[dict[str, Any]] | None) -> list[DbCheck]:
    checks: list[DbCheck] = []
    for idx, item in enumerate(raw or []):
        checks.append(
            DbCheck(
                name=str(item.get("name", f"db_check_{idx + 1}")),
                query=str(item["query"]),
                params=dict(item.get("params") or {}),
                expect_one=item.get("expect_one"),
                expect_many_count=item.get("expect_many_count"),
                expect_empty=bool(item.get("expect_empty", False)),
            )
        )
    return checks


def _parse_case(raw: dict[str, Any]) -> TestCase:
    return TestCase(
        id=str(raw["id"]),
        name=str(raw.get("name", raw["id"])),
        method=str(raw.get("method", "GET")).upper(),
        path=str(raw["path"]),
        headers={str(k): str(v) for k, v in (raw.get("headers") or {}).items()},
        query=dict(raw.get("query") or {}),
        json=raw.get("json"),
        expected=_parse_expected(raw.get("expected")),
        db=_parse_db_checks(raw.get("db")),
        timeout_seconds=raw.get("timeout_seconds"),
        tags=list(raw.get("tags") or []),
    )
