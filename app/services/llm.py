import logging
from typing import Any, Dict, Optional, TypeVar, Generic, Callable, Awaitable
from functools import wraps
from app.services.claude import ClaudeService
from app.services.openai import OpenAIService
from app.config import Config
from app.errors import retry_on_error

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
        self.claude = ClaudeService(config)
        self.openai = OpenAIService(config)
        self.config = config

    async def _execute_with_fallback(self, operation: LLMOperation[T]) -> T:
        """Execute an LLM operation with automatic fallback."""
        try:
            logger.info(f"Attempting {operation.name} with primary provider")
            return await operation.primary_provider(*operation.args, **operation.kwargs)
        except Exception as e:
            logger.warning(f"Primary provider failed for {operation.name}, falling back: {e}")
            try:
                logger.info(f"Attempting {operation.name} with fallback provider")
                return await operation.fallback_provider(*operation.args, **operation.kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback provider also failed for {operation.name}: {fallback_error}")
                # If both providers fail, return None or empty result instead of raising
                if operation.name == "generate_descriptions":
                    return operation.kwargs.get("event_data")
                elif operation.name == "enhance_genres":
                    return operation.kwargs.get("event_data")
                elif operation.name in ["extract_event_data", "extract_event_data_with_vision"]:
                    return None
                elif operation.name == "analyze_text":
                    return None
                raise

    @retry_on_error(max_attempts=2)
    async def generate_descriptions(self, event_data: Any) -> Any:
        """Generate event descriptions with fallback."""
        operation = LLMOperation(
            name="generate_descriptions",
            primary_provider=self.claude.generate_descriptions,
            fallback_provider=self.openai.generate_descriptions,
            event_data=event_data
        )
        return await self._execute_with_fallback(operation)

    @retry_on_error(max_attempts=2)
    async def analyze_text(self, prompt: str) -> Optional[str]:
        """Analyze text with fallback."""
        operation = LLMOperation(
            name="analyze_text",
            primary_provider=self.claude.analyze_text,
            fallback_provider=self.openai.analyze_text,
            prompt=prompt
        )
        return await self._execute_with_fallback(operation)

    @retry_on_error(max_attempts=2)
    async def extract_event_data(self, prompt: str, image_b64: Optional[str] = None, mime_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Extract event data with fallback."""
        if image_b64 and mime_type:
            operation = LLMOperation(
                name="extract_event_data_with_vision",
                primary_provider=self.claude.extract_from_image,
                fallback_provider=self.openai.extract_from_image,
                image_data=image_b64,
                mime_type=mime_type,
                url=""  # URL is not available in this context
            )
        else:
            operation = LLMOperation(
                name="extract_event_data",
                primary_provider=self.claude.extract_from_html,
                fallback_provider=self.openai.extract_from_html,
                html=prompt,
                url=""  # URL is not available in this context
            )
        return await self._execute_with_fallback(operation)

    @retry_on_error(max_attempts=2)
    async def enhance_genres(self, event_data: Any) -> Any:
        """Enhance genres with fallback."""
        operation = LLMOperation(
            name="enhance_genres",
            primary_provider=self.claude.enhance_genres,
            fallback_provider=self.openai.enhance_genres,
            event_data=event_data
        )
        return await self._execute_with_fallback(operation)