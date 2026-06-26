from __future__ import annotations

from typing import Any


class JsonPathError(ValueError):
    pass


def get_json_path(document: Any, path: str) -> Any:
    """Tiny JSON path reader supporting $.field, $.a.b, and $.items[0].name."""
    if not path.startswith("$"):
        raise JsonPathError(f"JSON path must start with $: {path}")
    current = document
    token = path[1:]
    while token:
        if token.startswith("."):
            token = token[1:]
            name, token = _read_name(token)
            if not isinstance(current, dict) or name not in current:
                raise JsonPathError(f"Missing field '{name}' in path {path}")
            current = current[name]
        elif token.startswith("["):
            end = token.find("]")
            if end == -1:
                raise JsonPathError(f"Unclosed index in path {path}")
            index_text = token[1:end]
            try:
                index = int(index_text)
            except ValueError as exc:
                raise JsonPathError(f"Only numeric indexes are supported: {path}") from exc
            if not isinstance(current, list) or index >= len(current):
                raise JsonPathError(f"Index {index} missing in path {path}")
            current = current[index]
            token = token[end + 1 :]
        else:
            raise JsonPathError(f"Unsupported token near '{token}' in path {path}")
    return current


def _read_name(token: str) -> tuple[str, str]:
    stop_positions = [idx for idx in [token.find("."), token.find("[")] if idx != -1]
    if not stop_positions:
        return token, ""
    stop = min(stop_positions)
    return token[:stop], token[stop:]
