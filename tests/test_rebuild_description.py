"""Test event description regeneration functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_config
from app.core.importer import EventImporter
from app.interfaces.api.models.requests import RebuildDescriptionRequest
from app.interfaces.api.routes.events import rebuild_event_description
from app.schemas import EventData, EventLocation, EventTime
from app.services.claude import ClaudeService
from app.services.llm import LLMService


@pytest.fixture
def sample_event_data():
    """Create sample event data for testing."""
    return EventData(
        title="Test Concert",
        venue="Test Venue",
        date="2024-01-01",
        time=EventTime(start="20:00", end="23:00", timezone="America/Los_Angeles"),
        location=EventLocation(
            city="Los Angeles", state="California", country="United States"
        ),
        short_description="A test concert event",
        long_description="This is a detailed description of the test concert event.",
        genres=["Rock", "Alternative"],
        source_url="https://example.com/event",
    )


class TestRebuildDescription:
    """Test cases for description regeneration."""

    @pytest.mark.asyncio
    async def test_rebuild_short_description(self, sample_event_data):
        """Test rebuilding short description."""
        cached_event = sample_event_data.model_dump(mode="json")
        cached_event["_db_id"] = 123

        with patch("app.core.importer.get_cached_event") as mock_get_cached:
            mock_get_cached.return_value = cached_event

            mock_llm = MagicMock()
            mock_llm.generate_short_description = AsyncMock(
                return_value="New short description"
            )

            importer = EventImporter(get_config())
            importer._services["llm"] = mock_llm

            result = await importer.rebuild_description(
                123, description_type="short", supplementary_context="Make it exciting"
            )

            assert result is not None
            assert result.short_description == "New short description"
            assert result.long_description == sample_event_data.long_description
            mock_llm.generate_short_description.assert_called_once()

    @pytest.mark.asyncio
    async def test_rebuild_long_description(self, sample_event_data):
        """Test rebuilding long description."""
        cached_event = sample_event_data.model_dump(mode="json")
        cached_event["_db_id"] = 123

        with patch("app.core.importer.get_cached_event") as mock_get_cached:
            mock_get_cached.return_value = cached_event

            mock_llm = MagicMock()
            mock_llm.generate_long_description = AsyncMock(
                return_value="New detailed long description with more information"
            )

            importer = EventImporter(get_config())
            importer._services["llm"] = mock_llm

            result = await importer.rebuild_description(
                123, description_type="long", supplementary_context="Add venue details"
            )

            assert result is not None
            assert result.short_description == sample_event_data.short_description
            assert (
                result.long_description
                == "New detailed long description with more information"
            )
            mock_llm.generate_long_description.assert_called_once()

    @pytest.mark.asyncio
    async def test_rebuild_description_not_found(self):
        """Test rebuilding description for non-existent event."""
        with patch("app.core.importer.get_cached_event") as mock_get_cached:
            mock_get_cached.return_value = None

            importer = EventImporter(get_config())
            result = await importer.rebuild_description(999, "short")

            assert result is None

    @pytest.mark.asyncio
    async def test_rebuild_description_api_endpoint(self, sample_event_data):
        """Test the API endpoint for rebuilding descriptions."""
        mock_router = MagicMock()
        mock_importer = MagicMock()
        mock_router.importer = mock_importer
        mock_importer.rebuild_description = AsyncMock(return_value=sample_event_data)

        request = RebuildDescriptionRequest(
            description_type="short", supplementary_context="Make it exciting"
        )

        with patch(
            "app.interfaces.api.routes.events.get_router", return_value=mock_router
        ):
            response = await rebuild_event_description(123, request)

            assert response.success is True
            assert response.event_id == 123
            assert "preview only" in response.message.lower()
            assert response.data == sample_event_data
            mock_importer.rebuild_description.assert_called_with(
                123, description_type="short", supplementary_context="Make it exciting"
            )


class TestLLMServiceGeneration:
    """Test LLM service individual description generation."""

    @pytest.mark.asyncio
    async def test_generate_short_description(self, sample_event_data):
        """Test generating only short description."""
        mock_claude = MagicMock(spec=ClaudeService)
        mock_claude.generate_descriptions = AsyncMock(
            return_value=sample_event_data.model_copy(
                update={"short_description": "Claude short description"}
            )
        )

        llm_service = LLMService(get_config())
        llm_service.primary_service = mock_claude

        result = await llm_service.generate_short_description(
            sample_event_data, supplementary_context="Make it punchy"
        )

        assert result == "Claude short description"

    @pytest.mark.asyncio
    async def test_generate_long_description(self, sample_event_data):
        """Test generating only long description."""
        mock_claude = MagicMock(spec=ClaudeService)
        mock_claude.generate_descriptions = AsyncMock(
            return_value=sample_event_data.model_copy(
                update={"long_description": "Claude detailed long description"}
            )
        )

        llm_service = LLMService(get_config())
        llm_service.primary_service = mock_claude

        result = await llm_service.generate_long_description(
            sample_event_data, supplementary_context="Add historical context"
        )

        assert result == "Claude detailed long description"
