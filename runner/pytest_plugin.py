from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from runner.config import load_env_config
from runner.loader import load_suite
from runner.reporting import write_reports


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("api-reliability-framework")
    group.addoption("--arf-suite", action="store", help="Path to YAML/JSON API test suite")
    group.addoption("--arf-env", action="store", default="configs/env.local.yaml", help="Path to environment config")
    group.addoption("--arf-report-dir", action="store", default="reports", help="Directory for JSON/HTML reports")


def pytest_configure(config: pytest.Config) -> None:
    config._arf_results = []  # type: ignore[attr-defined]
    config._arf_suite = None  # type: ignore[attr-defined]
    config._arf_env = None  # type: ignore[attr-defined]


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "arf_case" not in metafunc.fixturenames:
        return
    suite_path = metafunc.config.getoption("--arf-suite")
    env_path = metafunc.config.getoption("--arf-env")
    if not suite_path:
        raise pytest.UsageError("--arf-suite is required")
    env = load_env_config(env_path)
    suite = load_suite(suite_path, env.variables)
    metafunc.config._arf_suite = suite  # type: ignore[attr-defined]
    metafunc.config._arf_env = env  # type: ignore[attr-defined]
    metafunc.parametrize("arf_case", suite.cases, ids=[case.id for case in suite.cases])


@pytest.fixture(scope="session")
def arf_env(request: pytest.FixtureRequest) -> Any:
    env = getattr(request.config, "_arf_env", None)
    if env is None:
        env = load_env_config(request.config.getoption("--arf-env"))
        request.config._arf_env = env  # type: ignore[attr-defined]
    return env


@pytest.fixture(scope="session")
def arf_result_store(request: pytest.FixtureRequest) -> list[Any]:
    return request.config._arf_results  # type: ignore[attr-defined]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:  # noqa: ARG001
    suite = getattr(session.config, "_arf_suite", None)
    results = getattr(session.config, "_arf_results", [])
    if not suite or not results:
        return
    report_dir = Path(session.config.getoption("--arf-report-dir"))
    write_reports(suite, results, report_dir)
