"""HTTP configuration settings."""

from pydantic_settings import BaseSettings


class HTTPConfig(BaseSettings):
    """HTTP client configurations."""

    # Timeout settings
    timeout: int = 30
    short_timeout: int = 10  # For quick operations like genre lookups
    long_timeout: int = 60  # For data extraction operations

    # Connection settings
    max_connections: int = 100
    max_keepalive_connections: int = 30
    user_agent: str = "EventImporter/1.0"
