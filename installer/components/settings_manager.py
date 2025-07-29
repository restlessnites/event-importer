"""Settings configuration component."""

from __future__ import annotations

from config.storage import SettingsStorage
from installer.paths import get_user_data_dir


class SettingsManager:
    """Simple wrapper around settings storage."""

    def __init__(self) -> None:
        self.storage = SettingsStorage()

        # Migrate from old config.json if it exists
        old_config_path = get_user_data_dir() / "config.json"
        if old_config_path.exists() and self.storage.migrate_from_json_file(old_config_path):
            # Rename old file to backup
            old_config_path.rename(old_config_path.with_suffix(".json.backup"))

    def get(self, key: str) -> str | None:
        """Get a setting value."""
        return self.storage.get(key)

    def set(self, key: str, value: str) -> None:
        """Set a setting value."""
        self.storage.set(key, value)

    def get_all(self) -> dict[str, str]:
        """Get all current settings."""
        return self.storage.get_all()
