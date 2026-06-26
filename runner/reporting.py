from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Template

from runner.models import CheckResult, Suite, TestCase, TestResult
from runner.serialization import to_plain


def build_defect_summary(case: TestCase, result: TestResult) -> str:
    first_failure = next((check for check in result.checks if not check.passed), None)
    failure_type = result.failure_type.value if result.failure_type else "UNKNOWN_FAILURE"
    title = f"[{failure_type}] {case.id} - {case.name}"
    severity = _severity_for(failure_type)
    observed = first_failure.message if first_failure else "Test failed without a captured assertion message."
    expected = _expected_text(first_failure)
    repro_steps = [
        f"{case.method} {case.path} with configured headers/body/query parameters.",
        "Validate HTTP response against the suite expectations.",
    ]
    if case.db:
        repro_steps.append("Run configured PostgreSQL validation query after the API call.")
    owner = _owner_for(failure_type)

    numbered = "\n".join(f"{idx}. {step}" for idx, step in enumerate(repro_steps, start=1))
    return (
        f"Title: {title}\n"
        f"Severity: {severity}\n"
        f"Observed: {observed}\n"
        f"Expected: {expected}\n"
        f"Repro Steps:\n{numbered}\n"
        f"Likely owner: {owner}"
    )


def write_reports(suite: Suite, results: list[TestResult], reports_dir: str | Path) -> dict[str, str]:
    output_dir = Path(reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "suite": {
            "name": suite.name,
            "version": suite.version,
            "description": suite.description,
            "tags": suite.tags,
        },
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summarize_results(results),
        "results": to_plain(results),
    }

    json_path = output_dir / "report.json"
    html_path = output_dir / "report.html"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    html_path.write_text(render_html_report(payload), encoding="utf-8")
    return {"json": str(json_path), "html": str(html_path)}


def summarize_results(results: list[TestResult]) -> dict[str, int]:
    total = len(results)
    passed = sum(1 for item in results if item.passed)
    failed = total - passed
    by_failure_type: dict[str, int] = {}
    for item in results:
        if item.failure_type:
            by_failure_type[item.failure_type.value] = by_failure_type.get(item.failure_type.value, 0) + 1
    return {"total": total, "passed": passed, "failed": failed, **{f"failure_{k}": v for k, v in by_failure_type.items()}}


def render_html_report(payload: dict) -> str:
    template = Template(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>API Reliability Report</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; margin: 32px; background: #f7f7f8; color: #1f2937; }
    .card { background: white; border: 1px solid #e5e7eb; border-radius: 14px; padding: 20px; margin-bottom: 18px; box-shadow: 0 1px 2px rgba(0,0,0,.04); }
    .summary { display: flex; gap: 16px; flex-wrap: wrap; }
    .metric { min-width: 120px; padding: 16px; border-radius: 12px; background: #f3f4f6; }
    .passed { color: #166534; font-weight: 700; }
    .failed { color: #991b1b; font-weight: 700; }
    code, pre { background: #111827; color: #f9fafb; padding: 12px; border-radius: 10px; overflow: auto; display: block; }
    table { border-collapse: collapse; width: 100%; }
    th, td { text-align: left; border-bottom: 1px solid #e5e7eb; padding: 10px; vertical-align: top; }
    .badge { display: inline-block; padding: 3px 8px; border-radius: 999px; background: #e5e7eb; font-size: 12px; }
  </style>
</head>
<body>
  <h1>API Reliability Report</h1>
  <div class="card">
    <h2>{{ payload.suite.name }}</h2>
    <p>{{ payload.suite.description }}</p>
    <p><strong>Generated:</strong> {{ payload.generated_at }}</p>
  </div>
  <div class="summary card">
    <div class="metric"><strong>Total</strong><br>{{ payload.summary.total }}</div>
    <div class="metric"><strong>Passed</strong><br><span class="passed">{{ payload.summary.passed }}</span></div>
    <div class="metric"><strong>Failed</strong><br><span class="failed">{{ payload.summary.failed }}</span></div>
  </div>
  {% for result in payload.results %}
  <div class="card">
    <h2>{{ result.case_id }} - {{ result.case_name }}</h2>
    <p>
      <span class="badge">{{ result.method }} {{ result.path }}</span>
      {% if result.passed %}<span class="passed">PASSED</span>{% else %}<span class="failed">FAILED</span>{% endif %}
      {% if result.failure_type %}<span class="badge">{{ result.failure_type }}</span>{% endif %}
      <span class="badge">{{ result.duration_ms }} ms</span>
    </p>
    <table>
      <thead><tr><th>Check</th><th>Status</th><th>Message</th><th>Expected</th><th>Observed</th></tr></thead>
      <tbody>
        {% for check in result.checks %}
        <tr>
          <td>{{ check.name }}</td>
          <td>{% if check.passed %}<span class="passed">PASS</span>{% else %}<span class="failed">FAIL</span>{% endif %}</td>
          <td>{{ check.message }}</td>
          <td>{{ check.expected }}</td>
          <td>{{ check.observed }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% if result.defect_summary %}
    <h3>Automatic defect summary</h3>
    <pre>{{ result.defect_summary }}</pre>
    {% endif %}
  </div>
  {% endfor %}
</body>
</html>
        """
    )
    return template.render(payload=payload)


def _severity_for(failure_type: str) -> str:
    if failure_type in {"DB_MISMATCH", "AUTH_FAILURE", "TIMEOUT"}:
        return "High"
    if failure_type in {"API_FAILURE", "VALIDATION_FAILURE"}:
        return "Medium"
    return "Low"


def _owner_for(failure_type: str) -> str:
    if failure_type == "DB_MISMATCH":
        return "Backend/API + Database team"
    if failure_type == "AUTH_FAILURE":
        return "Auth/API team"
    if failure_type == "TIMEOUT":
        return "API/Platform reliability team"
    if failure_type == "VALIDATION_FAILURE":
        return "API contract owner"
    if failure_type == "API_FAILURE":
        return "Backend/API team"
    return "Needs triage"


def _expected_text(first_failure: CheckResult | None) -> str:
    if not first_failure:
        return "Configured test expectations should pass."
    if first_failure.expected is not None:
        return f"Expected {first_failure.expected!r}."
    return "Expected the configured validation check to pass."


def escape_text(value: str) -> str:
    return html.escape(value)
