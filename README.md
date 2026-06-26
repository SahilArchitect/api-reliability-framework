# API Test Automation and Reliability Framework

A production-style Python framework for testing REST APIs, validating PostgreSQL state, classifying failures, and generating clean defect reports from YAML/JSON test definitions.

This project is built for SDET, Test Automation, Application Support, Technical Support, and backend roles. It shows you can test an API, verify the database side effects, and hand a developer a useful bug report instead of a screenshot of sadness.

## What it does

- Runs API test suites from YAML or JSON definitions.
- Executes HTTP requests with retry and timeout control.
- Validates status code, headers, JSON body, JSON paths, and response schema-like required fields.
- Validates PostgreSQL state after API calls.
- Classifies failures into:
  - `API_FAILURE`
  - `DB_MISMATCH`
  - `TIMEOUT`
  - `VALIDATION_FAILURE`
  - `AUTH_FAILURE`
  - `UNKNOWN_FAILURE`
- Generates JSON and HTML reports.
- Writes structured JSON logs to `reports/run.log`.
- Produces automatic defect summaries for failed test cases.
- Includes a realistic mock FastAPI service backed by PostgreSQL.
- Provides a CLI command:

```bash
python -m runner run --suite smoke
```

- Includes Docker Compose and GitHub Actions CI.

## Architecture

```mermaid
flowchart LR
    YAML[YAML/JSON Suites] --> CLI[runner CLI]
    CLI --> Pytest[pytest dynamic runner]
    Pytest --> Executor[API executor]
    Executor --> MockAPI[Mock FastAPI service]
    MockAPI --> Postgres[(PostgreSQL)]
    Pytest --> DBValidator[PostgreSQL validator]
    DBValidator --> Postgres
    Pytest --> Classifier[Failure classifier]
    Classifier --> Reports[JSON + HTML reports]
    Reports --> Defects[Auto defect summaries]
```

## Project structure

```text
api-reliability-framework/
├── runner/                         # Test framework package
│   ├── cli.py                       # CLI entrypoint
│   ├── executor.py                  # API execution + retries
│   ├── validators.py                # Response and DB validation
│   ├── classifier.py                # Failure classification
│   ├── reporting.py                 # JSON/HTML reports + defect summaries
│   ├── pytest_plugin.py             # pytest integration
│   └── pytest_tests/test_yaml_case.py
├── mock_service/                    # Fake API under test
│   └── app/main.py
├── suites/                          # YAML suites
│   ├── smoke.yaml
│   ├── regression.yaml
│   └── failure_gallery.yaml
├── configs/
│   ├── env.local.yaml
│   └── env.docker.yaml
├── tests/                           # Unit tests for framework internals
├── .github/workflows/ci.yml
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── pyproject.toml
```

## Run with Docker Compose, easiest path

From the project root:

```bash
docker compose up --build test-runner
```

Reports are written to:

```text
reports/report.json
reports/report.html
reports/run.log
```

A static sample report is also included in `sample_reports/` for quick review.

To keep services running and execute manually:

```bash
docker compose up --build -d postgres mock-api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m runner run --suite smoke --env configs/env.local.yaml --reports-dir reports
```

## Local run without Docker test-runner

You still need PostgreSQL and the mock API. Let Docker run those two:

```bash
docker compose up --build -d postgres mock-api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m runner run --suite smoke --env configs/env.local.yaml --reports-dir reports
```

Check the mock API:

```bash
curl http://localhost:8000/health
```

## CLI usage

```bash
python -m runner run --suite smoke
python -m runner run --suite regression --env configs/env.local.yaml
python -m runner run --suite suites/smoke.yaml --reports-dir reports
python -m runner list-suites
python -m runner validate-suite --suite smoke
```

The `--suite smoke` shorthand resolves to `suites/smoke.yaml`.

## Example YAML test case

```yaml
name: Smoke Suite
cases:
  - id: create_order_success
    name: Create order and verify database row
    method: POST
    path: /orders
    headers:
      Authorization: "Bearer ${AUTH_TOKEN}"
    json:
      order_id: "${ORDER_ID}"
      customer_email: "sahil@example.com"
      amount: 1299.50
      status: created
    expected:
      status_code: 201
      json:
        order_id: "${ORDER_ID}"
        status: created
      json_paths:
        - path: "$.amount"
          equals: 1299.5
    db:
      - name: Verify order row exists
        query: "select status, amount from orders where order_id = %(order_id)s"
        params:
          order_id: "${ORDER_ID}"
        expect_one:
          status: created
          amount: 1299.5
```

## Environment config

```yaml
base_url: "http://localhost:8000"
database_url: "postgresql://app:app@localhost:5432/app"
timeout_seconds: 5
retry:
  attempts: 2
  backoff_seconds: 0.25
headers:
  X-Test-Runner: api-reliability-framework
variables:
  AUTH_TOKEN: local-secret-token
  ORDER_ID: order-${RUN_ID}
```

Variables are resolved from:

1. Built-in variables like `${RUN_ID}`.
2. Environment config variables.
3. OS environment variables.

## Failure classification examples

| Failure | Classifier output | Example cause |
|---|---|---|
| Endpoint returns 500 or connection fails | `API_FAILURE` | Service error, wrong path, broken dependency |
| HTTP request times out | `TIMEOUT` | Slow endpoint, service unavailable |
| 401 or 403 status | `AUTH_FAILURE` | Missing/invalid token |
| JSON/status/header assertion fails | `VALIDATION_FAILURE` | API response changed |
| SQL validation fails | `DB_MISMATCH` | API returned success but DB row was wrong/missing |

## Automatic defect report example

```text
Title: [DB_MISMATCH] create_order_success - Verify order row exists
Severity: High
Observed: Query returned status='pending', expected status='created'.
Expected: Database row should match the configured expectations after the API call.
Repro Steps:
1. POST /orders with the configured payload.
2. Validate HTTP response.
3. Run DB query: select status, amount from orders where order_id = %(order_id)s
Likely owner: Backend/API team
```

## Mock service endpoints

The included mock service provides:

- `GET /health`
- `POST /orders`
- `GET /orders/{order_id}`
- `PATCH /orders/{order_id}/status`
- `GET /orders/{order_id}/audit`
- `GET /slow?seconds=2`
- `GET /auth/check`

The service requires:

```text
Authorization: Bearer local-secret-token
```

for protected endpoints.

## GitHub Actions CI

The CI workflow:

1. Installs dependencies.
2. Starts PostgreSQL and mock API using Docker Compose.
3. Runs unit tests.
4. Runs the smoke API suite.
5. Uploads reports as build artifacts.

File:

```text
.github/workflows/ci.yml
```

## Troubleshooting

### Docker credential error on macOS

If Docker shows something like:

```text
error getting credentials - err: exec: "docker-credential-desktop": executable file not found in $PATH
```

edit `~/.docker/config.json` and remove or fix the broken `credsStore` entry, then retry:

```bash
docker compose up --build test-runner
```

Yes, Docker sometimes fails before your code even gets a chance to fail. Elegant civilization.

### Port already in use

If port `8000` or `5432` is busy, change the host ports in `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"
```

Then update `configs/env.local.yaml` accordingly.
