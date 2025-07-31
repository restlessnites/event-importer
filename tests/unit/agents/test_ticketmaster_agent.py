"""Tests for the Ticketmaster agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.ticketmaster_agent import TicketmasterAgent
from app.schemas import EventData, EventLocation


@pytest.fixture
def mock_config():
    """Return a mock config object."""
    config = MagicMock()
    config.api.ticketmaster_api_key = "test_key"
    return config


@pytest.fixture
def http_service():
    """Return a mock http service."""
    return AsyncMock()


@pytest.fixture
def llm_service():
    """Return a mock llm service."""
    return AsyncMock()


@pytest.mark.asyncio
@patch("app.agents.ticketmaster_agent.logger")
async def test_import_event_api_error(
    mock_logger, mock_config, http_service, llm_service
):
    """Test that the agent handles API errors gracefully."""
    # Arrange
    url = "https://www.ticketmaster.com/event/123"

    # First call for direct lookup will fail with 401
    direct_lookup_response = AsyncMock()
    direct_lookup_response.status = 401
    direct_lookup_response.json = AsyncMock(
        return_value={"fault": {"faultstring": "Invalid API Key"}}
    )

    # Second call for search will also fail
    search_response = AsyncMock()
    search_response.status = 401
    search_response.json = AsyncMock(
        return_value={"fault": {"faultstring": "Invalid API Key"}}
    )

    # Configure http_service to return different responses for each call
    http_service.get.side_effect = [direct_lookup_response, search_response]

    agent = TicketmasterAgent(
        mock_config, services={"http": http_service, "llm": llm_service}
    )

    # Act
    result = await agent.import_event(url, "test_request_id")

    # Assert
    assert result is None
    # The final error log should be about not finding the event
    mock_logger.error.assert_called_with(
        "Could not find event via direct lookup or search",
        extra={"url": url},
    )


@pytest.mark.asyncio
async def test_import_event_success(mock_config, http_service, llm_service):
    """Test that the agent correctly parses a valid API response."""
    # Arrange
    url = "https://www.ticketmaster.com/event/G5v0Z9Jke0A_G"
    api_response = {
        "name": "Test Event",
        "dates": {"start": {"localDate": "2025-01-01", "localTime": "20:00:00"}},
        "_embedded": {
            "venues": [
                {
                    "name": "Test Venue",
                    "city": {"name": "Test City"},
                    "state": {"name": "Test State", "stateCode": "TS"},
                    "country": {"name": "Test Country", "countryCode": "TC"},
                    "location": {"latitude": "34.05", "longitude": "-118.25"},
                }
            ],
            "attractions": [{"name": "Artist 1"}, {"name": "Artist 2"}],
        },
        "classifications": [{"segment": {"name": "Music"}, "genre": {"name": "Rock"}}],
    }
    http_service.get.return_value.json = AsyncMock(return_value=api_response)
    http_service.get.return_value.status = 200

    # Mock the llm_service to return the event data directly
    llm_service.generate_descriptions.side_effect = lambda event_data: event_data

    agent = TicketmasterAgent(
        mock_config, services={"http": http_service, "llm": llm_service}
    )

    # Act
    result = await agent.import_event(url, "test_request_id")

    # Assert
    assert isinstance(result, EventData)
    assert result.title == "Test Event"
    assert result.venue == "Test Venue"
    assert result.date == "2025-01-01"
    assert result.time.start == "20:00"
    assert result.lineup == ["Artist 1", "Artist 2"]
    assert result.genres == ["Rock"]
    assert isinstance(result.location, EventLocation)
    assert result.location.city == "Test City"
    assert result.location.state == "TS"
    assert result.location.country == "TC"
    assert result.location.coordinates.lat == 34.05
    assert result.location.coordinates.lng == -118.25


@pytest.mark.asyncio
async def test_import_event_no_embedded_data(mock_config, http_service, llm_service):
    """Test that the agent handles responses with no embedded data."""
    # Arrange
    url = "https://www.ticketmaster.com/event/no-embedded"
    api_response = {
        "name": "Test Event with No Venue",
        "dates": {"start": {"localDate": "2025-01-01", "localTime": "20:00:00"}},
    }
    http_service.get.return_value.json = AsyncMock(return_value=api_response)
    http_service.get.return_value.status = 200

    # Mock the llm_service to return the event data directly
    llm_service.generate_descriptions.side_effect = lambda event_data: event_data

    agent = TicketmasterAgent(
        mock_config, services={"http": http_service, "llm": llm_service}
    )

    # Act
    result = await agent.import_event(url, "test_request_id")

    # Assert
    assert isinstance(result, EventData)
    assert result.title == "Test Event with No Venue"
    assert result.venue is None
    assert result.lineup == []


@pytest.mark.asyncio
async def test_import_event_no_dates(mock_config, http_service, llm_service):
    """Test that the agent handles responses with no dates."""
    # Arrange
    url = "https://www.ticketmaster.com/event/no-dates"
    api_response = {"name": "Test Event with No Dates"}
    http_service.get.return_value.json = AsyncMock(return_value=api_response)
    http_service.get.return_value.status = 200

    # Mock the llm_service to return the event data directly
    llm_service.generate_descriptions.side_effect = lambda event_data: event_data

    agent = TicketmasterAgent(
        mock_config, services={"http": http_service, "llm": llm_service}
    )

    # Act
    result = await agent.import_event(url, "test_request_id")

    # Assert
    assert isinstance(result, EventData)
    assert result.title == "Test Event with No Dates"
    assert result.date is None


@pytest.mark.asyncio
async def test_import_event_not_found(mock_config, http_service, llm_service):
    """Test that the agent handles a 404 Not Found response."""
    # Arrange
    url = "https://www.ticketmaster.com/event/notfound"
    http_service.get.return_value.json = AsyncMock(return_value={})
    http_service.get.return_value.status = 404
    agent = TicketmasterAgent(
        mock_config, services={"http": http_service, "llm": llm_service}
    )

    # Act
    result = await agent.import_event(url, "test_request_id")

    # Assert
    assert result is None
