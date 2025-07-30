"""Test event update functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_config
from app.core.importer import EventImporter
from app.interfaces.api.models.requests import UpdateEventRequest
from app.interfaces.api.routes.events import update_event
from app.schemas import EventData, EventLocation, EventTime


@pytest.fixture
def sample_event_data():
    """Create sample event data for testing."""
    return EventData(
        title="Original Concert",
        venue="Original Venue",
        date="2024-01-01",
        time=EventTime(start="20:00", end="23:00", timezone="America/Los_Angeles"),
        location=EventLocation(
            city="Los Angeles", state="California", country="United States"
        ),
        short_description="Original short description",
        long_description="Original long description",
        genres=["Rock"],
        lineup=["Band A", "Band B"],
        minimum_age="21+",
        cost="$25",
        source_url="https://example.com/event",
    )


class TestUpdateEvent:
    """Test cases for event updates."""

    @pytest.mark.asyncio
    async def test_update_single_field(self, sample_event_data):
        """Test updating a single field."""
        cached_event = sample_event_data.model_dump(mode="json")
        cached_event["_db_id"] = 123

        with (
            patch("app.core.importer.get_cached_event") as mock_get_cached,
            patch("app.core.importer.cache_event") as mock_cache,
        ):
            mock_get_cached.return_value = cached_event

            importer = EventImporter(get_config())
            result = await importer.update_event(123, {"venue": "New Venue"})

            assert result is not None
            assert result.venue == "New Venue"
            assert result.title == "Original Concert"  # Unchanged
            mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, sample_event_data):
        """Test updating multiple fields."""
        cached_event = sample_event_data.model_dump(mode="json")
        cached_event["_db_id"] = 123

        updates = {
            "venue": "New Venue",
            "date": "2024-02-01",
            "minimum_age": "18+",
            "genres": ["Electronic", "House"],
        }

        with (
            patch("app.core.importer.get_cached_event") as mock_get_cached,
            patch("app.core.importer.cache_event"),
        ):
            mock_get_cached.return_value = cached_event

            importer = EventImporter(get_config())
            result = await importer.update_event(123, updates)

            assert result is not None
            assert result.venue == "New Venue"
            assert result.date == "2024-02-01"
            assert result.minimum_age == "18+"
            assert result.genres == ["Electronic", "House"]
            assert result.title == "Original Concert"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_time_structure(self, sample_event_data):
        """Test updating time with proper EventTime conversion."""
        cached_event = sample_event_data.model_dump(mode="json")
        cached_event["_db_id"] = 123

        new_time = {"start": "19:00", "end": "02:00", "timezone": "America/New_York"}

        with (
            patch("app.core.importer.get_cached_event") as mock_get_cached,
            patch("app.core.importer.cache_event"),
        ):
            mock_get_cached.return_value = cached_event

            importer = EventImporter(get_config())
            result = await importer.update_event(123, {"time": new_time})

            assert result is not None
            assert isinstance(result.time, EventTime)
            assert result.time.start == "19:00"
            assert result.time.end == "02:00"
            assert result.time.timezone == "America/New_York"

    @pytest.mark.asyncio
    async def test_update_multi_day_event(self, sample_event_data):
        """Test updating to multi-day event with end_date."""
        cached_event = sample_event_data.model_dump(mode="json")
        cached_event["_db_id"] = 123

        updates = {"date": "2024-07-15", "end_date": "2024-07-17"}

        with (
            patch("app.core.importer.get_cached_event") as mock_get_cached,
            patch("app.core.importer.cache_event"),
        ):
            mock_get_cached.return_value = cached_event

            importer = EventImporter(get_config())
            result = await importer.update_event(123, updates)

            assert result is not None
            assert result.date == "2024-07-15"
            assert result.end_date == "2024-07-17"

    @pytest.mark.asyncio
    async def test_update_event_not_found(self):
        """Test updating non-existent event."""
        with patch("app.core.importer.get_cached_event") as mock_get_cached:
            mock_get_cached.return_value = None

            importer = EventImporter(get_config())
            result = await importer.update_event(999, {"venue": "New Venue"})

            assert result is None

    @pytest.mark.asyncio
    async def test_update_invalid_field(self, sample_event_data):
        """Test updating with invalid field name."""
        cached_event = sample_event_data.model_dump(mode="json")
        cached_event["_db_id"] = 123

        with (
            patch("app.core.importer.get_cached_event") as mock_get_cached,
            patch("app.core.importer.cache_event"),
        ):
            mock_get_cached.return_value = cached_event

            importer = EventImporter(get_config())
            # Should still work but ignore invalid field
            result = await importer.update_event(123, {"invalid_field": "value"})

            assert result is not None
            # Event should be unchanged except for validation
            assert result.title == "Original Concert"

    @pytest.mark.asyncio
    async def test_update_event_api_endpoint(self, sample_event_data):
        """Test the API endpoint for updating events."""
        mock_router = MagicMock()
        mock_importer = MagicMock()
        mock_router.importer = mock_importer
        mock_importer.update_event = AsyncMock(return_value=sample_event_data)

        request = UpdateEventRequest(venue="New Venue", date="2024-02-01")

        with patch(
            "app.interfaces.api.routes.events.get_router", return_value=mock_router
        ):
            response = await update_event(123, request)

            assert response.success is True
            assert response.event_id == 123
            assert "2 field(s)" in response.message
            assert response.updated_fields == ["venue", "date"]
            assert response.data == sample_event_data

    @pytest.mark.asyncio
    async def test_update_event_api_no_fields(self):
        """Test API endpoint with no fields to update."""
        mock_router = MagicMock()

        request = UpdateEventRequest()

        with patch(
            "app.interfaces.api.routes.events.get_router", return_value=mock_router
        ):
            with pytest.raises(Exception) as exc_info:
                await update_event(123, request)

            assert "No fields provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_short_description_length(self, sample_event_data):
        """Test updating short description respects length limit."""
        cached_event = sample_event_data.model_dump(mode="json")
        cached_event["_db_id"] = 123

        # Create a description that's within the 200 char limit
        new_description = "A" * 190

        with (
            patch("app.core.importer.get_cached_event") as mock_get_cached,
            patch("app.core.importer.cache_event"),
        ):
            mock_get_cached.return_value = cached_event

            importer = EventImporter(get_config())
            result = await importer.update_event(
                123, {"short_description": new_description}
            )

            assert result is not None
            assert result.short_description == new_description
            assert len(result.short_description) <= 200
