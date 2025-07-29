"""
Shared settings configuration using Pydantic.
"""

from pydantic import BaseModel, Field, ConfigDict


class SettingInfo(BaseModel):
    """Information about a configuration setting."""

    display_name: str
    description: str
    instructions: str | None = None
    default: str | None = None


class Settings(BaseModel):
    """All available settings for the application."""
    
    model_config = ConfigDict(extra="allow")

    # API Keys
    ANTHROPIC_API_KEY: SettingInfo = Field(
        default=SettingInfo(
            display_name="Anthropic API Key",
            description="API key for Claude (primary LLM)",
            instructions="https://console.anthropic.com",
        )
    )

    OPENAI_API_KEY: SettingInfo = Field(
        default=SettingInfo(
            display_name="OpenAI API Key",
            description="API key for ChatGPT (fallback LLM)",
            instructions="https://platform.openai.com",
        )
    )

    ZYTE_API_KEY: SettingInfo = Field(
        default=SettingInfo(
            display_name="Zyte API Key",
            description="API key for web scraping",
            instructions="https://www.zyte.com",
        )
    )

    TICKETMASTER_API_KEY: SettingInfo = Field(
        default=SettingInfo(
            display_name="Ticketmaster API Key",
            description="API key for Ticketmaster events",
            instructions="https://developer.ticketmaster.com",
        )
    )

    GOOGLE_API_KEY: SettingInfo = Field(
        default=SettingInfo(
            display_name="Google API Key",
            description="API key for image and genre enhancement",
            instructions="https://developers.google.com/custom-search",
        )
    )

    GOOGLE_CSE_ID: SettingInfo = Field(
        default=SettingInfo(
            display_name="Google CSE ID",
            description="Custom Search Engine ID for Google searches",
            instructions="https://programmablesearchengine.google.com",
        )
    )

    TICKETFAIRY_API_KEY: SettingInfo = Field(
        default=SettingInfo(
            display_name="TicketFairy API Key",
            description="API key for event submission",
            instructions=None,
        )
    )

    # Application Settings
    update_url: SettingInfo = Field(
        default=SettingInfo(
            display_name="Update URL",
            description="URL to download Event Importer updates",
            default="https://github.com/restlessnites/event-importer/releases/latest/download/event-importer-macos",
        )
    )

    version: SettingInfo = Field(
        default=SettingInfo(
            display_name="Version", description="Application version", default="1.0.0"
        )
    )

    first_run_complete: SettingInfo = Field(
        default=SettingInfo(
            display_name="First Run Complete",
            description="Whether the initial setup has been completed",
            default="false",
        )
    )


# Create a global instance
SETTINGS = Settings()


def get_api_keys() -> list[str]:
    """Get list of all API key settings."""
    return [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "ZYTE_API_KEY",
        "TICKETMASTER_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_CSE_ID",
        "TICKETFAIRY_API_KEY",
    ]


def get_all_settings() -> dict[str, SettingInfo]:
    """Get all settings with their info."""
    result = {}
    for field_name, _field in SETTINGS.__fields__.items():
        if hasattr(SETTINGS, field_name):
            result[field_name] = getattr(SETTINGS, field_name)
    return result


def get_setting_info(key: str) -> SettingInfo | None:
    """Get information about a specific setting."""
    if hasattr(SETTINGS, key):
        return getattr(SETTINGS, key)
    return None
