"""TicketFairy integration"""

from app.integrations.ticketfairy import mcp_tools
from app.integrations.ticketfairy.base import TicketFairyIntegration

TicketFairyIntegration.mcp_tools = mcp_tools
