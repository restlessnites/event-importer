"""LLM service."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.config import Config
from app.errors import ConfigurationError, retry_on_error
from app.schemas import EventData
from app.services.claude import ClaudeService
from app.services.openai import OpenAIService

logger = logging.getLogger(__name__)

# Error message constants
LLM_NO_PROVIDERS_CONFIGURED = "No LLM providers configured. Please set either ANTHROPIC_API_KEY or OPENAI_API_KEY in your environment."

T = TypeVar("T")


class LLMOperation[T]:
    """Represents an LLM operation with its providers and fallback logic."""

    def __init__(
        self: LLMOperation,
        name: str,
        primary_provider: Callable[..., Awaitable[T]],
        fallback_provider: Callable[..., Awaitable[T]] | None,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        self.name = name
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self.args = args
        self.kwargs = kwargs


class LLMService:
    """Service for handling LLM operations with automatic fallback."""

    def __init__(self: LLMService, config: Config) -> None:
        """Initialize LLM service with configured providers."""
        self.config = config
        self.primary_service = ClaudeService(config)
        self.fallback_service = OpenAIService(config) if config.api.openai_api_key else None

        # Validate that at least one service is properly configured
        self._validate_configuration()

    def _validate_configuration(self: LLMService) -> None:
        """Validate that at least one LLM provider is properly configured."""
        claude_configured = bool(self.config.api.anthropic_api_key)
        openai_configured = bool(self.config.api.openai_api_key)

        if not claude_configured and not openai_configured:
            raise ConfigurationError(LLM_NO_PROVIDERS_CONFIGURED)

        if claude_configured:
            logger.info("Claude API configured as primary LLM provider")
        else:
            logger.warning("Claude API not configured - missing ANTHROPIC_API_KEY")

        if openai_configured:
            logger.info("OpenAI API configured as fallback LLM provider")
        else:
            logger.warning("OpenAI API not configured - missing OPENAI_API_KEY")

    async def _execute_with_fallback(self: LLMService, operation: LLMOperation[T]) -> T:
        """Execute an LLM operation with automatic fallback."""
        try:
            logger.info(f"Attempting {operation.name} with primary provider (Claude)")
            return await operation.primary_provider(*operation.args, **operation.kwargs)
        except Exception as e:
            logger.warning(
                f"Primary provider (Claude) failed for {operation.name}, falling back to OpenAI: {e}",
            )
            if self.fallback_service and operation.fallback_provider:
                try:
                    logger.info(
                        f"Attempting {operation.name} with fallback provider (OpenAI)",
                    )
                    return await operation.fallback_provider(
                        *operation.args,
                        **operation.kwargs,
                    )
                except Exception as fallback_error:
                    logger.exception(
                        f"Fallback provider (OpenAI) also failed for {operation.name}",
                    )
                    raise fallback_error from e
            else:
                logger.exception(
                    "Fallback provider (OpenAI) not available or configured, cannot retry.",
                )
                raise e

    def _enhance_description(self: LLMService, event_data: EventData) -> EventData:
        """Appends lineup to long description if available."""
        if not event_data.lineup:
            return event_data

        lineup_header = "Lineup"
        lineup_text = ", ".join(event_data.lineup)

        if event_data.long_description:
            # Check if lineup is already present to avoid duplication
            if lineup_header.lower() not in event_data.long_description.lower():
                event_data.long_description = f"{event_data.long_description.strip()}\n\n{lineup_header}:\n{lineup_text}"
        else:
            event_data.long_description = f"{lineup_header}:\n{lineup_text}"

        return event_data

    @retry_on_error(max_attempts=2)
    async def generate_descriptions(
        self: LLMService,
        event_data: EventData,
        force_rebuild: bool = False,
    ) -> EventData:
        """Generate long/short descriptions for an event if they are missing."""
        # Descriptions are generated only if there's no long description,
        # or if it's shorter than 200 characters.
        needs_long = (
            not event_data.long_description or len(event_data.long_description) < 200
        )
        needs_short = not (
            event_data.short_description and len(event_data.short_description) <= 100
        )

        if force_rebuild or needs_long or needs_short:
            operation = LLMOperation(
                "generate_descriptions",
                self.primary_service.generate_descriptions,
                self.fallback_service.generate_descriptions
                if self.fallback_service
                else None,
                event_data,
                force_rebuild=force_rebuild,
            )
            event_data = await self._execute_with_fallback(operation)

        # Always enhance with lineup after potential generation
        return self._enhance_description(event_data)

    @retry_on_error(max_attempts=2)
    async def analyze_text(self: LLMService, prompt: str) -> str | None:
        """Analyze text with fallback."""
        operation = LLMOperation(
            name="analyze_text",
            primary_provider=self.primary_service.analyze_text,
            fallback_provider=self.fallback_service.analyze_text
            if self.fallback_service
            else None,
            prompt=prompt,
        )
        return await self._execute_with_fallback(operation)

    @retry_on_error(max_attempts=2)
    async def extract_event_data(
        self: LLMService,
        prompt: str,
        image_b64: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Extract structured event data from a text prompt or image, with fallback."""
        operation = LLMOperation(
            "extract_event_data",
            self.primary_service.extract_event_data,
            self.fallback_service.extract_event_data if self.fallback_service else None,
            prompt=prompt,
            image_b64=image_b64,
            mime_type=mime_type,
        )
        return await self._execute_with_fallback(operation)

    @retry_on_error(max_attempts=2)
    async def enhance_genres(self: LLMService, event_data: EventData) -> EventData:
        """Enhance genres with fallback."""
        operation = LLMOperation(
            name="enhance_genres",
            primary_provider=self.primary_service.enhance_genres,
            fallback_provider=self.fallback_service.enhance_genres
            if self.fallback_service
            else None,
            event_data=event_data,
        )
        return await self._execute_with_fallback(operation)

    @retry_on_error(max_attempts=2)
    async def extract_from_html(
        self: LLMService,
        html: str,
        url: str,
    ) -> EventData | None:
        """Extract event data from HTML with fallback."""
        operation = LLMOperation(
            "extract_from_html",
            self.primary_service.extract_from_html,
            self.fallback_service.extract_from_html if self.fallback_service else None,
            html,
            url,
        )
        return await self._execute_with_fallback(operation)

    @retry_on_error(max_attempts=2)
    async def extract_from_image(
        self: LLMService,
        image_data: bytes,
        mime_type: str,
        url: str,
    ) -> EventData | None:
        """Extract event data from an image with fallback."""
        operation = LLMOperation(
            "extract_from_image",
            self.primary_service.extract_from_image,
            self.fallback_service.extract_from_image if self.fallback_service else None,
            image_data,
            mime_type,
            url,
        )
        event_data = await self._execute_with_fallback(operation)

        if event_data:
            return self._enhance_description(event_data)
        return None
