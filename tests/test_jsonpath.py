from runner.jsonpath import get_json_path


def test_get_nested_field():
    body = {"order": {"items": [{"sku": "ABC", "qty": 2}]}}
    assert get_json_path(body, "$.order.items[0].sku") == "ABC"
    assert get_json_path(body, "$.order.items[0].qty") == 2
