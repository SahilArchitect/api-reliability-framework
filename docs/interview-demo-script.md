# Interview demo script

Use this when explaining the project in interviews.

## 30-second pitch

I built a Python API reliability framework that runs declarative YAML test suites through pytest. It executes REST calls, validates response contracts, verifies PostgreSQL side effects, classifies failures, and generates JSON/HTML reports with automatic defect summaries. I also included a mock FastAPI service and Docker Compose environment so the project can be demonstrated end-to-end.

## Demo sequence

```bash
docker compose up --build -d postgres mock-api
python -m runner run --suite smoke --env configs/env.local.yaml --reports-dir reports
open reports/report.html
```

Then run intentional failures:

```bash
python -m runner run --suite failure_gallery --env configs/env.local.yaml --reports-dir reports
open reports/report.html
```

## What to emphasize

- YAML-driven test definitions make the framework reusable by QA, SDET, support, and backend teams.
- DB validation catches cases where the API returns success but persistence is wrong.
- Failure classification reduces triage time.
- Automatic defect summaries make failures immediately actionable.
- GitHub Actions proves CI readiness.
