"""Retry configuration settings."""

from pydantic_settings import BaseSettings


class RetryConfig(BaseSettings):
    """Retry configuration settings."""

    max_attempts: int = 3
    delay: float = 1.0
    backoff: float = 2.0


def get_retry_config() -> RetryConfig:
    """Get retry configuration instance."""
    return RetryConfig()
