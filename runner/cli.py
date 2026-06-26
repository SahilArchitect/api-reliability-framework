from __future__ import annotations

import argparse
from pathlib import Path

import pytest
from rich.console import Console
from rich.table import Table

from runner.config import load_env_config
from runner.loader import load_suite, resolve_suite_path
from runner.logging_config import configure_logging

console = Console()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m runner", description="API reliability test runner")
    subcommands = parser.add_subparsers(dest="command", required=True)

    run_parser = subcommands.add_parser("run", help="Run an API test suite")
    run_parser.add_argument("--suite", required=True, help="Suite name or path, for example smoke or suites/smoke.yaml")
    run_parser.add_argument("--env", default="configs/env.local.yaml", help="Environment config path")
    run_parser.add_argument("--reports-dir", default="reports", help="Report output directory")
    run_parser.add_argument("--verbose", action="store_true", help="Show verbose pytest output")

    list_parser = subcommands.add_parser("list-suites", help="List available suites")
    list_parser.add_argument("--suites-dir", default="suites")

    validate_parser = subcommands.add_parser("validate-suite", help="Validate suite syntax")
    validate_parser.add_argument("--suite", required=True)
    validate_parser.add_argument("--env", default="configs/env.local.yaml")

    args = parser.parse_args(argv)

    if args.command == "run":
        return _run(args.suite, args.env, args.reports_dir, args.verbose)
    if args.command == "list-suites":
        return _list_suites(args.suites_dir)
    if args.command == "validate-suite":
        return _validate_suite(args.suite, args.env)
    return 2


def _run(suite: str, env_path: str, reports_dir: str, verbose: bool) -> int:
    suite_path = resolve_suite_path(suite)
    log_path = configure_logging(reports_dir)
    console.print(f"[bold]Running suite:[/bold] {suite_path}")
    console.print(f"[bold]Environment:[/bold] {env_path}")
    console.print(f"[bold]Log file:[/bold] {log_path}")

    test_module = Path(__file__).parent / "pytest_tests" / "test_yaml_case.py"
    pytest_args = [
        str(test_module),
        "-p",
        "runner.pytest_plugin",
        f"--arf-suite={suite_path}",
        f"--arf-env={env_path}",
        f"--arf-report-dir={reports_dir}",
        "--tb=short",
    ]
    if not verbose:
        pytest_args.insert(0, "-q")
    exit_code = pytest.main(pytest_args)

    json_report = Path(reports_dir) / "report.json"
    html_report = Path(reports_dir) / "report.html"
    console.print(f"\n[bold]Reports:[/bold] {json_report} and {html_report}")
    if exit_code == 0:
        console.print("[green]All tests passed.[/green]")
    else:
        console.print("[red]Some tests failed. Open the HTML report for defect summaries.[/red]")
    return int(exit_code)


def _list_suites(suites_dir: str) -> int:
    directory = Path(suites_dir)
    table = Table(title="Available suites")
    table.add_column("Name")
    table.add_column("Path")
    if not directory.exists():
        console.print(f"[red]Suite directory not found:[/red] {directory}")
        return 1
    for path in sorted([*directory.glob("*.yaml"), *directory.glob("*.json")]):
        table.add_row(path.stem, str(path))
    console.print(table)
    return 0


def _validate_suite(suite: str, env_path: str) -> int:
    suite_path = resolve_suite_path(suite)
    env = load_env_config(env_path)
    loaded = load_suite(suite_path, env.variables)
    console.print(f"[green]Suite is valid:[/green] {loaded.name} ({len(loaded.cases)} cases)")
    return 0
