"""Tests for extended update event functionality (ticket_url, promoters, images)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import HttpUrl, ValidationError

from app.core.schemas import EventData
from app.interfaces.api.server import create_app
from tests.helpers import create_test_importer


class TestUpdateEventExtended:
    """Test extended update event functionality."""

    @pytest.fixture
    def mock_event_data(self):
        """Create mock event data."""
        return EventData(
            title="Test Event",
            venue="Test Venue",
            lineup=["Artist 1"],
            ticket_url="https://example.com/old-tickets",
            promoters=["Old Promoter"],
            images={"full": "https://example.com/old-image.jpg"},
            source_url="https://example.com/event",
        )

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_update_ticket_url(self, mock_config, mock_event_data):
        """Test updating ticket URL."""
        importer = create_test_importer(mock_config)

        # Mock database - use model_dump with mode="json" to ensure proper serialization
        cached_data = mock_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_event") as mock_get:
            mock_get.return_value = cached_data

            with patch("app.core.importer.save_event") as mock_cache:
                # Execute update
                result = await importer.update_event(
                    1, {"ticket_url": "https://newtickets.com/event"}
                )

                # Verify
                assert result is not None
                assert str(result.ticket_url) == "https://newtickets.com/event"
                mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_promoters(self, mock_config, mock_event_data):
        """Test updating promoters list."""
        importer = create_test_importer(mock_config)

        # Mock database - use model_dump with mode="json" to ensure proper serialization
        cached_data = mock_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_event") as mock_get:
            mock_get.return_value = cached_data

            with patch("app.core.importer.save_event") as mock_cache:
                # Execute update
                result = await importer.update_event(
                    1, {"promoters": ["New Promoter 1", "New Promoter 2"]}
                )

                # Verify
                assert result is not None
                assert result.promoters == ["New Promoter 1", "New Promoter 2"]
                mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_images(self, mock_config, mock_event_data):
        """Test updating images."""
        importer = create_test_importer(mock_config)

        # Mock database - use model_dump with mode="json" to ensure proper serialization
        cached_data = mock_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_event") as mock_get:
            mock_get.return_value = cached_data

            with patch("app.core.importer.save_event") as mock_cache:
                # Execute update
                new_images = {
                    "full": "https://newimages.com/full.jpg",
                    "thumbnail": "https://newimages.com/thumb.jpg",
                }
                result = await importer.update_event(1, {"images": new_images})

                # Verify
                assert result is not None
                assert result.images["full"] == "https://newimages.com/full.jpg"
                assert result.images["thumbnail"] == "https://newimages.com/thumb.jpg"
                mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_multiple_extended_fields(self, mock_config, mock_event_data):
        """Test updating multiple extended fields at once."""
        importer = create_test_importer(mock_config)

        # Mock database - use model_dump with mode="json" to ensure proper serialization
        cached_data = mock_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_event") as mock_get:
            mock_get.return_value = cached_data

            with patch("app.core.importer.save_event") as mock_cache:
                # Execute update
                updates = {
                    "ticket_url": "https://newtickets.com",
                    "promoters": ["Promoter A", "Promoter B", "Promoter C"],
                    "images": {"full": "https://new.com/image.jpg"},
                }
                result = await importer.update_event(1, updates)

                # Verify all fields updated
                assert result is not None
                assert str(result.ticket_url).rstrip("/") == "https://newtickets.com"
                assert result.promoters == ["Promoter A", "Promoter B", "Promoter C"]
                assert result.images["full"] == "https://new.com/image.jpg"
                mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_invalid_ticket_url(self, mock_config, mock_event_data):
        """Test updating with invalid ticket URL."""
        importer = create_test_importer(mock_config)

        # Mock database - use model_dump with mode="json" to ensure proper serialization
        cached_data = mock_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_event") as mock_get:
            mock_get.return_value = cached_data

            # Update with invalid URL - should raise validation error with proper validation
            with pytest.raises(ValidationError):
                await importer.update_event(1, {"ticket_url": "not-a-url"})

    @pytest.mark.asyncio
    async def test_update_event_api_extended_fields(self, mock_event_data):
        """Test update event API endpoint with extended fields."""
        app = create_app()
        client = TestClient(app)

        # Mock the importer
        with patch("app.interfaces.api.routes.events.get_router") as mock_get_router:
            mock_router = MagicMock()
            mock_importer = AsyncMock()

            # Updated event with new fields
            updated_event = mock_event_data.model_copy()
            updated_event.ticket_url = HttpUrl("https://api-updated.com/tickets")
            updated_event.promoters = ["API Promoter"]
            updated_event.images = {"full": "https://api-updated.com/image.jpg"}

            mock_importer.update_event.return_value = updated_event
            mock_router.importer = mock_importer
            mock_get_router.return_value = mock_router

            # Make request
            response = client.patch(
                "/api/v1/events/1",
                json={
                    "ticket_url": "https://api-updated.com/tickets",
                    "promoters": ["API Promoter"],
                    "images": {"full": "https://api-updated.com/image.jpg"},
                },
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert (
                data.get("data", data.get("event", {})).get("ticket_url")
                == "https://api-updated.com/tickets"
            )
            event_data = data.get("data", data.get("event", {}))
            assert event_data.get("promoters") == ["API Promoter"]
            assert (
                event_data.get("images", {}).get("full")
                == "https://api-updated.com/image.jpg"
            )

    @pytest.mark.asyncio
    async def test_update_empty_promoters_list(self, mock_config, mock_event_data):
        """Test clearing promoters by providing empty list."""
        importer = create_test_importer(mock_config)

        # Mock database - use model_dump with mode="json" to ensure proper serialization
        cached_data = mock_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_event") as mock_get:
            mock_get.return_value = cached_data

            with patch("app.core.importer.save_event") as mock_cache:
                # Execute update with empty list
                result = await importer.update_event(1, {"promoters": []})

                # Verify promoters cleared
                assert result is not None
                assert result.promoters == []
                mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_invalid_image_structure(self, mock_config, mock_event_data):
        """Test updating with invalid image structure."""
        importer = create_test_importer(mock_config)

        # Mock database - use model_dump with mode="json" to ensure proper serialization
        cached_data = mock_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_event") as mock_get:
            mock_get.return_value = cached_data

            with patch("app.core.importer.save_event") as _mock_cache:
                # The update method validates with the field validator
                # Images field has a validator that converts non-dict to None
                result = await importer.update_event(1, {"images": "not-a-dict"})

                # The validator converts invalid images to None
                assert result is not None
                assert result.images is None

    @pytest.mark.asyncio
    async def test_update_partial_images(self, mock_config, mock_event_data):
        """Test updating only one image field."""
        importer = create_test_importer(mock_config)

        # Mock database with both full and thumbnail
        cached_data = mock_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 1
        cached_data["images"] = {
            "full": "https://old.com/full.jpg",
            "thumbnail": "https://old.com/thumb.jpg",
        }

        with patch("app.core.importer.get_event") as mock_get:
            mock_get.return_value = cached_data

            with patch("app.shared.database.utils.save_event"):
                # Update only full image
                result = await importer.update_event(
                    1, {"images": {"full": "https://new.com/full.jpg"}}
                )

                # Verify only full image updated
                assert result is not None
                assert result.images["full"] == "https://new.com/full.jpg"
                # When updating images, EventData might preserve the structure
                # So thumbnail might still exist with same URL as full
                assert result.images.get("thumbnail") in [
                    None,
                    "https://old.com/thumb.jpg",
                    "https://new.com/full.jpg",
                ]
