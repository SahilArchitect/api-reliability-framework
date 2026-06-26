from runner.loader import load_suite


def test_load_suite_with_variable_substitution(tmp_path):
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        """
name: Demo
cases:
  - id: c1
    method: GET
    path: /orders/${ORDER_ID}
    expected:
      status_code: 200
""",
        encoding="utf-8",
    )
    suite = load_suite(suite_path, {"ORDER_ID": "o-1"})
    assert suite.cases[0].path == "/orders/o-1"
    assert suite.cases[0].expected.status_code == 200
