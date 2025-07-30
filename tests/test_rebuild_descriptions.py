"""Test event description regeneration functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_config
from app.core.importer import EventImporter
from app.interfaces.api.models.requests import RebuildDescriptionRequest
from app.interfaces.api.models.responses import RebuildDescriptionResponse
from app.interfaces.api.routes.events import rebuild_event_descriptions
from app.schemas import EventData, EventLocation, EventTime
from app.services.claude import ClaudeService
from app.services.openai import OpenAIService
from app.shared.database.models import EventCache


@pytest.fixture
def sample_event_data():
    """Create sample event data for testing."""
    return EventData(
        title="Test Concert",
        venue="The Fillmore",
        date="2024-12-25",
        time=EventTime(start="20:00"),
        location=EventLocation(
            city="San Francisco",
            state="CA",
            country="USA"
        ),
        lineup=["Artist 1", "Artist 2"],
        genres=["Rock", "Alternative"],
        short_description="Rock concert at The Fillmore",
        long_description="A great rock concert featuring Artist 1 and Artist 2 at the historic Fillmore venue.",
        source_url="https://example.com/event/123"
    )


@pytest.fixture
def mock_event_cache(sample_event_data):
    """Create a mock event cache entry."""
    cache = MagicMock(spec=EventCache)
    cache.id = 123
    cache.source_url = sample_event_data.source_url
    cache.scraped_data = sample_event_data.model_dump(mode="json")
    return cache


class TestRebuildDescriptions:
    """Test the rebuild descriptions functionality."""

    @pytest.mark.asyncio
    async def test_rebuild_descriptions_basic(self, sample_event_data):
        """Test basic description rebuild without supplementary context."""
        # Create importer with mocked services
        importer = EventImporter()

        # Mock the LLM service
        mock_llm_service = AsyncMock()
        mock_llm_service.generate_descriptions = AsyncMock(return_value=sample_event_data)
        importer._services["llm"] = mock_llm_service

        # Mock get_cached_event to return our sample data with _db_id
        cached_data = sample_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 123

        with patch("app.core.importer.get_cached_event", return_value=cached_data), \
             patch("app.core.importer.cache_event") as mock_cache:
            result = await importer.rebuild_descriptions(123)

            # Verify the result
            assert result is not None
            assert result.title == "Test Concert"

            # Verify LLM service was called correctly
            mock_llm_service.generate_descriptions.assert_called_once()
            call_args = mock_llm_service.generate_descriptions.call_args
            assert call_args[1]["force_rebuild"] is True
            assert call_args[1]["supplementary_context"] is None

            # Verify cache was updated
            mock_cache.assert_called_once_with(
                sample_event_data.source_url,
                sample_event_data.model_dump(mode="json")
            )

    @pytest.mark.asyncio
    async def test_rebuild_descriptions_with_context(self, sample_event_data):
        """Test description rebuild with supplementary context."""
        importer = EventImporter()

        # Mock the LLM service to return modified descriptions
        modified_event = sample_event_data.model_copy()
        modified_event.long_description = "An amazing night of rock music featuring Artist 1 and Artist 2 at the legendary Fillmore. This special holiday concert will feature extended sets and surprise guests."
        modified_event.short_description = "Holiday rock concert with surprise guests"

        mock_llm_service = AsyncMock()
        mock_llm_service.generate_descriptions = AsyncMock(return_value=modified_event)
        importer._services["llm"] = mock_llm_service

        # Mock get_cached_event
        cached_data = sample_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 123

        supplementary_context = "This is a special holiday concert with surprise guests"

        with patch("app.core.importer.get_cached_event", return_value=cached_data), \
             patch("app.core.importer.cache_event"):
            result = await importer.rebuild_descriptions(123, supplementary_context=supplementary_context)

            # Verify the result has updated descriptions
            assert result is not None
            assert "surprise guests" in result.short_description
            assert "holiday concert" in result.long_description.lower()

            # Verify LLM service was called with context
            mock_llm_service.generate_descriptions.assert_called_once()
            call_args = mock_llm_service.generate_descriptions.call_args
            assert call_args[1]["force_rebuild"] is True
            assert call_args[1]["supplementary_context"] == supplementary_context

    @pytest.mark.asyncio
    async def test_rebuild_descriptions_not_found(self):
        """Test rebuild when event is not found in cache."""
        importer = EventImporter()

        with patch("app.core.importer.get_cached_event", return_value=None):
            result = await importer.rebuild_descriptions(999)
            assert result is None

    @pytest.mark.asyncio
    async def test_rebuild_descriptions_api_endpoint(self, sample_event_data):
        """Test the API endpoint for rebuilding descriptions."""
        # Mock the router and importer
        mock_router = MagicMock()
        mock_importer = AsyncMock()
        mock_importer.rebuild_descriptions = AsyncMock(return_value=sample_event_data)
        mock_router.importer = mock_importer

        with patch("app.interfaces.api.routes.events.get_router", return_value=mock_router):
            # Test without context
            response = await rebuild_event_descriptions(123)
            assert isinstance(response, RebuildDescriptionResponse)
            assert response.success is True
            assert response.event_id == 123
            assert response.data == sample_event_data

            # Verify importer was called correctly
            mock_importer.rebuild_descriptions.assert_called_with(123, supplementary_context=None)

    @pytest.mark.asyncio
    async def test_rebuild_descriptions_api_endpoint_with_context(self, sample_event_data):
        """Test the API endpoint with supplementary context."""
        mock_router = MagicMock()
        mock_importer = AsyncMock()
        mock_importer.rebuild_descriptions = AsyncMock(return_value=sample_event_data)
        mock_router.importer = mock_importer

        request = RebuildDescriptionRequest(
            supplementary_context="Holiday special with surprise guests"
        )

        with patch("app.interfaces.api.routes.events.get_router", return_value=mock_router):
            response = await rebuild_event_descriptions(123, request=request)
            assert response.success is True

            # Verify context was passed through
            mock_importer.rebuild_descriptions.assert_called_with(
                123,
                supplementary_context="Holiday special with surprise guests"
            )

    @pytest.mark.asyncio
    async def test_rebuild_descriptions_api_endpoint_not_found(self):
        """Test API endpoint when event is not found."""
        mock_router = MagicMock()
        mock_importer = AsyncMock()
        mock_importer.rebuild_descriptions = AsyncMock(return_value=None)
        mock_router.importer = mock_importer

        with patch("app.interfaces.api.routes.events.get_router", return_value=mock_router):
            with pytest.raises(Exception) as exc_info:
                await rebuild_event_descriptions(999)
            assert "404" in str(exc_info.value)


class TestLLMServiceIntegration:
    """Test LLM service integration with supplementary context."""

    @pytest.mark.asyncio
    async def test_claude_service_with_context(self, sample_event_data):
        """Test Claude service generates descriptions with context."""
        config = get_config()
        service = ClaudeService(config)

        # Mock the Claude API call
        mock_response = {
            "long_description": "Enhanced description with context",
            "short_description": "Enhanced short desc"
        }

        with patch.object(service, "_call_with_tool", return_value=mock_response):
            await service.generate_descriptions(
                sample_event_data,
                force_rebuild=True,
                supplementary_context="Add holiday theme"
            )

            # Verify the prompt included the context
            service._call_with_tool.assert_called_once()
            call_args = service._call_with_tool.call_args
            prompt = call_args[0][0]
            assert "Additional Context: Add holiday theme" in prompt

    @pytest.mark.asyncio
    async def test_openai_service_with_context(self, sample_event_data):
        """Test OpenAI service generates descriptions with context."""
        config = get_config()
        service = OpenAIService(config)
        service.client = MagicMock()  # Mock the client

        # Mock the OpenAI API response
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(
                    tool_calls=[
                        MagicMock(
                            function=MagicMock(
                                name="generate_descriptions",
                                arguments='{"long_description": "New long", "short_description": "New short"}'
                            )
                        )
                    ]
                )
            )
        ]

        service.client.chat.completions.create = AsyncMock(return_value=mock_completion)

        await service.generate_descriptions(
            sample_event_data,
            force_rebuild=True,
            supplementary_context="Make it festive"
        )

        # Verify the API was called
        create_call = service.client.chat.completions.create
        create_call.assert_called_once()

        # Check that the prompt includes the context
        messages = create_call.call_args[1]["messages"]
        user_message = messages[0]["content"]
        assert "Additional Context: Make it festive" in user_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
