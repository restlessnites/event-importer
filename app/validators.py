"""Application-specific validators."""

from __future__ import annotations

import asyncio
import logging
import subprocess  # noqa S404
from pathlib import Path

from app.config import get_config
from app.shared.database.connection import init_db
from app.shared.http import close_http_service
from installer.components.api_keys import APIKeyManager
from installer.utils import Console

logger = logging.getLogger(__name__)


class InstallationValidator:
    """Validator for the application installation."""

    def __init__(self) -> None:
        """Initialize the validator."""
        self.config = get_config()
        self.api_key_manager = APIKeyManager(Console())
        self.messages = []

    def validate(self, project_root: Path) -> tuple[bool, list[str]]:
        """Run all validation checks."""
        self.messages = []
        self._validate_api_keys(project_root)
        self._validate_database_connection()
        return len(self.messages) == 0, self.messages

    def _validate_api_keys(self, project_root: Path) -> None:
        """Validate that all required API keys are configured."""
        is_valid, missing_keys = self.api_key_manager.validate_keys(project_root)
        if not is_valid:
            for key in missing_keys:
                self.messages.append(f"Required API key not configured: {key}")

    def _validate_database_connection(self) -> None:
        """Validate the database connection and schema."""
        try:
            init_db()
            asyncio.run(close_http_service())
        except Exception as e:
            self.messages.append(f"Database connection failed: {e}")
