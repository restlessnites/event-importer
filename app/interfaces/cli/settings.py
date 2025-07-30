"""Settings management CLI commands."""

import clicycle

from app import __version__
from config.settings import get_all_settings, get_setting_info
from config.storage import SettingsStorage


def list_settings():
    """Show all current settings."""
    storage = SettingsStorage()
    current_values = storage.get_all()
    all_settings = get_all_settings()

    clicycle.header("Current Settings")

    # Group settings by type
    api_keys = []
    app_settings = []

    for key, info in all_settings.items():
        current_value = current_values.get(key, "")
        if "API_KEY" in key or "CSE_ID" in key:
            api_keys.append((key, info, current_value))
        else:
            app_settings.append((key, info, current_value))

    if api_keys:
        clicycle.section("API Keys")
        for _key, info, value in api_keys:
            masked_value = "***set***" if value else "not set"
            clicycle.info(f"{info.display_name}: {masked_value}")

    if app_settings:
        clicycle.section("Application Settings")
        # Show version from project metadata (not stored setting)
        clicycle.info(f"Version: {__version__}")
        for _key, info, value in app_settings:
            display_value = value if value else "not set"
            clicycle.info(f"{info.display_name}: {display_value}")


def set_value(key: str, value: str):
    """Set a setting value."""
    storage = SettingsStorage()
    setting_info = get_setting_info(key)

    if not setting_info:
        clicycle.error(f"Unknown setting: {key}")
        clicycle.info("Use 'event-importer settings' to see available settings")
        return

    # No boolean settings to validate currently

    storage.set(key, value)

    # Show confirmation with masked value for API keys
    if "API_KEY" in key or "CSE_ID" in key:
        display_value = "***set***" if value else "cleared"
    else:
        display_value = value

    clicycle.success(f"Set {setting_info.display_name}: {display_value}")


def get_value(key: str):
    """Get a setting value."""
    storage = SettingsStorage()
    setting_info = get_setting_info(key)

    if not setting_info:
        clicycle.error(f"Unknown setting: {key}")
        clicycle.info("Use 'event-importer settings' to see available settings")
        return

    value = storage.get(key)

    # Show value with masking for API keys
    if "API_KEY" in key or "CSE_ID" in key:
        display_value = "***set***" if value else "not set"
    else:
        display_value = value if value else "not set"

    clicycle.info(f"{setting_info.display_name}: {display_value}")
