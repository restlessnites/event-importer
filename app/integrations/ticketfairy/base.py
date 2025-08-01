"""TicketFairy integration"""

from app.integrations.base import Integration
from config import config


class TicketFairyIntegration(Integration):
    """TicketFairy integration"""

    @property
    def name(self) -> str:
        """The name of the integration"""
        return "ticketfairy"

    def is_enabled(self) -> bool:
        """Check if TicketFairy integration is properly configured."""
        return bool(config.api.ticketfairy_api_key)
