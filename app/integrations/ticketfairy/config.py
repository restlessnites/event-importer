"""TicketFairy configuration."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class TicketFairyConfig:
    """Configuration for TicketFairy integration."""

    # API Configuration
    api_key: str | None = None
    api_base_url: str = "https://www.theticketfairy.com/api"
    draft_events_endpoint: str = "/draft-events"
    origin: str = "https://restlessnites.com"

    # Request configuration
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds

    @classmethod
    def from_env(cls: type[TicketFairyConfig]) -> TicketFairyConfig:
        """Create configuration from environment variables."""
        config = cls()

        # Load from environment
        config.api_key = os.getenv("TICKETFAIRY_API_KEY")
        config.origin = os.getenv("TICKETFAIRY_ORIGIN", config.origin)

        # Optional overrides
        if timeout := os.getenv("TICKETFAIRY_TIMEOUT"):
            config.timeout = int(timeout)
        if max_retries := os.getenv("TICKETFAIRY_MAX_RETRIES"):
            config.max_retries = int(max_retries)
        if retry_delay := os.getenv("TICKETFAIRY_RETRY_DELAY"):
            config.retry_delay = float(retry_delay)

        return config

    def is_enabled(self: TicketFairyConfig) -> bool:
        """Check if TicketFairy integration is properly configured."""
        return bool(self.api_key)

    def validate(self: TicketFairyConfig) -> None:
        """Validate configuration and log warnings if needed."""
        if not self.is_enabled():
            logger.warning(
                "TicketFairy API key not configured - TicketFairy integration disabled",
            )


# Global instance
_config: TicketFairyConfig | None = None


def get_ticketfairy_config() -> TicketFairyConfig:
    """Get the TicketFairy configuration instance."""
    global _config
    if _config is None:
        _config = TicketFairyConfig.from_env()
    return _config
