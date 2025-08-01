"""Test event description regeneration functionality - legacy tests for backwards compatibility."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.importer import EventImporter
from app.core.schemas import DescriptionResult, EventData, EventLocation, EventTime
from app.interfaces.api.models.requests import RebuildDescriptionRequest
from app.interfaces.api.models.responses import RebuildDescriptionResponse
from app.interfaces.api.routes.events import rebuild_event_description
from app.services.llm.providers.claude import Claude
from app.services.llm.providers.openai import OpenAI
from app.shared.database.models import Event
from config import config


@pytest.fixture
def sample_event_data():
    """Create sample event data for testing."""
    return EventData(
        title="Test Concert",
        venue="The Fillmore",
        date="2024-12-25",
        time=EventTime(start="20:00"),
        location=EventLocation(city="San Francisco", state="CA", country="USA"),
        lineup=["Artist 1", "Artist 2"],
        genres=["Rock", "Alternative"],
        short_description="Rock concert at The Fillmore",
        long_description="A great rock concert featuring Artist 1 and Artist 2 at the historic Fillmore venue.",
        source_url="https://example.com/event/123",
    )


@pytest.fixture
def mock_event_cache(sample_event_data):
    """Create a mock event cache entry."""
    cache = MagicMock(spec=Event)
    cache.id = 123
    cache.source_url = sample_event_data.source_url
    cache.scraped_data = sample_event_data.model_dump(mode="json")
    return cache


class TestRebuildDescriptions:
    """Test the rebuild descriptions functionality - legacy compatibility."""

    @pytest.mark.asyncio
    async def test_rebuild_descriptions_basic(self, sample_event_data):
        """Test basic description rebuild without supplementary context."""
        # This test maintains backwards compatibility by testing the old flow
        importer = EventImporter(config)

        # Mock the provider with generate_descriptions method
        mock_provider = MagicMock()
        mock_provider.generate_descriptions = AsyncMock(
            return_value=sample_event_data.model_copy(
                update={"short_description": "New short description"}
            )
        )

        # Mock the LLM service to return the provider
        mock_llm_service = MagicMock()
        mock_llm_service.primary_provider = mock_provider
        mock_llm_service.fallback_provider = None
        # Replace service after creation
        importer.services["llm"] = mock_llm_service

        # Mock get_event to return our sample data with _db_id
        cached_data = sample_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 123

        with patch("app.core.importer.get_event", return_value=cached_data):
            # Test the new singular method
            result = await importer.rebuild_description(123, "short")

            # Verify the result returns DescriptionResult
            assert result is not None
            assert result.short_description == "New short description"
            assert result.long_description == sample_event_data.long_description

    @pytest.mark.asyncio
    async def test_rebuild_descriptions_with_context(self, sample_event_data):
        """Test description rebuild with supplementary context."""
        importer = EventImporter(config)

        # Mock the provider to return modified descriptions
        modified_event = sample_event_data.model_copy()
        modified_event.long_description = "An amazing night of rock music featuring Artist 1 and Artist 2 at the legendary Fillmore. This special holiday concert will feature extended sets and surprise guests."
        modified_event.short_description = "Holiday rock concert with surprise guests"

        mock_provider = MagicMock()
        mock_provider.generate_descriptions = AsyncMock(return_value=modified_event)

        # Mock the LLM service to return the provider
        mock_llm_service = MagicMock()
        mock_llm_service.primary_provider = mock_provider
        mock_llm_service.fallback_provider = None
        # Replace service after creation
        importer.services["llm"] = mock_llm_service

        # Mock get_event
        cached_data = sample_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 123

        supplementary_context = "This is a special holiday concert with surprise guests"

        with patch("app.core.importer.get_event", return_value=cached_data):
            result = await importer.rebuild_description(
                123, "long", supplementary_context=supplementary_context
            )

            # Verify the result returns DescriptionResult with updated descriptions
            assert result is not None
            assert "holiday concert" in result.long_description.lower()
            assert (
                result.short_description == "Holiday rock concert with surprise guests"
            )

    @pytest.mark.asyncio
    async def test_rebuild_descriptions_not_found(self):
        """Test rebuild when event is not found in cache."""
        importer = EventImporter(config)

        with patch("app.shared.database.utils.get_event", return_value=None):
            result = await importer.rebuild_description(999, "short")
            assert result is None

    @pytest.mark.asyncio
    async def test_rebuild_descriptions_api_endpoint(self, sample_event_data):
        """Test the API endpoint for rebuilding descriptions."""
        # Mock the router and importer
        mock_router = MagicMock()
        mock_importer = AsyncMock()
        # rebuild_description returns DescriptionResult
        mock_result = DescriptionResult(
            short_description="New short description",
            long_description=sample_event_data.long_description,
        )
        mock_importer.rebuild_description = AsyncMock(return_value=mock_result)
        mock_router.importer = mock_importer

        # Mock database query for fetching event
        mock_db_session = MagicMock()
        mock_event = MagicMock()
        mock_event.scraped_data = sample_event_data.model_dump(mode="json")
        mock_db_session.query().filter().first.return_value = mock_event

        with (
            patch(
                "app.interfaces.api.routes.events.get_router", return_value=mock_router
            ),
            patch("app.interfaces.api.routes.events.get_db_session") as mock_get_db,
        ):
            mock_get_db.return_value.__enter__.return_value = mock_db_session

            # Test without context
            request = RebuildDescriptionRequest(description_type="short")
            response = await rebuild_event_description(123, request)
            assert isinstance(response, RebuildDescriptionResponse)
            assert response.success is True
            assert response.event_id == 123
            assert response.data.short_description == "New short description"

            # Verify importer was called correctly
            mock_importer.rebuild_description.assert_called_with(
                123, description_type="short", supplementary_context=None
            )

    @pytest.mark.asyncio
    async def test_rebuild_descriptions_api_endpoint_with_context(
        self, sample_event_data
    ):
        """Test the API endpoint with supplementary context."""
        mock_router = MagicMock()
        mock_importer = AsyncMock()
        # rebuild_description returns DescriptionResult
        mock_result = DescriptionResult(
            short_description=sample_event_data.short_description,
            long_description="Holiday special long description",
        )
        mock_importer.rebuild_description = AsyncMock(return_value=mock_result)
        mock_router.importer = mock_importer

        # Mock database query for fetching event
        mock_db_session = MagicMock()
        mock_event = MagicMock()
        mock_event.scraped_data = sample_event_data.model_dump(mode="json")
        mock_db_session.query().filter().first.return_value = mock_event

        request = RebuildDescriptionRequest(
            description_type="long",
            supplementary_context="Holiday special with surprise guests",
        )

        with (
            patch(
                "app.interfaces.api.routes.events.get_router", return_value=mock_router
            ),
            patch("app.interfaces.api.routes.events.get_db_session") as mock_get_db,
        ):
            mock_get_db.return_value.__enter__.return_value = mock_db_session
            response = await rebuild_event_description(123, request)
            assert response.success is True

            # Verify context was passed through
            mock_importer.rebuild_description.assert_called_with(
                123,
                description_type="long",
                supplementary_context="Holiday special with surprise guests",
            )

    @pytest.mark.asyncio
    async def test_rebuild_descriptions_api_endpoint_not_found(self):
        """Test API endpoint when event is not found."""
        mock_router = MagicMock()
        mock_importer = AsyncMock()
        mock_importer.rebuild_description = AsyncMock(return_value=None)
        mock_router.importer = mock_importer

        request = RebuildDescriptionRequest(description_type="short")

        with patch(
            "app.interfaces.api.routes.events.get_router", return_value=mock_router
        ):
            with pytest.raises(Exception) as exc_info:
                await rebuild_event_description(999, request)
            assert "404" in str(exc_info.value)


class TestLLMServiceIntegration:
    """Test LLM service integration with supplementary context."""

    @pytest.mark.asyncio
    async def test_claude_service_with_context(self, sample_event_data):
        """Test Claude service generates descriptions with context."""
        service = Claude(config)

        # Mock the Claude API call
        mock_response = {
            "long_description": "Enhanced description with context",
            "short_description": "Enhanced short desc",
        }

        with patch.object(service, "_call_with_tool", return_value=mock_response):
            await service.generate_descriptions(
                sample_event_data,
                needs_long=True,
                needs_short=True,
                supplementary_context="Add holiday theme",
            )

            # Verify the prompt included the context
            service._call_with_tool.assert_called_once()
            call_args = service._call_with_tool.call_args
            prompt = call_args[0][0]
            assert "Additional Context: Add holiday theme" in prompt

    @pytest.mark.asyncio
    async def test_openai_service_with_context(self, sample_event_data):
        """Test OpenAI service generates descriptions with context."""
        service = OpenAI(config)
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
                                arguments='{"long_description": "New long", "short_description": "New short"}',
                            )
                        )
                    ]
                )
            )
        ]

        service.client.chat.completions.create = AsyncMock(return_value=mock_completion)

        await service.generate_descriptions(
            sample_event_data,
            needs_long=True,
            needs_short=True,
            supplementary_context="Make it festive",
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
