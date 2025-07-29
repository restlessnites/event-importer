"""Installation validation for the installer."""

from __future__ import annotations

import logging

from config.settings import get_api_keys
from config.storage import SettingsStorage
from installer.paths import get_user_data_dir

logger = logging.getLogger(__name__)


class InstallationValidator:
    """Validate the Event Importer installation."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def validate(self) -> tuple[bool, list[str]]:
        """Run all validation checks."""
        self.messages = []
        self._check_api_keys()
        self._check_database()
        return len(self.messages) == 0, self.messages

    def _check_api_keys(self) -> None:
        """Check if API keys are present."""
        try:
            storage = SettingsStorage()
            api_keys = get_api_keys()

            for key in api_keys:
                value = storage.get(key)
                if not value or value.strip() == "":
                    self.messages.append(f"API key not configured: {key}")
        except Exception as e:
            self.messages.append(f"Could not check API keys: {e}")

    def _check_database(self) -> None:
        """Check if the database is accessible and initialized."""
        try:
            db_path = get_user_data_dir() / "events.db"
            if not db_path.exists():
                self.messages.append("Database does not exist")
                return

            # Try to access the settings storage
            storage = SettingsStorage(db_path)
            storage.get("first_run_complete")  # Simple test query
        except Exception as e:
            self.messages.append(f"Database connection failed: {e}")
