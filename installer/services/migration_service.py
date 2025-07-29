from __future__ import annotations

import shutil
from pathlib import Path

from dotenv import dotenv_values

from config.paths import get_user_data_dir
from installer.services.settings_service import SettingsService


class MigrationManager:
    """Manages migrating data from a previous installation."""

    def __init__(self) -> None:
        self.settings_manager = SettingsService()
        self.user_data_dir = get_user_data_dir()
        self.new_db_path = self.user_data_dir / "events.db"

    def is_migration_needed(self) -> bool:
        """Check if migration is needed."""
        return not self.settings_manager.get("first_run_complete")

    def migrate_from_path(self, source_path: Path) -> tuple[bool, str]:
        """Migrate data from the specified path.

        Returns:
            (success, message) tuple
        """
        env_success, env_msg = self._migrate_env_file(source_path)
        db_success, db_msg = self._migrate_database(source_path)

        success = env_success and db_success
        if success:
            return True, "Data migration complete"
        messages = []
        if not env_success:
            messages.append(f"Env: {env_msg}")
        if not db_success:
            messages.append(f"DB: {db_msg}")
        return False, "; ".join(messages)

    def _migrate_env_file(self, source_path: Path) -> tuple[bool, str]:
        """Migrate .env file with API keys."""
        env_file = source_path / ".env"
        if not env_file.exists():
            return True, "No .env file found"

        try:
            env_vars = dotenv_values(env_file)
            for key, value in env_vars.items():
                if value:
                    self.settings_manager.set(key, value)
            return True, f"Migrated {len(env_vars)} settings"
        except Exception as e:
            return False, f"Failed to migrate .env: {e}"

    def _migrate_database(self, source_path: Path) -> tuple[bool, str]:
        """Migrate the database file."""
        old_db_path = source_path / "data" / "events.db"
        if not old_db_path.exists():
            return True, "No database found"

        if self.new_db_path.exists():
            return False, "Database already exists at destination"

        try:
            self.new_db_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old_db_path, self.new_db_path)
            return True, "Database migrated"
        except Exception as e:
            return False, f"Failed to migrate database: {e}"
