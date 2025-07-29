"""Tests for TicketFairy client."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.ticketfairy.shared.client import TicketFairyClient


@pytest.fixture
def tf_client():
    """Create a TicketFairy client."""
    client = TicketFairyClient()

    # Mock the config directly on the client instance
    config = MagicMock()
    config.api_key = "test-api-key"
    config.api_base_url = "https://www.theticketfairy.com/api"
    config.draft_events_endpoint = "/draft-events"
    config.origin = "https://example.com"
    config.timeout = 30
    client.config = config

    return client


@pytest.fixture
def sample_event_data():
    """Create sample event data."""
    return {
        "title": "Test Event",
        "venue": "Test Venue",
        "date": "2025-02-01",
        "lineup": ["Artist 1", "Artist 2"],
        "genres": ["house", "techno"],
        "source_url": "https://example.com/event",
    }


@pytest.mark.asyncio
async def test_submit_success(tf_client, sample_event_data):
    """Test successful event submission."""
    with patch.object(tf_client.http, "post", new_callable=AsyncMock) as mock_post:
        # Create a mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "id": "123",
                    "status": "accepted",
                    "message": "Event submitted successfully",
                }
            )
        )
        mock_post.return_value = mock_response

        result = await tf_client.submit(sample_event_data)

        assert result["id"] == "123"
        assert result["status"] == "accepted"
        assert result["message"] == "Event submitted successfully"

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://www.theticketfairy.com/api/draft-events"
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-api-key"
        assert call_args[1]["json"] == sample_event_data


@pytest.mark.asyncio
async def test_submit_api_error(tf_client, sample_event_data):
    """Test API error during submission."""
    with patch.object(tf_client.http, "post", new_callable=AsyncMock) as mock_post:
        # Create a mock error response
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(
            return_value=json.dumps({"message": "Invalid event data"})
        )
        mock_post.return_value = mock_response

        result = await tf_client.submit(sample_event_data)

        # The submit method returns the response data even on error
        assert result["message"] == "Invalid event data"


@pytest.mark.asyncio
async def test_submit_no_api_key(sample_event_data):
    """Test submission without API key."""
    client = TicketFairyClient()

    # Mock the config attribute directly
    config = MagicMock()
    config.api_key = None  # No API key
    config.api_base_url = "https://www.theticketfairy.com/api"
    config.draft_events_endpoint = "/draft-events"
    config.origin = "https://example.com"
    config.timeout = 30
    client.config = config

    with pytest.raises(ValueError, match="TicketFairy API key not configured"):
        await client.submit(sample_event_data)
