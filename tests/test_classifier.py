from runner.classifier import classify_error
from runner.models import FailureType


def test_timeout_classification():
    assert classify_error("Request timeout after 1s") == FailureType.TIMEOUT


def test_auth_classification():
    assert classify_error("Expected status 200, observed 401", status_code=401) == FailureType.AUTH_FAILURE


def test_db_classification():
    assert classify_error("Expected exactly one row, observed 0", check_name="db:verify row") == FailureType.DB_MISMATCH


def test_validation_classification():
    assert classify_error("Expected JSON field status='ok', observed 'down'") == FailureType.VALIDATION_FAILURE
