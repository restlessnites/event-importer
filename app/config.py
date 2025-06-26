"""Centralized configuration management for the Event Importer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class APIConfig:
    """Configuration for external API services."""

    anthropic_key: str | None = None
    openai_key: str | None = None
    zyte_key: str | None = None
    ticketmaster_key: str | None = None
    google_api_key: str | None = None
    google_cse_id: str | None = None
    ticketfairy_api_key: str | None = None

    def validate(self: APIConfig) -> dict[str, bool]:
        """Validate which APIs are configured."""
        return {
            "anthropic": bool(self.anthropic_key),
            "openai": bool(self.openai_key),
            "zyte": bool(self.zyte_key),
            "ticketmaster": bool(self.ticketmaster_key),
            "google_search": bool(self.google_api_key and self.google_cse_id),
            "ticketfairy": bool(self.ticketfairy_api_key),
        }


@dataclass
class HTTPConfig:
    """Configuration for HTTP client behavior."""

    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    )
    max_connections: int = 10
    max_keepalive_connections: int = 5


@dataclass
class ExtractionConfig:
    """Configuration for extraction behavior."""

    max_html_size: int = 10 * 1024 * 1024  # 10MB
    max_image_size: int = 20 * 1024 * 1024  # 20MB
    min_image_width: int = 500
    min_image_height: int = 500
    default_timeout: int = 60
    max_description_length: int = 5000
    short_description_length: int = 150


@dataclass
class ZyteConfig:
    """Configuration specific to Zyte API."""

    api_url: str = "https://api.zyte.com/v1/extract"
    use_residential_proxy: bool = False
    geolocation: str | None = None
    javascript_wait: int = 5  # seconds to wait for JS
    screenshot_full_page: bool = True


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

    # Runtime settings
    debug: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_env(cls: type[Config], env_file: Path | None = None) -> Config:
        """Create configuration from environment variables."""
        if env_file:
            load_dotenv(env_file)
        else:
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

        # Load optional overrides
        if timeout := os.getenv("HTTP_TIMEOUT"):
            config.http.timeout = int(timeout)

        if max_retries := os.getenv("HTTP_MAX_RETRIES"):
            config.http.max_retries = int(max_retries)

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
            config.log_level = log_level.upper()

        return config

    def validate(self: Config) -> None:
        """Validate configuration and raise if critical keys are missing."""
        api_status = self.api.validate()

        if not api_status["anthropic"] and not api_status.get("openai"):
            error_msg = "At least one of ANTHROPIC_API_KEY or OPENAI_API_KEY is required."
            raise ValueError(error_msg)

        if not api_status["zyte"]:
            error_msg = "ZYTE_API_KEY is required"
            raise ValueError(error_msg)

        # Log warnings for optional APIs
        if not api_status["ticketmaster"]:
            import logging

            logging.warning(
                "Ticketmaster API key not configured - Ticketmaster imports disabled",
            )

        if not api_status["google_search"]:
            import logging

            logging.warning("Google Search API not configured - image search disabled")

        if not api_status["ticketfairy"]:
            import logging

            logging.warning(
                "TicketFairy API key not configured - TicketFairy integration disabled",
            )

    def get_enabled_features(self: Config) -> dict[str, bool]:
        """Get which features are enabled based on configuration."""
        api_status = self.api.validate()
        features = {
            "resident_advisor": True,  # Always enabled (no auth needed)
            "ticketmaster": api_status["ticketmaster"],
            "image_search": api_status["google_search"],
            "web_scraping": api_status["zyte"],
            "ticketfairy_integration": api_status["ticketfairy"],
        }
        if api_status.get("openai"):
            features["openai_fallback"] = True
        return features


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
        _config.validate()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance (mainly for testing)."""
    global _config
    _config = config
