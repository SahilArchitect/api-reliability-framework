.PHONY: install test lint format run-smoke run-regression run-failure docker-smoke clean

install:
	python -m pip install -e ".[dev]"

test:
	pytest tests

lint:
	ruff check .
	mypy runner

format:
	ruff check . --fix

run-smoke:
	python -m runner run --suite smoke --env configs/env.local.yaml --reports-dir reports

run-regression:
	python -m runner run --suite regression --env configs/env.local.yaml --reports-dir reports

run-failure:
	python -m runner run --suite failure_gallery --env configs/env.local.yaml --reports-dir reports

docker-smoke:
	docker compose up --build test-runner

clean:
	rm -rf reports .pytest_cache .ruff_cache .mypy_cache
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
