"""Tests for TicketFairy client."""

from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.ticketfairy.client import TicketFairyClient
from app.schemas import EventData


@pytest.fixture
def tf_client():
    """Create a TicketFairy client."""
    return TicketFairyClient()


@pytest.fixture
def sample_event_data():
    """Create sample event data."""
    return EventData(
        title="Test Event",
        venue="Test Venue",
        date="2025-02-01",
        lineup=["Artist 1", "Artist 2"],
        genres=["house", "techno"],
        source_url="https://example.com/event"
    )


@pytest.mark.asyncio
async def test_submit_event_success(tf_client, sample_event_data):
    """Test successful event submission."""
    with patch.object(tf_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "id": "123",
            "status": "accepted",
            "message": "Event submitted successfully"
        })
        mock_post.return_value = mock_response

        result = await tf_client.submit_event(sample_event_data)

        assert result["success"] is True
        assert result["submission_id"] == "123"
        assert result["status"] == "accepted"

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "/events/submit"
        assert "json" in call_args[1]


@pytest.mark.asyncio
async def test_submit_event_failure(tf_client, sample_event_data):
    """Test failed event submission."""
    with patch.object(tf_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_response.json = AsyncMock(return_value={
            "error": "Invalid event data",
            "details": "Missing required field: location"
        })
        mock_post.return_value = mock_response

        result = await tf_client.submit_event(sample_event_data)

        assert result["success"] is False
        assert "error" in result
        assert "Invalid event data" in result["error"]


@pytest.mark.asyncio
async def test_get_submission_status(tf_client):
    """Test getting submission status."""
    with patch.object(tf_client.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "id": "123",
            "status": "published",
            "event_url": "https://ticketfairy.com/event/123"
        })
        mock_get.return_value = mock_response

        result = await tf_client.get_submission_status("123")

        assert result["status"] == "published"
        assert result["event_url"] == "https://ticketfairy.com/event/123"

        mock_get.assert_called_once_with("/submissions/123")
