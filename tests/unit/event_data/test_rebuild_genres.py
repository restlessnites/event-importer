"""Tests for genre rebuilding functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.importer import EventImporter
from app.errors import APIError
from app.interfaces.api.server import create_app
from app.schemas import EventData, ServiceFailure


class TestRebuildGenres:
    """Test genre rebuilding functionality."""

    @pytest.fixture
    def mock_event_data(self):
        """Create mock event data."""
        return EventData(
            title="Test Event",
            lineup=["Artist 1", "Artist 2"],
            genres=["Rock"],
            source_url="https://example.com/event",
        )

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = MagicMock()
        config.api = MagicMock()
        config.api.anthropic_api_key = "test-key"
        config.api.openai_api_key = "test-key"
        config.api.google_api_key = "test-key"
        config.api.google_cse_id = "test-cse-id"
        return config

    @pytest.mark.asyncio
    async def test_rebuild_genres_with_lineup(self, mock_config, mock_event_data):
        """Test rebuilding genres for event with lineup."""
        importer = EventImporter(mock_config)

        # Mock database - return dict with _db_id
        cached_data = mock_event_data.model_dump()
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_cached_event") as mock_get:
            mock_get.return_value = cached_data

            # Mock genre service to update the event's genres
            async def mock_enhance_genres(event_data, supplementary_context=None):
                # Return the same event with updated genres
                event_data.genres = ["Electronic", "House", "Techno"]
                return event_data

            # Mock the services dictionary in importer
            mock_genre_service = MagicMock()
            mock_genre_service.enhance_genres = mock_enhance_genres
            importer._services = {"genre": mock_genre_service}

            # Execute rebuild
            result, failures = await importer.rebuild_genres(1)

            # Verify
            assert result is not None
            assert result.genres == ["Electronic", "House", "Techno"]
            assert failures == []

    @pytest.mark.asyncio
    async def test_rebuild_genres_without_lineup(self, mock_config):
        """Test rebuilding genres for event without lineup requires context."""
        importer = EventImporter(mock_config)

        # Mock event without lineup
        mock_event = EventData(
            title="Test Event",
            lineup=[],  # No lineup
            genres=[],
            source_url="https://example.com/event",
        )

        # Mock database
        cached_data = mock_event.model_dump()
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_cached_event") as mock_get:
            mock_get.return_value = cached_data

            # Mock genre service that will raise error
            async def mock_enhance_genres(event_data, supplementary_context=None):
                if not event_data.lineup and not supplementary_context:
                    raise ValueError(
                        "Cannot search for genres: Event has no lineup. "
                        "Please provide artist names in supplementary_context parameter."
                    )
                return event_data

            mock_genre_service = MagicMock()
            mock_genre_service.enhance_genres = mock_enhance_genres
            importer._services = {"genre": mock_genre_service}

            # Should return the event but with empty genres and error in failures
            result, failures = await importer.rebuild_genres(1)

            # The method returns the event even if enhancement fails
            assert result is not None
            assert result.genres == []
            assert len(failures) == 1
            assert "no lineup" in str(failures[0])

    @pytest.mark.asyncio
    async def test_rebuild_genres_with_supplementary_context(self, mock_config):
        """Test rebuilding genres with supplementary context."""
        importer = EventImporter(mock_config)

        # Mock event without lineup
        mock_event = EventData(
            title="Test Event",
            lineup=[],
            genres=[],
            source_url="https://example.com/event",
        )

        # Mock database
        cached_data = mock_event.model_dump()
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_cached_event") as mock_get:
            mock_get.return_value = cached_data

            # Mock genre service
            async def mock_enhance_genres(event_data, supplementary_context=None):
                if supplementary_context:
                    event_data.genres = ["Ambient", "IDM"]
                return event_data

            mock_genre_service = MagicMock()
            mock_genre_service.enhance_genres = mock_enhance_genres
            importer._services = {"genre": mock_genre_service}

            # Execute rebuild with context
            result, failures = await importer.rebuild_genres(
                1, supplementary_context="Boards of Canada"
            )

            # Verify
            assert result is not None
            # The mock should have updated genres since supplementary_context was provided
            assert result.genres == ["Ambient", "IDM"]

    @pytest.mark.asyncio
    async def test_rebuild_genres_not_found(self, mock_config):
        """Test rebuilding genres for non-existent event."""
        importer = EventImporter(mock_config)

        # Mock database returns None
        with patch("app.core.importer.get_cached_event") as mock_get:
            mock_get.return_value = None

            # Execute rebuild
            result, failures = await importer.rebuild_genres(999)

            # Verify
            assert result is None
            assert failures == []

    @pytest.mark.asyncio
    async def test_rebuild_genres_api_endpoint(self, mock_event_data):
        """Test rebuild genres API endpoint."""
        app = create_app()
        client = TestClient(app)

        # Mock the importer
        with patch("app.interfaces.api.routes.events.get_router") as mock_get_router:
            mock_router = MagicMock()
            mock_importer = AsyncMock()

            # Return updated event data with new genres
            updated_event = mock_event_data.model_copy()
            updated_event.genres = ["Electronic", "House"]

            mock_importer.rebuild_genres.return_value = (
                updated_event,
                [ServiceFailure(service="TestService", error="Test error")],
            )
            mock_router.importer = mock_importer
            mock_get_router.return_value = mock_router

            # Make request
            response = client.post(
                "/api/v1/events/1/rebuild/genres",
                json={"supplementary_context": "Electronic artists"},
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "genres" in data["data"] or data.get("genres") == [
                "Electronic",
                "House",
            ]
            assert len(data["service_failures"]) == 1
            assert data["service_failures"][0]["service"] == "TestService"

    @pytest.mark.asyncio
    async def test_rebuild_genres_with_service_failures(
        self, mock_config, mock_event_data
    ):
        """Test rebuilding genres with service failures."""
        importer = EventImporter(mock_config)

        # Mock database
        cached_data = mock_event_data.model_dump()
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_cached_event") as mock_get:
            mock_get.return_value = cached_data

            # Mock genre service that partially fails
            async def mock_enhance_genres(event_data, supplementary_context=None):
                # The actual enhance_genres method doesn't take failure_collector
                # It throws exceptions which are caught by rebuild_genres
                # Raise an API error that will be caught
                raise APIError("GoogleSearch", "API key not configured")

            mock_genre_service = MagicMock()
            mock_genre_service.enhance_genres = mock_enhance_genres
            importer._services = {"genre": mock_genre_service}

            # Execute rebuild
            result, failures = await importer.rebuild_genres(1)

            # Verify
            assert result is not None
            # When enhance_genres fails, genres are cleared (as per line 598 in importer.py)
            assert result.genres == []  # Genres were cleared before enhancement
            assert len(failures) == 1
            assert (
                failures[0].service == "GoogleSearch"
                if hasattr(failures[0], "service")
                else failures[0]["service"] == "GoogleSearch"
            )
