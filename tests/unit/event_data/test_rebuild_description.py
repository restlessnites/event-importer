"""Test event description regeneration functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_config
from app.core.schemas import DescriptionResult, EventData, EventLocation, EventTime
from app.interfaces.api.models.requests import RebuildDescriptionRequest
from app.interfaces.api.routes.events import rebuild_event_description
from app.services.llm.providers.claude import Claude
from app.services.llm.service import LLMService
from tests.helpers import create_test_importer


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

            # Create a mock provider with generate_descriptions method
            mock_provider = MagicMock()
            mock_provider.generate_descriptions = AsyncMock(
                return_value=sample_event_data.model_copy(
                    update={"short_description": "New short description"}
                )
            )

            # Create a mock LLM service that returns the provider
            mock_llm_service = MagicMock()
            mock_llm_service.primary_provider = mock_provider
            mock_llm_service.fallback_provider = None

            importer = create_test_importer(get_config(), {"llm": mock_llm_service})

            result = await importer.rebuild_description(
                123, description_type="short", supplementary_context="Make it exciting"
            )

            assert result is not None
            assert result.short_description == "New short description"
            assert result.long_description == sample_event_data.long_description

            # Update the assertion to check the call was made with correct params
            expected_event = sample_event_data.model_copy()
            expected_event.short_description = None  # This is cleared before calling
            mock_provider.generate_descriptions.assert_called_once_with(
                expected_event,
                needs_long=False,
                needs_short=True,
                supplementary_context="Make it exciting",
            )

    @pytest.mark.asyncio
    async def test_rebuild_long_description(self, sample_event_data):
        """Test rebuilding long description."""
        cached_event = sample_event_data.model_dump(mode="json")
        cached_event["_db_id"] = 123

        with patch("app.core.importer.get_cached_event") as mock_get_cached:
            mock_get_cached.return_value = cached_event

            # Create a mock provider with generate_descriptions method
            mock_provider = MagicMock()
            mock_provider.generate_descriptions = AsyncMock(
                return_value=sample_event_data.model_copy(
                    update={
                        "long_description": "New detailed long description with more information"
                    }
                )
            )

            # Create a mock LLM service that returns the provider
            mock_llm_service = MagicMock()
            mock_llm_service.primary_provider = mock_provider
            mock_llm_service.fallback_provider = None

            importer = create_test_importer(get_config(), {"llm": mock_llm_service})

            result = await importer.rebuild_description(
                123, description_type="long", supplementary_context="Add venue details"
            )

            assert result is not None
            assert result.short_description == sample_event_data.short_description
            assert (
                result.long_description
                == "New detailed long description with more information"
            )

            # Update the assertion to check the call was made with correct params
            expected_event = sample_event_data.model_copy()
            expected_event.long_description = None  # This is cleared before calling
            mock_provider.generate_descriptions.assert_called_once_with(
                expected_event,
                needs_long=True,
                needs_short=False,
                supplementary_context="Add venue details",
            )

    @pytest.mark.asyncio
    async def test_rebuild_description_not_found(self):
        """Test rebuilding description for non-existent event."""
        with patch("app.core.importer.get_cached_event") as mock_get_cached:
            mock_get_cached.return_value = None

            importer = create_test_importer(get_config())
            result = await importer.rebuild_description(999, "short")

            assert result is None

    @pytest.mark.asyncio
    async def test_rebuild_description_api_endpoint(self, sample_event_data):
        """Test the API endpoint for rebuilding descriptions."""
        mock_router = MagicMock()
        mock_importer = MagicMock()
        mock_router.importer = mock_importer

        # rebuild_description returns DescriptionResult, not EventData
        mock_result = DescriptionResult(
            short_description="New short description",
            long_description=sample_event_data.long_description,
        )
        mock_importer.rebuild_description = AsyncMock(return_value=mock_result)

        request = RebuildDescriptionRequest(
            description_type="short", supplementary_context="Make it exciting"
        )

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

            response = await rebuild_event_description(123, request)

            assert response.success is True
            assert response.event_id == 123
            assert "preview only" in response.message.lower()
            # The API should return EventData with the new description
            assert response.data.short_description == "New short description"
            assert response.data.long_description == sample_event_data.long_description
            mock_importer.rebuild_description.assert_called_with(
                123, description_type="short", supplementary_context="Make it exciting"
            )


class TestLLMServiceGeneration:
    """Test LLM service individual description generation."""

    @pytest.mark.asyncio
    async def test_generate_short_description(self, sample_event_data):
        """Test generating only short description."""
        mock_claude = MagicMock(spec=Claude)
        mock_claude.generate_descriptions = AsyncMock(
            return_value=sample_event_data.model_copy(
                update={"short_description": "Claude short description"}
            )
        )

        llm_service = LLMService(get_config())
        llm_service.primary_provider = mock_claude

        # Remove long description to ensure short is generated
        test_data = sample_event_data.model_copy(update={"short_description": None})
        result = await llm_service.generate_descriptions(test_data)

        assert result.short_description == "Claude short description"

    @pytest.mark.asyncio
    async def test_generate_long_description(self, sample_event_data):
        """Test generating only long description."""
        mock_claude = MagicMock(spec=Claude)
        mock_claude.generate_descriptions = AsyncMock(
            return_value=sample_event_data.model_copy(
                update={"long_description": "Claude detailed long description"}
            )
        )

        llm_service = LLMService(get_config())
        llm_service.primary_provider = mock_claude

        # Remove short description to ensure long is generated
        test_data = sample_event_data.model_copy(update={"long_description": None})
        result = await llm_service.generate_descriptions(test_data)
        assert result.long_description == "Claude detailed long description"
