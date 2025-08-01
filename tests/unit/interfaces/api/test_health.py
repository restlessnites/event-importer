"""Tests for API health endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.interfaces.api.server import create_app


@pytest.fixture
def client():
    """Create a test client."""
    app = create_app()
    return TestClient(app)


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "features" in data
    assert isinstance(data["features"], list)
    # Should always have at least dice and ra
    assert "dice" in data["features"]
    assert "ra" in data["features"]


def test_health_check_with_api_keys(client):
    """Test health check with API keys configured."""
    with (
        patch("app.interfaces.api.routes.health.config") as mock_config,
        patch(
            "app.interfaces.api.routes.health.get_enabled_integrations"
        ) as mock_get_enabled_integrations,
    ):
        # Configure mock config
        mock_config.get_enabled_features.return_value = [
            "dice",
            "ra",
            "ticketmaster",
            "web",
            "image",
            "ai_extraction",
        ]
        mock_get_enabled_integrations.return_value = ["ticketfairy"]

        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        features = data["features"]
        integrations = data["integrations"]

        # Check expected features are enabled
        assert "dice" in features
        assert "ra" in features
        assert "ticketmaster" in features
        assert "web" in features
        assert "image" in features
        assert "ai_extraction" in features
        assert "ticketfairy" in integrations
