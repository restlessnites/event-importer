"""Tests for image rebuilding functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.schemas import EventData, ImageCandidate, ImageResult, ImageSearchResult
from app.interfaces.api.server import create_app
from tests.helpers import create_test_importer


class TestRebuildImage:
    """Test image rebuilding functionality."""

    @pytest.fixture
    def mock_event_data(self):
        """Create mock event data."""
        return EventData(
            title="Test Event",
            venue="Test Venue",
            lineup=["Artist 1"],
            images={"full": "https://example.com/old-image.jpg"},
            source_url="https://example.com/event",
        )

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = MagicMock()
        config.api = MagicMock()
        config.api.google_api_key = "test-key"
        config.api.google_cse_id = "test-cse-id"
        return config

    @pytest.fixture
    def mock_image_search_result(self):
        """Create mock image search result."""
        return ImageSearchResult(
            candidates=[
                ImageCandidate(
                    url="https://example.com/image1.jpg",
                    score=90,
                    source="Event Website",
                    dimensions="1200x630",
                    reason="High quality official poster",
                ),
                ImageCandidate(
                    url="https://example.com/image2.jpg",
                    score=70,
                    source="Social Media",
                    dimensions="800x800",
                    reason="Artist promotional image",
                ),
            ],
            selected=ImageCandidate(
                url="https://example.com/image1.jpg",
                score=90,
                source="Event Website",
                dimensions="1200x630",
                reason="High quality official poster",
            ),
        )

    @pytest.mark.asyncio
    async def test_rebuild_image_success(
        self, mock_config, mock_event_data, mock_image_search_result
    ):
        """Test successful image rebuild."""
        importer = create_test_importer(mock_config)

        # Mock database
        cached_data = mock_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_cached_event") as mock_get:
            mock_get.return_value = cached_data

            # Mock image service
            async def mock_enhance_event_image(
                event_data,
                supplementary_context=None,
                force_search=False,
            ):
                # enhance_event_image now returns ImageResult
                return ImageResult(
                    original_image_url=event_data.images.get("full") if event_data.images else None,
                    enhanced_image_url=mock_image_search_result.selected.url,
                    thumbnail_url=mock_image_search_result.selected.url,
                    search_result=mock_image_search_result
                )

            mock_image_service = MagicMock()
            mock_image_service.enhance_event_image = mock_enhance_event_image
            importer.services["image"] = mock_image_service

            # Execute rebuild
            result, failures = await importer.rebuild_image(1)

            # Verify ImageResult
            assert result is not None
            assert result.enhanced_image_url == mock_image_search_result.selected.url
            assert result.thumbnail_url == mock_image_search_result.selected.url
            assert result.search_result == mock_image_search_result
            assert failures == []

    @pytest.mark.asyncio
    async def test_rebuild_image_with_supplementary_context(
        self, mock_config, mock_event_data
    ):
        """Test rebuilding image with supplementary context."""
        importer = create_test_importer(mock_config)

        # Mock database
        cached_data = mock_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_cached_event") as mock_get:
            mock_get.return_value = cached_data

            # Track the call to verify context was passed
            context_passed = None

            async def mock_enhance_event_image(
                event_data,
                supplementary_context=None,
                force_search=False,
            ):
                nonlocal context_passed
                context_passed = supplementary_context
                # Return ImageResult with no enhancement
                return ImageResult(
                    original_image_url=event_data.images.get("full") if event_data.images else None,
                    enhanced_image_url=event_data.images.get("full") if event_data.images else None,
                )

            mock_image_service = MagicMock()
            mock_image_service.enhance_event_image = mock_enhance_event_image
            importer.services["image"] = mock_image_service

            # Execute rebuild with context
            result, failures = await importer.rebuild_image(
                1, supplementary_context="official poster 2024"
            )

            # Verify context was passed
            assert context_passed == "official poster 2024"
            assert result is not None

    @pytest.mark.asyncio
    async def test_rebuild_image_not_found(self, mock_config):
        """Test rebuilding image for non-existent event."""
        importer = create_test_importer(mock_config)

        # Mock database returns None
        with patch("app.core.importer.get_cached_event") as mock_get:
            mock_get.return_value = None

            # Execute rebuild
            result, failures = await importer.rebuild_image(999)

            # Verify
            assert result is None
            assert failures == []

    @pytest.mark.asyncio
    async def test_rebuild_image_no_candidates(self, mock_config, mock_event_data):
        """Test rebuilding image when no candidates found."""
        importer = create_test_importer(mock_config)

        # Mock database
        cached_data = mock_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_cached_event") as mock_get:
            mock_get.return_value = cached_data

            # Mock image service returns no candidates
            async def mock_enhance_event_image(
                event_data,
                supplementary_context=None,
                force_search=False,
            ):
                # Return ImageResult with no enhancement
                return ImageResult(
                    original_image_url=event_data.images.get("full") if event_data.images else None,
                    enhanced_image_url=event_data.images.get("full") if event_data.images else None,
                )

            mock_image_service = MagicMock()
            mock_image_service.enhance_event_image = mock_enhance_event_image
            importer.services["image"] = mock_image_service

            # Execute rebuild
            result, failures = await importer.rebuild_image(1)

            # Verify - no image change when no better image found
            assert result is not None
            assert result.original_image_url == mock_event_data.images.get("full")
            assert result.enhanced_image_url == mock_event_data.images.get("full")  # Same as original

    @pytest.mark.asyncio
    async def test_rebuild_image_api_endpoint(
        self, mock_event_data, mock_image_search_result
    ):
        """Test rebuild image API endpoint."""
        app = create_app()
        client = TestClient(app)

        # Mock event with image search result
        mock_event_with_search = mock_event_data.model_copy()
        mock_event_with_search.image_search = mock_image_search_result

        # Mock the importer
        with patch("app.interfaces.api.routes.events.get_router") as mock_get_router:
            mock_router = MagicMock()
            mock_importer = AsyncMock()
            mock_importer.rebuild_image.return_value = (
                mock_event_with_search,
                [],
            )
            mock_router.importer = mock_importer
            mock_get_router.return_value = mock_router

            # Make request
            response = client.post(
                "/api/v1/events/1/rebuild/image",
                json={"supplementary_context": "festival poster"},
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["image_candidates"]) == 2
            assert data["best_image"]["score"] == 90
            assert data["best_image"]["source"] == "Event Website"

    @pytest.mark.asyncio
    async def test_rebuild_image_with_service_failures(
        self, mock_config, mock_event_data
    ):
        """Test rebuilding image with service failures."""
        importer = create_test_importer(mock_config)

        # Mock database
        cached_data = mock_event_data.model_dump(mode="json")
        cached_data["_db_id"] = 1
        with patch("app.core.importer.get_cached_event") as mock_get:
            mock_get.return_value = cached_data

            # Mock image service with failures
            async def mock_enhance_event_image(
                event_data,
                supplementary_context=None,
                force_search=False,
            ):
                # Raise an exception to simulate failure
                raise Exception("Invalid CSE ID")

            mock_image_service = MagicMock()
            mock_image_service.enhance_event_image = mock_enhance_event_image
            importer.services["image"] = mock_image_service

            # Execute rebuild
            result, failures = await importer.rebuild_image(1)

            # Verify
            assert result is not None
            assert len(failures) == 1
            assert failures[0].service == "image"
            assert "Invalid CSE ID" in failures[0].error

    @pytest.mark.asyncio
    async def test_rebuild_image_api_endpoint_not_found(self):
        """Test rebuild image API endpoint for non-existent event."""
        app = create_app()
        client = TestClient(app)

        # Mock the importer
        with patch("app.interfaces.api.routes.events.get_router") as mock_get_router:
            mock_router = MagicMock()
            mock_importer = AsyncMock()
            mock_importer.rebuild_image.return_value = (None, [])
            mock_router.importer = mock_importer
            mock_get_router.return_value = mock_router

            # Make request
            response = client.post(
                "/api/v1/events/999/rebuild/image",
                json={},
            )

            # Verify
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
