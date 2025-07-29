"""Centralized configuration management for the Event Importer."""

from __future__ import annotations

import json
from functools import cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.shared.path import get_project_root


class HTTPConfig(BaseSettings):
    """HTTP client configurations."""

    timeout: int = 30
    max_connections: int = 100
    max_keepalive_connections: int = 30
    user_agent: str = "EventImporter/1.0"


class APIConfig(BaseSettings):
    """API key configurations."""

    model_config = SettingsConfigDict(
        env_file=get_project_root() / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    zyte_api_key: str | None = None
    ticketmaster_api_key: str | None = None
    google_api_key: str | None = None
    google_cse_id: str | None = None
    ticketfairy_api_key: str | None = None


class Config(BaseSettings):
    """Main configuration container."""

    model_config = SettingsConfigDict(
        env_file=get_project_root() / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API configurations
    api: APIConfig = APIConfig()

    # HTTP configurations
    http: HTTPConfig = HTTPConfig()

    # Runtime settings
    debug: bool = False
    log_level: str = "INFO"

    def get_enabled_features(self) -> list[str]:
        """Get list of enabled features based on available API keys."""
        features = ["dice", "ra"]  # Always enabled

        if self.api.ticketmaster_api_key:
            features.append("ticketmaster")
        if self.api.zyte_api_key:
            features.append("web")
            features.append("image")
        if self.api.anthropic_api_key or self.api.openai_api_key:
            features.append("ai_extraction")

        return sorted(features)


@cache
def get_config() -> Config:
    """Get the global configuration instance."""
    return Config()


def clear_config_cache() -> None:
    """Clear the cached configuration."""
    get_config.cache_clear()


if __name__ == "__main__":
    config = get_config()
    # Pretty print the config
    print(json.dumps(config.model_dump(), indent=4))
