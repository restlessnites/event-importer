"""Exception classes and error handling utilities for the Event Importer."""

import functools
import logging
from typing import Callable, Optional, TypeVar
from dataclasses import dataclass
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)


logger = logging.getLogger(__name__)


class EventImporterError(Exception):
    """Base exception for all Event Importer errors."""

    pass


class ConfigurationError(EventImporterError):
    """Raised when configuration is invalid or missing."""

    pass


class ExtractionError(EventImporterError):
    """Base exception for extraction-related errors."""

    pass


class APIError(ExtractionError):
    """Raised when an external API call fails."""

    def __init__(self, service: str, message: str, status_code: Optional[int] = None):
        self.service = service
        self.status_code = status_code
        super().__init__(f"{service} API error: {message}")


class ValidationError(ExtractionError):
    """Raised when data validation fails."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Validation error for '{field}': {message}")


class TimeoutError(ExtractionError):
    """Raised when an operation times out."""

    pass


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, service: str, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        message = "Rate limit exceeded"
        if retry_after:
            message += f" (retry after {retry_after}s)"
        super().__init__(service, message)


class AuthenticationError(APIError):
    """Raised when API authentication fails."""

    def __init__(self, service: str):
        super().__init__(service, "Authentication failed", 401)


class NotFoundError(ExtractionError):
    """Raised when a requested resource is not found."""

    pass


class UnsupportedURLError(ExtractionError):
    """Raised when a URL cannot be handled by any agent."""

    def __init__(self, url: str):
        self.url = url
        super().__init__(f"No agent can handle URL: {url}")


class SecurityPageError(ExtractionError):
    """Raised when a security or protection page is detected."""
    
    def __init__(self, message: str, url: Optional[str] = None):
        self.url = url
        super().__init__(f"Security page detected: {message}")

@dataclass
class ErrorContext:
    """Context information for error handling."""

    url: Optional[str] = None
    agent: Optional[str] = None
    operation: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


T = TypeVar("T")


def handle_errors(
    *,
    default: Optional[T] = None,
    reraise: bool = True,
    log_level: int = logging.ERROR,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for consistent error handling.

    Args:
        default: Default value to return on error
        reraise: Whether to re-raise the exception after logging
        log_level: Logging level for errors
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except EventImporterError as e:
                logger.log(log_level, f"{func.__name__} failed: {e}")
                if reraise:
                    raise
                return default
            except Exception as e:
                logger.exception(f"Unexpected error in {func.__name__}: {e}")
                if reraise:
                    raise
                return default

        return wrapper

    return decorator


def handle_errors_async(
    *,
    default: Optional[T] = None,
    reraise: bool = True,
    log_level: int = logging.ERROR,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Async version of handle_errors decorator.

    Args:
        default: Default value to return on error
        reraise: Whether to re-raise the exception after logging
        log_level: Logging level for errors
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except EventImporterError as e:
                logger.log(log_level, f"{func.__name__} failed: {e}")
                if reraise:
                    raise
                return default
            except Exception as e:
                logger.exception(f"Unexpected error in {func.__name__}: {e}")
                if reraise:
                    raise
                return default

        return wrapper

    return decorator


def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (APIError, TimeoutError),
) -> Callable:
    """
    Decorator to retry a function on specific errors using tenacity.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for exponential backoff
        exceptions: Tuple of exceptions to retry on
    """
    def should_retry(retry_state):
        """Custom retry condition that excludes non-retryable errors."""
        if retry_state.outcome and retry_state.outcome.failed:
            exception = retry_state.outcome.exception()
            # Never retry these error types
            if isinstance(exception, (AuthenticationError, SecurityPageError, ValidationError)):
                return False
            # Only retry specified exceptions
            return isinstance(exception, exceptions)
        return False
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=delay, exp_base=backoff),
        retry=should_retry,
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def format_error_response(
    error: Exception,
    context: Optional[ErrorContext] = None,
) -> dict:
    """
    Format an error for API response.

    Args:
        error: The exception
        context: Optional error context

    Returns:
        Dictionary with error details
    """
    response = {
        "error": type(error).__name__,
        "message": str(error),
    }

    if isinstance(error, APIError):
        response["service"] = error.service
        if error.status_code:
            response["status_code"] = error.status_code

    if isinstance(error, ValidationError):
        response["field"] = error.field

    if isinstance(error, RateLimitError) and error.retry_after:
        response["retry_after"] = error.retry_after

    if context:
        response["context"] = context.to_dict()

    return response
