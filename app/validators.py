"""Application-specific validators."""

from __future__ import annotations

import logging

from rich.console import Console
from sqlalchemy import text

from app.config import get_config
from app.shared.api_keys_info import ALL_KEYS
from app.shared.database.connection import get_db_session, init_db
from app.shared.path import get_user_data_dir

logger = logging.getLogger(__name__)


class InstallationValidator:
    """Validate the Event Importer installation."""

    def __init__(self) -> None:
        # NOTE: We are NOT using get_console() here because this validator
        # is also used by the installer, and we don't want to create a
        # circular dependency.
        self.console = Console()
        self.messages: list[str] = []
        self.config = get_config()

    def validate(self) -> tuple[bool, list[str]]:
        """Run all validation checks."""
        self.messages = []
        self._check_api_keys()
        self._check_database()
        return len(self.messages) == 0, self.messages

    def _check_api_keys(self) -> None:
        """Check if API keys are present."""
        for key in ALL_KEYS:
            # Convert the ENV_VAR_CASE to the dataclass_case for the check
            attribute_name = key.lower()
            if not getattr(self.config.api, attribute_name, None):
                self.messages.append(f"API key not configured: {key}")

    def _check_database(self) -> None:
        """Check if the database is accessible and initialized."""
        try:
            db_path = get_user_data_dir() / "events.db"
            if not db_path.exists():
                init_db()
            else:
                # Attempt a simple query to ensure the DB is not corrupt
                with get_db_session() as db:
                    db.execute(text("SELECT 1"))
        except Exception as e:
            self.messages.append(f"Database connection failed: {e}")
