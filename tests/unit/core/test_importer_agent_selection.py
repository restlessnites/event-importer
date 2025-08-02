"""Test the EventImporter agent selection logic including image detection."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientResponse

from app.core.importer import EventImporter
from app.core.schemas import ImportMethod
from app.extraction_agents.providers.dice import Dice
from app.extraction_agents.providers.image import Image
from app.extraction_agents.providers.ra import ResidentAdvisor
from app.extraction_agents.providers.ticketmaster import Ticketmaster
from app.extraction_agents.providers.web import Web
from config import Config

# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"
TEST_IMAGE_PATH = FIXTURES_DIR / "test_event_flyer.jpg"


@pytest.fixture
def test_image_data():
    """Load test image data from fixture file."""
    if TEST_IMAGE_PATH.exists():
        with TEST_IMAGE_PATH.open('rb') as f:
            return f.read()
    # Fallback to a simple test image if fixture doesn't exist
    return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'


@pytest.fixture
def test_image_url():
    """Return a consistent test image URL."""
    return f"file://{TEST_IMAGE_PATH}"


@pytest.fixture
def config():
    """Create a test config."""
    config = MagicMock(spec=Config)
    # API configuration
    config.api = MagicMock()
    config.api.anthropic_api_key = "test-claude-key"
    config.api.openai_api_key = "test-openai-key"
    config.api.google_api_key = "test-google-key"
    config.api.google_cse_id = "test-cse-id"
    config.api.zyte_api_key = "test-zyte-key"
    config.api.ticketfairy_api_key = None
    # HTTP configuration
    config.http = MagicMock()
    config.http.timeout = 30
    config.http.max_retries = 3
    # Legacy attributes for backward compatibility
    config.llm = MagicMock()
    config.llm.claude_api_key = "test-claude-key"
    config.llm.openai_api_key = "test-openai-key"
    config.google = MagicMock()
    config.google.api_key = "test-google-key"
    config.google.cse_id = "test-cse-id"
    config.ticketfairy = MagicMock()
    config.ticketfairy.api_key = None
    config.zyte = MagicMock()
    config.zyte.api_key = "test-zyte-key"
    return config


@pytest.fixture
def importer(config):
    """Create an EventImporter instance."""
    with patch("app.core.importer.get_available_integrations", return_value={}):
        return EventImporter(config)


class TestImageDetection:
    """Test image detection via content-type."""

    @pytest.mark.asyncio
    async def test_detect_image_jpeg(self, importer):
        """Test that JPEG content-type is detected as image."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.headers = {"content-type": "image/jpeg"}

        with patch.object(importer, "get_service") as mock_get_service:
            mock_http = AsyncMock()
            mock_http.head = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_http

            method = await importer._detect_import_method("https://example.com/image.jpg")
            assert method == ImportMethod.IMAGE

    @pytest.mark.asyncio
    async def test_detect_image_png(self, importer):
        """Test that PNG content-type is detected as image."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.headers = {"content-type": "image/png"}

        with patch.object(importer, "get_service") as mock_get_service:
            mock_http = AsyncMock()
            mock_http.head = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_http

            method = await importer._detect_import_method("https://example.com/image.png")
            assert method == ImportMethod.IMAGE

    @pytest.mark.asyncio
    async def test_detect_image_octet_stream(self, importer):
        """Test that application/octet-stream is detected as image."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.headers = {"content-type": "application/octet-stream"}

        with patch.object(importer, "get_service") as mock_get_service:
            mock_http = AsyncMock()
            mock_http.head = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_http

            method = await importer._detect_import_method("https://example.com/file.bin")
            assert method == ImportMethod.IMAGE

    @pytest.mark.asyncio
    async def test_detect_html(self, importer):
        """Test that HTML content-type is detected as web."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}

        with patch.object(importer, "get_service") as mock_get_service:
            mock_http = AsyncMock()
            mock_http.head = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_http

            method = await importer._detect_import_method("https://example.com/page.html")
            assert method == ImportMethod.WEB

    @pytest.mark.asyncio
    async def test_detect_text(self, importer):
        """Test that text content-type is detected as web."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.headers = {"content-type": "text/plain"}

        with patch.object(importer, "get_service") as mock_get_service:
            mock_http = AsyncMock()
            mock_http.head = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_http

            method = await importer._detect_import_method("https://example.com/file.txt")
            assert method == ImportMethod.WEB

    @pytest.mark.asyncio
    async def test_detect_unknown_defaults_to_web(self, importer):
        """Test that unknown content-type defaults to web."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.headers = {"content-type": "application/json"}

        with patch.object(importer, "get_service") as mock_get_service:
            mock_http = AsyncMock()
            mock_http.head = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_http

            method = await importer._detect_import_method("https://example.com/data.json")
            assert method == ImportMethod.WEB

    @pytest.mark.asyncio
    async def test_detect_head_request_fails_defaults_to_web(self, importer):
        """Test that HEAD request failure defaults to web."""
        with patch.object(importer, "get_service") as mock_get_service:
            mock_http = AsyncMock()
            mock_http.head = AsyncMock(side_effect=Exception("Network error"))
            mock_get_service.return_value = mock_http

            method = await importer._detect_import_method("https://example.com/page")
            assert method == ImportMethod.WEB

    @pytest.mark.asyncio
    async def test_detect_missing_content_type_defaults_to_web(self, importer):
        """Test that missing content-type header defaults to web."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.headers = {}

        with patch.object(importer, "get_service") as mock_get_service:
            mock_http = AsyncMock()
            mock_http.head = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_http

            method = await importer._detect_import_method("https://example.com/page")
            assert method == ImportMethod.WEB


