"""Configuration operations."""

from config.settings import get_api_keys
from installer.constants import CONFIG
from installer.services.settings_service import SettingsService


def get_missing_api_keys(settings_manager: SettingsService) -> list[str]:
    """Get list of missing API keys."""
    missing_keys = []
    for key in get_api_keys():
        if not settings_manager.get(key):
            missing_keys.append(key)
    return missing_keys


def set_download_url_if_missing(settings_manager: SettingsService):
    """Set default download URL if not configured."""
    if not settings_manager.get("update_url"):
        settings_manager.set("update_url", str(CONFIG.default_download_url))
