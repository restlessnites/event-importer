"""Configuration module - orchestrates all configuration components."""

import logging

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.api import APIConfig
from config.http import HTTPConfig
from config.loader import load_config
from config.paths import get_project_root
from config.processing import ProcessingConfig
from config.runtime import RuntimeConfig

logger = logging.getLogger(__name__)


class Config(BaseSettings):
    """Main configuration container that orchestrates all config components."""

    # API configurations
    api: APIConfig = Field(default_factory=APIConfig)

    # HTTP configurations
    http: HTTPConfig = Field(default_factory=HTTPConfig)

    # Processing configurations
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)

    # Runtime configurations
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)

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


# Create the global configuration instance
config = Config()