class TestAgentSelection:
    """Test the _select_agent method with various scenarios."""

    @pytest.mark.asyncio
    async def test_select_agent_resident_advisor(self, importer):
        """Test that RA URLs get the RA agent."""
        agent = await importer._select_agent("https://ra.co/events/123456", "test-id")
        assert isinstance(agent, ResidentAdvisor)

    @pytest.mark.asyncio
    async def test_select_agent_ticketmaster(self, importer):
        """Test that Ticketmaster URLs get the Ticketmaster agent."""
        agent = await importer._select_agent("https://www.ticketmaster.com/event/ABC123", "test-id")
        assert isinstance(agent, Ticketmaster)

    @pytest.mark.asyncio
    async def test_select_agent_dice(self, importer):
        """Test that Dice URLs get the Dice agent."""
        agent = await importer._select_agent("https://dice.fm/event/test-event", "test-id")
        assert isinstance(agent, Dice)

    @pytest.mark.asyncio
    async def test_select_agent_unknown_web_page(self, importer):
        """Test that unknown URLs with HTML content get the Web agent."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.headers = {"content-type": "text/html"}

        with patch.object(importer, "get_service") as mock_get_service:
            mock_http = AsyncMock()
            mock_http.head = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_http

            agent = await importer._select_agent("https://shrineauditorium.com/events/123", "test-id")
            assert isinstance(agent, Web)

    @pytest.mark.asyncio
    async def test_select_agent_unknown_image_url(self, importer):
        """Test that unknown URLs with image content get the Image agent."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.headers = {"content-type": "image/jpeg"}

        with patch.object(importer, "get_service") as mock_get_service:
            mock_http = AsyncMock()
            mock_http.head = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_http

            agent = await importer._select_agent("https://example.com/flyer.jpg", "test-id")
            assert isinstance(agent, Image)

    @pytest.mark.asyncio
    async def test_select_agent_unknown_defaults_to_web(self, importer):
        """Test that unknown URLs with no content-type detection default to Web agent."""
        with patch.object(importer, "get_service") as mock_get_service:
            mock_http = AsyncMock()
            mock_http.head = AsyncMock(side_effect=Exception("Failed"))
            mock_get_service.return_value = mock_http

            agent = await importer._select_agent("https://unknown-site.com/event", "test-id")
            assert isinstance(agent, Web)

    @pytest.mark.asyncio
    async def test_select_agent_shrine_auditorium(self, importer):
        """Test the specific Shrine Auditorium case that was failing."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}

        with patch.object(importer, "get_service") as mock_get_service:
            mock_http = AsyncMock()
            mock_http.head = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_http

            # This was the URL that was failing before our fix
            agent = await importer._select_agent(
                "https://www.shrineauditorium.com/events/detail/event_id=875456",
                "test-id"
            )
            assert isinstance(agent, Web)

    @pytest.mark.asyncio
    async def test_select_agent_local_test_image(self, importer, test_image_url):
        """Test agent selection with local test image fixture."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.headers = {"content-type": "image/jpeg"}

        with patch.object(importer, "get_service") as mock_get_service:
            mock_http = AsyncMock()
            mock_http.head = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_http

            # Use the local test image fixture
            agent = await importer._select_agent(test_image_url, "test-id")
            assert isinstance(agent, Image)
