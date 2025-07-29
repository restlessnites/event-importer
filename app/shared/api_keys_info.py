"""
Centralized information about all supported API keys.
"""

ALL_KEYS = {
    "ANTHROPIC_API_KEY": {
        "description": "Anthropic API key for Claude",
        "url": "https://console.anthropic.com",
    },
    "ZYTE_API_KEY": {
        "description": "Zyte API key for web scraping",
        "url": "https://www.zyte.com",
    },
    "OPENAI_API_KEY": {
        "description": "OpenAI API key (fallback LLM)",
        "url": "https://platform.openai.com",
    },
    "TICKETMASTER_API_KEY": {
        "description": "Ticketmaster API key",
        "url": "https://developer.ticketmaster.com",
    },
    "GOOGLE_API_KEY": {
        "description": "Google API key (for image/genre enhancement)",
        "url": "https://developers.google.com/custom-search",
    },
    "GOOGLE_CSE_ID": {
        "description": "Google Custom Search Engine ID",
        "url": None,
    },
    "TICKETFAIRY_API_KEY": {
        "description": "TicketFairy API key (for event submission)",
        "url": None,
    },
}
