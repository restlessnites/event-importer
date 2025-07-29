"""Centralized configuration management for the Event Importer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import cache

from dotenv import load_dotenv

from app.shared.path import get_project_root


@dataclass
class APIConfig:
    """API key configurations."""

    anthropic_key: str | None = None
    openai_key: str | None = None
    zyte_key: str | None = None
    ticketmaster_key: str | None = None
    google_api_key: str | None = None
    google_cse_id: str | None = None
    ticketfairy_api_key: str | None = None


@dataclass
class HTTPConfig:
    """HTTP client settings."""

    timeout: int = 30
    max_retries: int = 3
    max_connections: int = 100
    max_keepalive_connections: int = 20
    user_agent: str = "EventImporter/1.0"


@dataclass
class ExtractionConfig:
    """Settings for data extraction."""

    use_cache: bool = True
    max_image_size: int = 1024 * 1024 * 5  # 5 MB
    min_image_width: int = 500
    min_image_height: int = 500


@dataclass
class ZyteConfig:
    """Zyte-specific settings."""

    use_residential_proxy: bool = False
    geolocation: str | None = None


@dataclass
class UpdateConfig:
    """Update-related settings."""

    file_url: str | None = None


@dataclass
class Config:
    """Main configuration container."""

    # API configurations
    api: APIConfig = field(default_factory=APIConfig)

    # HTTP client settings
    http: HTTPConfig = field(default_factory=HTTPConfig)

    # Extraction settings
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)

    # Zyte-specific settings
    zyte: ZyteConfig = field(default_factory=ZyteConfig)

    # Update settings
    update: UpdateConfig = field(default_factory=UpdateConfig)

    # Runtime settings
    debug: bool = False
    log_level: str = "INFO"

    def get_enabled_features(self) -> list[str]:
        """Get list of enabled features based on configured API keys."""
        features = []

        # Always available (no API key required)
        features.extend(["dice", "ra"])

        # API key dependent features
        if self.api.ticketmaster_key:
            features.append("ticketmaster")

        if self.api.zyte_key:
            features.append("web")
            features.append("image")

        if self.api.google_api_key and self.api.google_cse_id:
            features.append("genre_enhancement")
            features.append("image_enhancement")

        if self.api.ticketfairy_api_key:
            features.append("ticketfairy")

        if self.api.anthropic_key or self.api.openai_key:
            features.append("ai_extraction")

        return sorted(features)

    @classmethod
    def from_env(cls) -> Config:
        """Load configuration from environment variables."""
        load_dotenv()

        config = cls()

        # Load API keys
        config.api.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        config.api.openai_key = os.getenv("OPENAI_API_KEY")
        config.api.zyte_key = os.getenv("ZYTE_API_KEY")
        config.api.ticketmaster_key = os.getenv("TICKETMASTER_API_KEY")
        config.api.google_api_key = os.getenv("GOOGLE_API_KEY")
        config.api.google_cse_id = os.getenv("GOOGLE_CSE_ID")
        config.api.ticketfairy_api_key = os.getenv("TICKETFAIRY_API_KEY")

        # Load update settings
        config.update.file_url = os.getenv("UPDATE_FILE_URL")

        # Load optional overrides
        if timeout := os.getenv("HTTP_TIMEOUT"):
            config.http.timeout = int(timeout)

        if max_retries := os.getenv("HTTP_MAX_RETRIES"):
            config.http.max_retries = int(max_retries)

        if use_cache := os.getenv("USE_CACHE"):
            config.extraction.use_cache = use_cache.lower() in ("true", "1", "yes")

        if use_proxy := os.getenv("ZYTE_USE_RESIDENTIAL_PROXY"):
            config.zyte.use_residential_proxy = use_proxy.lower() in (
                "true",
                "1",
                "yes",
            )

        if geo := os.getenv("ZYTE_GEOLOCATION"):
            config.zyte.geolocation = geo

        if debug := os.getenv("DEBUG"):
            config.debug = debug.lower() in ("true", "1", "yes")

        if log_level := os.getenv("LOG_LEVEL"):
            config.log_level = log_level

        return config


# Global config instance
_config: Config | None = None


@cache
def get_config() -> Config:
    """Get the global configuration instance."""
    # Ensure .env is loaded
    env_path = get_project_root() / ".env"
    load_dotenv(dotenv_path=env_path)
    return Config.from_env()


def clear_config_cache() -> None:
    """Clear the cached configuration."""
    get_config.cache_clear()


if __name__ == "__main__":
    config = get_config()
    # Pretty print the config
    import json

    print(json.dumps(config.__dict__, indent=4))
