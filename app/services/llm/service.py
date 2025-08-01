"""LLM service."""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.core.errors import ConfigurationError, retry_on_error
from app.core.schemas import EventData
from app.services.llm.base import BaseLLMService
from app.services.llm.providers.claude import Claude
from app.services.llm.providers.openai import OpenAI
from config import Config

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
        self.primary_provider: BaseLLMService = Claude(config)
        self.fallback_provider: BaseLLMService | None = (
            OpenAI(config) if config.api.openai_api_key else None
        )

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
            if self.fallback_provider and operation.fallback_provider:
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
                event_data.long_description = f"{event_data.long_description.strip()}\\n\\n{lineup_header}:\\n{lineup_text}"
        else:
            event_data.long_description = f"{lineup_header}:\\n{lineup_text}"

        return event_data

    def needs_description_generation(
        self: LLMService, event_data: EventData, force_rebuild: bool = False
    ) -> tuple[bool, bool]:
        """Determine if long or short descriptions need to be generated."""
        needs_long = (
            force_rebuild
            or not event_data.long_description
            or (
                len(event_data.long_description)
                < self.config.processing.long_description_min_length
            )
        )
        needs_short = (
            force_rebuild
            or not event_data.short_description
            or (
                len(event_data.short_description)
                > self.config.processing.short_description_max_length
            )
        )
        return needs_long, needs_short

    @retry_on_error(max_attempts=2)
    async def generate_descriptions(
        self: LLMService,
        event_data: EventData,
        force_rebuild: bool = False,
        supplementary_context: str | None = None,
    ) -> EventData:
        """Generate long/short descriptions for an event if they are missing or do not meet length criteria."""
        needs_long, needs_short = self.needs_description_generation(
            event_data, force_rebuild
        )

        # If no descriptions need fixing, return the original event data
        if not needs_long and not needs_short:
            return self._enhance_description(event_data)

        # Call the LLM to generate the descriptions that are needed
        operation = LLMOperation(
            "generate_descriptions",
            self.primary_provider.generate_descriptions,
            self.fallback_provider.generate_descriptions
            if self.fallback_provider
            else None,
            event_data=event_data,
            needs_long=needs_long,
            needs_short=needs_short,
            supplementary_context=supplementary_context,
        )
        updated_event = await self._execute_with_fallback(operation)

        # Enhance the final result
        return self._enhance_description(updated_event)

    @retry_on_error(max_attempts=2)
    async def analyze_text(self: LLMService, prompt: str) -> str | None:
        """Analyze text with fallback."""
        operation = LLMOperation(
            name="analyze_text",
            primary_provider=self.primary_provider.analyze_text,
            fallback_provider=self.fallback_provider.analyze_text
            if self.fallback_provider
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
            self.primary_provider.extract_event_data,
            self.fallback_provider.extract_event_data
            if self.fallback_provider
            else None,
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
            primary_provider=self.primary_provider.enhance_genres,
            fallback_provider=self.fallback_provider.enhance_genres
            if self.fallback_provider
            else None,
            event_data=event_data,
        )
        return await self._execute_with_fallback(operation)

    @retry_on_error(max_attempts=2)
    async def extract_from_html(
        self: LLMService,
        html: str,
        url: str,
        needs_long_description: bool = True,
        needs_short_description: bool = True,
    ) -> EventData | None:
        """Extract event data from HTML with fallback."""
        operation = LLMOperation(
            "extract_from_html",
            self.primary_provider.extract_from_html,
            self.fallback_provider.extract_from_html
            if self.fallback_provider
            else None,
            html,
            url,
            needs_long_description=needs_long_description,
            needs_short_description=needs_short_description,
        )
        return await self._execute_with_fallback(operation)

    @retry_on_error(max_attempts=2)
    async def extract_from_image(
        self: LLMService,
        image_data: bytes,
        mime_type: str,
        url: str,
        needs_long_description: bool = True,
        needs_short_description: bool = True,
    ) -> EventData | None:
        """Extract event data from an image with fallback."""
        operation = LLMOperation(
            "extract_from_image",
            self.primary_provider.extract_from_image,
            self.fallback_provider.extract_from_image
            if self.fallback_provider
            else None,
            image_data,
            mime_type,
            url,
            needs_long_description=needs_long_description,
            needs_short_description=needs_short_description,
        )
        event_data = await self._execute_with_fallback(operation)

        if event_data:
            return self._enhance_description(event_data)
        return None

    @retry_on_error(max_attempts=2)
    async def extract_genres_with_context(
        self: LLMService,
        prompt: str,
    ) -> list[str]:
        """Extract genres using structured output with custom prompt."""
        # Use Claude's structured genre tool with custom prompt
        if self.primary_provider:
            try:
                # Use Claude's structured tool directly with custom prompt
                result = await self.primary_provider._call_with_tool(
                    prompt,
                    tool=self.primary_provider.GENRE_TOOL,
                    tool_name="enhance_genres",
                )
                if result and result.get("genres"):
                    return result["genres"]
                return []
            except Exception as e:
                logger.debug(f"Primary service genre extraction failed: {e}")
                if self.fallback_provider:
                    # Fallback to text analysis if structured fails
                    response = await self.fallback_provider.analyze_text(prompt)
                    if response:
                        # Simple extraction - look for genres in text
                        genres = re.findall(
                            r"\\b[A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*\\b", response
                        )
                        # Filter to likely genre words
                        genre_words = [
                            "House",
                            "Techno",
                            "Electronic",
                            "Rock",
                            "Pop",
                            "Jazz",
                            "Hip-Hop",
                            "Trap",
                            "Dubstep",
                            "Drum",
                            "Bass",
                        ]
                        found_genres = [
                            g for g in genres if any(word in g for word in genre_words)
                        ]
                        return found_genres[:4]
                raise e
        return []
