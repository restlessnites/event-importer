"""Centralized configuration management for the Event Importer."""

from __future__ import annotations

import json
import logging
import sys
from functools import cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.shared.path import get_project_root, get_user_data_dir
from config.storage import SettingsStorage

logger = logging.getLogger(__name__)


class HTTPConfig(BaseSettings):
    """HTTP client configurations."""

    timeout: int = 30
    max_connections: int = 100
    max_keepalive_connections: int = 30
    user_agent: str = "EventImporter/1.0"


def load_config() -> dict[str, Any]:
    """Load configuration from SQLite storage (for packaged app) or fallback to JSON."""
    # Only use storage when running as packaged app
    if getattr(sys, "frozen", False):
        try:
            # Try SQLite storage first
            storage = SettingsStorage(get_user_data_dir() / "events.db")
            settings = storage.get_all()
            if settings:
                return settings
        except Exception as e:
            logger.debug("Failed to load config from SQLite storage: %s", e)

        # Fallback to old config.json if SQLite fails
        config_path = get_user_data_dir() / "config.json"
        if config_path.exists():
            try:
                with config_path.open() as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                pass
    return {}


class APIConfig(BaseSettings):
    """API key configurations."""

    anthropic_api_key: str | None = Field(None, alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")
    zyte_api_key: str | None = Field(None, alias="ZYTE_API_KEY")
    ticketmaster_api_key: str | None = Field(None, alias="TICKETMASTER_API_KEY")
    google_api_key: str | None = Field(None, alias="GOOGLE_API_KEY")
    google_cse_id: str | None = Field(None, alias="GOOGLE_CSE_ID")
    ticketfairy_api_key: str | None = Field(None, alias="TICKETFAIRY_API_KEY")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # For packaged app: config.json -> env vars
        # For development: .env -> env vars
        del settings_cls  # Required by pydantic but unused
        return (
            init_settings,
            lambda: load_config(),  # Only loads in packaged app
            env_settings,
            dotenv_settings,  # Only loads in development
            file_secret_settings,
        )

    model_config = SettingsConfigDict(
        env_file=get_project_root() / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


class Config(BaseSettings):
    """Main configuration container."""

    # API configurations
    api: APIConfig = Field(default_factory=APIConfig)

    # HTTP configurations
    http: HTTPConfig = Field(default_factory=HTTPConfig)

    # Runtime settings
    debug: bool = Field(False, alias="DEBUG")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # For packaged app: config.json -> env vars
        # For development: .env -> env vars
        del settings_cls  # Required by pydantic but unused
        return (
            init_settings,
            lambda: load_config(),  # Only loads in packaged app
            env_settings,
            dotenv_settings,  # Only loads in development
            file_secret_settings,
        )

    model_config = SettingsConfigDict(
        env_file=get_project_root() / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

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
