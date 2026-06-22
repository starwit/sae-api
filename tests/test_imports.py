import pytest

def test_saeapi_import():
    try:
        from saeapi.saeapi import SaeApi
    except ImportError as e:
        pytest.fail(f"Failed to import SaeApi: {e}")

    assert SaeApi is not None, "SaeApi should be imported successfully"