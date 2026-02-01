"""Pytest utilities and marker definitions.

This module provides pytest configuration and utilities for running tests.
Tests can be tagged using pytest markers (e.g., @pytest.mark.unit_build).

To run tests with a specific marker:
    pytest -m unit_build

To register custom markers, add them to pyproject.toml or pytest.ini:
    [tool.pytest.ini_options]
    markers = [
        "unit_build: marks tests as unit build tests",
    ]
"""

import pytest

# Define custom markers for test organization
unit_build = pytest.mark.unit_build
integration = pytest.mark.integration
slow = pytest.mark.slow
