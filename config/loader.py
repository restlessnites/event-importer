"""Configuration loading utilities."""

import json
import logging
import sys
from typing import Any

from config.paths import get_user_data_dir
from config.storage import SettingsStorage

logger = logging.getLogger(__name__)


def load_config() -> dict[str, Any]:
    """Load configuration from SQLite storage (for packaged app) or fallback to JSON."""
    # Only use storage when running as packaged app
    if getattr(sys, "frozen", False):
        try:
            # Try SQLite storage first
            storage = SettingsStorage(get_user_data_dir() / "events.db")
            settings = storage.get_all()
            if settings:
                return settings
        except Exception as e:
            logger.debug("Failed to load config from SQLite storage: %s", e)

        # Fallback to old config.json if SQLite fails
        config_path = get_user_data_dir() / "config.json"
        if config_path.exists():
            try:
                with config_path.open() as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                pass
    return {}
