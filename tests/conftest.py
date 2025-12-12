"""Pytest configuration and fixtures."""
import pytest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root / "frontend"))
sys.path.insert(0, str(project_root / "scrapers"))
sys.path.insert(0, str(project_root / "snowflake"))

# Suppress warnings
os.environ["PYTHONWARNINGS"] = "ignore::DeprecationWarning"


@pytest.fixture(scope="session")
def project_root_path():
    """Provide project root path to tests."""
    return Path(__file__).parent.parent


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests as API endpoint tests"
    )
