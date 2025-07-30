"""TicketFairy integration"""

from app.config import get_config
from app.integrations.base import Integration


class TicketFairyIntegration(Integration):
    """TicketFairy integration"""

    @property
    def name(self) -> str:
        """The name of the integration"""
        return "ticketfairy"

    def is_enabled(self) -> bool:
        """Check if TicketFairy integration is properly configured."""
        config = get_config()
        return bool(config.api.ticketfairy_api_key)
