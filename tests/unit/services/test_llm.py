"""Tests for LLM service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Config
from app.core.errors import ConfigurationError
from app.core.schemas import EventData
from app.services.llm.service import LLMService


@pytest.fixture
def mock_config():
    """Create a mock config with API keys."""
    config = MagicMock(spec=Config)
    config.api = MagicMock()
    config.api.anthropic_api_key = "test-claude-key"
    config.api.openai_api_key = "test-openai-key"
    config.processing = MagicMock()
    config.processing.long_description_min_length = 100
    config.processing.short_description_max_length = 100
    return config


@pytest.fixture
def mock_config_claude_only():
    """Create a mock config with only Claude API key."""
    config = MagicMock(spec=Config)
    config.api = MagicMock()
    config.api.anthropic_api_key = "test-claude-key"
    config.api.openai_api_key = None
    config.processing = MagicMock()
    config.processing.long_description_min_length = 100
    config.processing.short_description_max_length = 100
    return config


@pytest.fixture
def mock_config_no_keys():
    """Create a mock config with no API keys."""
    config = MagicMock(spec=Config)
    config.api = MagicMock()
    config.api.anthropic_api_key = None
    config.api.openai_api_key = None
    return config


def test_init_with_both_providers(mock_config):
    """Test initialization with both providers configured."""
    with (
        patch("app.services.llm.service.Claude") as mock_claude,
        patch("app.services.llm.service.OpenAI") as mock_openai,
    ):
        service = LLMService(mock_config)

        # Both services should be initialized
        mock_claude.assert_called_once_with(mock_config)
        mock_openai.assert_called_once_with(mock_config)
        assert service.primary_provider is not None
        assert service.fallback_provider is not None


def test_init_with_claude_only(mock_config_claude_only):
    """Test initialization with only Claude configured."""
    with (
        patch("app.services.llm.service.Claude") as mock_claude,
        patch("app.services.llm.service.OpenAI") as mock_openai,
    ):
        service = LLMService(mock_config_claude_only)

        # Only Claude should be initialized
        mock_claude.assert_called_once_with(mock_config_claude_only)
        mock_openai.assert_not_called()
        assert service.primary_provider is not None
        assert service.fallback_provider is None


def test_init_no_providers_raises_error(mock_config_no_keys):
    """Test initialization with no providers raises error."""
    with (
        patch("app.services.llm.service.Claude"),
        patch("app.services.llm.service.OpenAI"),
    ):
        with pytest.raises(ConfigurationError) as exc_info:
            LLMService(mock_config_no_keys)

        assert "No LLM providers configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_descriptions_success(mock_config):
    """Test successful description generation."""
    with (
        patch("app.services.llm.service.Claude") as mock_claude_class,
        patch("app.services.llm.service.OpenAI"),
    ):
        # Setup mock
        mock_claude = AsyncMock()
        mock_claude_class.return_value = mock_claude
        # generate_descriptions returns the modified EventData object
        event_data = EventData(
            title="Test Event",
            venue="Test Venue",
            date="2025-01-01",
            long_description="Original long",
            short_description="Original short",
        )
        modified_event = event_data.model_copy(
            update={
                "long_description": "Long description",
                "short_description": "Short desc",
            }
        )
        mock_claude.generate_descriptions.return_value = modified_event

        service = LLMService(mock_config)

        result = await service.generate_descriptions(event_data, force_rebuild=True)

        assert result.title == "Test Event"
        assert result.long_description == "Long description"
        assert result.short_description == "Short desc"
        mock_claude.generate_descriptions.assert_called_once()


@pytest.mark.asyncio
async def test_generate_descriptions_with_fallback(mock_config):
    """Test description generation falls back to OpenAI on Claude failure."""
    with (
        patch("app.services.llm.service.Claude") as mock_claude_class,
        patch("app.services.llm.service.OpenAI") as mock_openai_class,
    ):
        # Setup mocks
        mock_claude = AsyncMock()
        mock_openai = AsyncMock()
        mock_claude_class.return_value = mock_claude
        mock_openai_class.return_value = mock_openai

        # Claude fails, OpenAI succeeds
        mock_claude.generate_descriptions.side_effect = Exception("Claude error")
        event_data = EventData(
            title="Test Event",
            venue="Test Venue",
            date="2025-01-01",
            long_description="original",
            short_description="original",
        )
        modified_event = event_data.model_copy(
            update={
                "long_description": "Fallback description",
                "short_description": "Fallback",
            }
        )
        mock_openai.generate_descriptions.return_value = modified_event

        service = LLMService(mock_config)

        result = await service.generate_descriptions(event_data, force_rebuild=True)

        assert result.title == "Test Event"
        assert result.long_description == "Fallback description"
        assert result.short_description == "Fallback"
        mock_claude.generate_descriptions.assert_called_once()
        mock_openai.generate_descriptions.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_text_success(mock_config):
    """Test successful text analysis."""
    with (
        patch("app.services.llm.service.Claude") as mock_claude_class,
        patch("app.services.llm.service.OpenAI"),
    ):
        # Setup mock
        mock_claude = AsyncMock()
        mock_claude_class.return_value = mock_claude
        mock_claude.analyze_text.return_value = "Analysis result"

        service = LLMService(mock_config)

        result = await service.analyze_text("Analyze this text")

        assert result == "Analysis result"
        mock_claude.analyze_text.assert_called_once_with(prompt="Analyze this text")


@pytest.mark.asyncio
async def test_extract_event_data_success(mock_config):
    """Test successful event data extraction."""
    with (
        patch("app.services.llm.service.Claude") as mock_claude_class,
        patch("app.services.llm.service.OpenAI"),
    ):
        # Setup mock
        mock_claude = AsyncMock()
        mock_claude_class.return_value = mock_claude
        mock_event_data = {"title": "Extracted Event", "venue": "Venue"}
        mock_claude.extract_event_data.return_value = mock_event_data

        service = LLMService(mock_config)

        result = await service.extract_event_data(
            prompt="Event text", image_b64="some-image-data", mime_type="image/png"
        )

        assert result == mock_event_data
        mock_claude.extract_event_data.assert_called_once_with(
            prompt="Event text", image_b64="some-image-data", mime_type="image/png"
        )
