"""Import agents for different event sources."""

from app.agents.dice_agent import DiceAgent
from app.agents.image_agent import ImageAgent
from app.agents.ra_agent import ResidentAdvisorAgent
from app.agents.ticketmaster_agent import TicketmasterAgent
from app.agents.web_agent import WebAgent

__all__ = [
    "ResidentAdvisorAgent",
    "TicketmasterAgent",
    "DiceAgent",
    "WebAgent",
    "ImageAgent",
]
