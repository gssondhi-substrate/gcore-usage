"""
Pytest configuration and fixtures for Gcore Usage API tests.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from main_new import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_token_manager():
    """Mock token manager."""
    with patch('apps.api.routes.token_manager') as mock:
        mock.get_token.return_value = "mock-token"
        yield mock


@pytest.fixture
def mock_gcore_client():
    """Mock Gcore client."""
    with patch('apps.api.routes.gcore_client') as mock:
        mock.get_features.return_value = [
            {"id": 1, "product": "CDN", "name": "Test Feature"}
        ]
        mock.start_report.return_value = "test-uuid-123"
        mock.check_status.return_value = {"status": "completed"}
        mock.download_report.return_value = [
            {"Client ID": "123", "Metric value": "100"}
        ]
        yield mock


@pytest.fixture
def sample_report_request():
    """Sample report request data."""
    return {
        "gcore_user_id": "123",
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "format": "json"
    }
