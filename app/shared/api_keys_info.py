"""
Centralized information about all supported API keys.
"""

ALL_KEYS = {
    "ANTHROPIC_API_KEY": {
        "description": "Anthropic API key for Claude",
        "required": True,
        "url": "https://console.anthropic.com",
    },
    "ZYTE_API_KEY": {
        "description": "Zyte API key for web scraping",
        "required": True,
        "url": "https://www.zyte.com",
    },
    "OPENAI_API_KEY": {
        "description": "OpenAI API key (fallback LLM)",
        "required": True,
        "url": "https://platform.openai.com",
    },
    "TICKETMASTER_API_KEY": {
        "description": "Ticketmaster API key",
        "required": True,
        "url": "https://developer.ticketmaster.com",
    },
    "GOOGLE_API_KEY": {
        "description": "Google API key (for image/genre enhancement)",
        "required": True,
        "url": "https://developers.google.com/custom-search",
    },
    "GOOGLE_CSE_ID": {
        "description": "Google Custom Search Engine ID",
        "required": True,
        "url": None,
    },
    "TICKETFAIRY_API_KEY": {
        "description": "TicketFairy API key (for event submission)",
        "required": True,
        "url": None,
    },
}
