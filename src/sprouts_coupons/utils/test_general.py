import json

import pytest

from sprouts-coupons.utils.general import read_json


@pytest.fixture
def test_json_file(tmp_path):
    """Fixture that creates a temporary JSON file for testing."""
    test_json_path = tmp_path / "test.json"
    test_data = {"key": "value"}
    with open(test_json_path, "w") as f:
        json.dump(test_data, f)
    return test_json_path, test_data


@pytest.mark.unit_build
class TestGeneralUtils:
    """Testing for general functions. Included to demonstrate pytest markers w/ GH Actions."""

    def test_read_json(self, test_json_file):
        test_json_path, test_data = test_json_file
        result = read_json(str(test_json_path))
        assert result == test_data

    def test_read_json_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            read_json("non_existent_file.json")

    def test_read_json_invalid_json(self, tmp_path):
        invalid_json_path = tmp_path / "invalid.json"
        with open(invalid_json_path, "w") as f:
            f.write("This is not a valid JSON string")

        with pytest.raises(json.JSONDecodeError):
            read_json(str(invalid_json_path))