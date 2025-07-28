"""TicketFairy integration"""

from app.integrations.base import Integration


class TicketFairyIntegration(Integration):
    """TicketFairy integration"""

    @property
    def name(self) -> str:
        """The name of the integration"""
        return "ticketfairy"
