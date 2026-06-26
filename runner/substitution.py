from __future__ import annotations

import os
import re
from typing import Any

_TOKEN_PATTERN = re.compile(r"\$\{([A-Za-z0-9_]+)\}")


def substitute(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return _TOKEN_PATTERN.sub(lambda match: str(variables.get(match.group(1), os.getenv(match.group(1), match.group(0)))), value)
    if isinstance(value, list):
        return [substitute(item, variables) for item in value]
    if isinstance(value, dict):
        return {str(k): substitute(v, variables) for k, v in value.items()}
    return value
