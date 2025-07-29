"""Exception classes and error handling utilities for the Event Importer."""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from tenacity import (
    RetryCallState,
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class EventImporterError(Exception):
    """Base exception for all Event Importer errors."""


class ConfigurationError(EventImporterError):
    """Raised when configuration is invalid or missing."""


class ExtractionError(EventImporterError):
    """Base exception for extraction-related errors."""


class ImporterError(Exception):
    """Base exception for all importer errors."""

    def __init__(self: ImporterError, message: str, service: str | None = None) -> None:
        self.message = message
        self.service = service
        super().__init__(f"{service}: {message}" if service else message)


class APIError(ImporterError):
    """Raised when an external API call fails."""

    def __init__(
        self: APIError,
        service: str,
        message: str,
        status_code: int | None = None,
    ) -> None:
        """Initialize APIError."""
        self.status_code = status_code
        super().__init__(message, service)


class AuthenticationError(APIError):
    """Raised for authentication failures (401)."""

    def __init__(self: AuthenticationError, service: str) -> None:
        """Initialize AuthenticationError."""
        super().__init__(service, "Authentication failed", 401)


class RateLimitError(APIError):
    """Raised for rate limit exceeded errors (429)."""

    def __init__(self: RateLimitError, service: str, retry_after: int | None) -> None:
        """Initialize RateLimitError."""
        self.retry_after = retry_after
        message = (
            f"Rate limit exceeded. Retry after: {retry_after}s"
            if retry_after
            else "Rate limit exceeded"
        )
        super().__init__(service, message, 429)


class RequestTimeoutError(APIError):
    """Raised for request timeouts."""

    def __init__(self: RequestTimeoutError, message: str) -> None:
        """Initialize RequestTimeoutError."""
        super().__init__("HTTP", message, 408)


class UnsupportedURLError(ImporterError):
    """Raised when a URL is not supported by any agent."""

    def __init__(self: UnsupportedURLError, url: str) -> None:
        """Initialize UnsupportedURLError."""
        self.url = url
        super().__init__(f"URL not supported: {url}")


class SecurityPageError(ImporterError):
    """Raised when a security/protection page is detected."""

    def __init__(self: SecurityPageError, reason: str, url: str) -> None:
        """Initialize SecurityPageError."""
        self.reason = reason
        self.url = url
        super().__init__(f"Security page detected: {reason}")


class DataExtractionError(ImporterError):
    """Raised when event data cannot be extracted from a page."""

    def __init__(self: DataExtractionError, message: str) -> None:
        """Initialize DataExtractionError."""
        super().__init__(message)


class ValidationError(ExtractionError):
    """Raised when data validation fails."""

    def __init__(self: ValidationError, field: str, message: str) -> None:
        self.field = field
        super().__init__(f"Validation error for '{field}': {message}")


@dataclass
class ErrorContext:
    """Context information for error handling."""

    url: str | None = None
    agent: str | None = None
    operation: str | None = None
    retry_count: int = 0

    def to_dict(self: ErrorContext) -> dict:
        """Convert to dictionary for logging."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


T = TypeVar("T")


def handle_errors[T](
    *,
    default: T | None = None,
    reraise: bool = True,
    log_level: int = logging.ERROR,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for consistent error handling.

    Args:
        default: Default value to return on error
        reraise: Whether to re-raise the exception after logging
        log_level: Logging level for errors

    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> T:
            try:
                return func(*args, **kwargs)
            except EventImporterError as e:
                logger.log(log_level, f"{func.__name__} failed: {e}")
                if reraise:
                    raise
                return default
            except Exception:
                logger.exception(f"Unexpected error in {func.__name__}")
                if reraise:
                    raise
                return default

        return wrapper

    return decorator


def handle_errors_async[T](
    *,
    default: T | None = None,
    reraise: bool = True,
    log_level: int = logging.ERROR,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Async version of handle_errors decorator.

    Args:
        default: Default value to return on error
        reraise: Whether to re-raise the exception after logging
        log_level: Logging level for errors

    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> T:
            try:
                return await func(*args, **kwargs)
            except EventImporterError as e:
                logger.log(log_level, f"{func.__name__} failed: {e}")
                if reraise:
                    raise
                return default
            except Exception:
                logger.exception(f"Unexpected error in {func.__name__}")
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
    """Decorator to retry a function on specific errors using tenacity.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for exponential backoff
        exceptions: Tuple of exceptions to retry on

    """

    def should_retry(retry_state: RetryCallState) -> bool:
        """Custom retry condition that excludes non-retryable errors."""
        if retry_state.outcome and retry_state.outcome.failed:
            exception = retry_state.outcome.exception()
            # Never retry these error types
            if isinstance(
                exception,
                AuthenticationError | SecurityPageError | ValidationError,
            ):
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
