"""
API key information for the installer.
Minimal version for installer - only what's needed for setup.
"""

# Only include required keys that the installer needs to configure
REQUIRED_KEYS = {
    "ANTHROPIC_API_KEY": {
        "display_name": "ANTHROPIC_API_KEY",
        "description": "Anthropic API key for Claude",
        "instructions": "https://console.anthropic.com",
        "required": True,
    },
}

# Full list for validation
ALL_KEYS = {
    "ANTHROPIC_API_KEY": {
        "display_name": "ANTHROPIC_API_KEY",
        "description": "Anthropic API key for Claude",
        "instructions": "https://console.anthropic.com",
        "required": True,
    },
    "ZYTE_API_KEY": {
        "display_name": "ZYTE_API_KEY",
        "description": "Zyte API key for web scraping",
        "instructions": "https://www.zyte.com",
        "required": False,
    },
    "OPENAI_API_KEY": {
        "display_name": "OPENAI_API_KEY",
        "description": "OpenAI API key (fallback LLM)",
        "instructions": "https://platform.openai.com",
        "required": False,
    },
    "TICKETMASTER_API_KEY": {
        "display_name": "TICKETMASTER_API_KEY",
        "description": "Ticketmaster API key",
        "instructions": "https://developer.ticketmaster.com",
        "required": False,
    },
    "GOOGLE_API_KEY": {
        "display_name": "GOOGLE_API_KEY",
        "description": "Google API key (for image/genre enhancement)",
        "instructions": "https://developers.google.com/custom-search",
        "required": False,
    },
    "GOOGLE_CSE_ID": {
        "display_name": "GOOGLE_CSE_ID",
        "description": "Google Custom Search Engine ID",
        "instructions": None,
        "required": False,
    },
    "TICKETFAIRY_API_KEY": {
        "display_name": "TICKETFAIRY_API_KEY",
        "description": "TicketFairy API key (for event submission)",
        "instructions": None,
        "required": False,
    },
}
