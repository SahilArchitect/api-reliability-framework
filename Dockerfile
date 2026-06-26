FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY runner ./runner
COPY mock_service ./mock_service
COPY suites ./suites
COPY configs ./configs
COPY tests ./tests

RUN pip install -e ".[dev]"

CMD ["python", "-m", "runner", "run", "--suite", "smoke", "--env", "configs/env.docker.yaml", "--reports-dir", "reports"]
