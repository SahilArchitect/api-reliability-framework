from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import yaml

from runner.models import EnvConfig, RetryConfig
from runner.substitution import substitute


def load_yaml_or_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    text = file_path.read_text(encoding="utf-8")
    if file_path.suffix.lower() == ".json":
        import json

        return json.loads(text)
    loaded = yaml.safe_load(text) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected mapping in {file_path}")
    return loaded


def load_env_config(path: str | Path) -> EnvConfig:
    raw = load_yaml_or_json(path)
    run_id = str(int(time.time() * 1000))
    variables = dict(raw.get("variables") or {})
    variables["RUN_ID"] = run_id
    variables = substitute(variables, variables)

    retry_raw = raw.get("retry") or {}
    retry = RetryConfig(
        attempts=int(retry_raw.get("attempts", 1)),
        backoff_seconds=float(retry_raw.get("backoff_seconds", 0.0)),
    )

    return EnvConfig(
        base_url=str(raw["base_url"]).rstrip("/"),
        database_url=raw.get("database_url"),
        timeout_seconds=float(raw.get("timeout_seconds", 5.0)),
        retry=retry,
        headers={str(k): str(v) for k, v in (raw.get("headers") or {}).items()},
        variables=variables,
    )
