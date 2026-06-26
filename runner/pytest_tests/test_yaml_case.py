from __future__ import annotations

from runner.executor import execute_case


def test_yaml_case(arf_case, arf_env, arf_result_store):
    result = execute_case(arf_case, arf_env)
    arf_result_store.append(result)
    assert result.passed, result.defect_summary
