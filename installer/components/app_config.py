"""
Manages the application's persistent configuration file (config.json).
"""

import json
from pathlib import Path

from installer.paths import get_user_data_dir
from installer.ui import get_console

CONFIG_FILE_NAME = "config.json"


class AppConfigManager:
    """Handles reading and writing the application's config.json file."""

    def __init__(self) -> None:
        self.console = get_console()
        self.config_path = get_user_data_dir() / CONFIG_FILE_NAME
        self.config = self._load()

    def _load(self) -> dict:
        """Loads the JSON configuration from the user's data directory."""
        if not self.config_path.exists():
            return {}

        try:
            with self.config_path.open() as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.console.error(f"Error reading config file: {e}")
            return {}

    def _save(self) -> bool:
        """Saves the current configuration to the JSON file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with self.config_path.open("w") as f:
                json.dump(self.config, f, indent=2)
            # Set secure file permissions (read/write for owner only)
            Path(self.config_path).chmod(0o600)
            return True
        except OSError as e:
            self.console.error(f"Error writing config file: {e}")
            return False

    def get_value(self, key: str) -> str | None:
        """Gets a value from the configuration."""
        return self.config.get(key)

    def set_value(self, key: str, value: str) -> bool:
        """Sets a value in the configuration and saves the file."""
        self.config[key] = value
        return self._save()
