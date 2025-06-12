import logging
from typing import Any, Dict, Optional, TypeVar, Generic, Callable, Awaitable
from functools import wraps
from app.services.claude import ClaudeService
from app.services.openai import OpenAIService
from app.config import Config
from app.errors import retry_on_error, handle_errors_async
from app.schemas import EventData

logger = logging.getLogger(__name__)

T = TypeVar('T')

class LLMOperation(Generic[T]):
    """Represents an LLM operation with its providers and fallback logic."""
    
    def __init__(
        self,
        name: str,
        primary_provider: Callable[..., Awaitable[T]],
        fallback_provider: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any
    ):
        self.name = name
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self.args = args
        self.kwargs = kwargs

class LLMService:
    """Service for handling LLM operations with automatic fallback."""
    
    def __init__(self, config: Config):
        """Initialize LLM service with configured providers."""
        self.config = config
        self.primary_service = ClaudeService(config)
        self.fallback_service = (
            OpenAIService(config) if config.api.openai_key else None
        )

    async def _execute_with_fallback(self, operation: LLMOperation[T]) -> T:
        """Execute an LLM operation with automatic fallback."""
        try:
            logger.info(f"Attempting {operation.name} with primary provider (Claude)")
            return await operation.primary_provider(*operation.args, **operation.kwargs)
        except Exception as e:
            logger.warning(
                f"Primary provider (Claude) failed for {operation.name}, falling back to OpenAI: {e}"
            )
            if self.fallback_service:
                try:
                    logger.info(f"Attempting {operation.name} with fallback provider (OpenAI)")
                    return await operation.fallback_provider(
                        *operation.args, **operation.kwargs
                    )
                except Exception as fallback_error:
                    logger.error(
                        f"Fallback provider (OpenAI) also failed for {operation.name}: {fallback_error}"
                    )
                    raise fallback_error from e
            else:
                logger.error(
                    "Fallback provider (OpenAI) not available or configured, cannot retry."
                )
                raise e

    @retry_on_error(max_attempts=2)
    async def generate_descriptions(self, event_data: EventData) -> EventData:
        """Generate event descriptions with fallback."""
        operation = LLMOperation(
            name="generate_descriptions",
            primary_provider=self.primary_service.generate_descriptions,
            fallback_provider=self.fallback_service.generate_descriptions,
            event_data=event_data,
        )
        return await self._execute_with_fallback(operation)

    @retry_on_error(max_attempts=2)
    async def analyze_text(self, prompt: str) -> Optional[str]:
        """Analyze text with fallback."""
        operation = LLMOperation(
            name="analyze_text",
            primary_provider=self.primary_service.analyze_text,
            fallback_provider=self.fallback_service.analyze_text,
            prompt=prompt,
        )
        return await self._execute_with_fallback(operation)

    @retry_on_error(max_attempts=2)
    async def extract_event_data(
        self,
        prompt: str,
        image_b64: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Extract structured event data from a text prompt or image, with fallback."""
        operation = LLMOperation(
            "extract_event_data",
            self.primary_service.extract_event_data,
            self.fallback_service.extract_event_data,
            prompt=prompt,
            image_b64=image_b64,
            mime_type=mime_type,
        )
        return await self._execute_with_fallback(operation)

    @retry_on_error(max_attempts=2)
    async def enhance_genres(self, event_data: EventData) -> EventData:
        """Enhance genres with fallback."""
        operation = LLMOperation(
            name="enhance_genres",
            primary_provider=self.primary_service.enhance_genres,
            fallback_provider=self.fallback_service.enhance_genres,
            event_data=event_data,
        )
        return await self._execute_with_fallback(operation)

    @retry_on_error(max_attempts=2)
    async def extract_from_html(self, html: str, url: str) -> Optional[EventData]:
        """Extract event data from HTML with fallback."""
        operation = LLMOperation(
            "extract_from_html",
            self.primary_service.extract_from_html,
            self.fallback_service.extract_from_html,
            html,
            url,
        )
        return await self._execute_with_fallback(operation)

    @retry_on_error(max_attempts=2)
    async def extract_from_image(
        self, image_data: bytes, mime_type: str, url: str
    ) -> Optional[EventData]:
        """Extract event data from an image with fallback."""
        operation = LLMOperation(
            "extract_from_image",
            self.primary_service.extract_from_image,
            self.fallback_service.extract_from_image,
            image_data,
            mime_type,
            url,
        )
        return await self._execute_with_fallback(operation)