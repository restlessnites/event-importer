from __future__ import annotations

import shutil
from pathlib import Path

import clicycle
from dotenv import dotenv_values

from installer.components.settings_manager import SettingsManager
from installer.paths import get_user_data_dir


class MigrationManager:
    """Manages migrating data from a previous installation."""

    def __init__(self) -> None:
        self.settings_manager = SettingsManager()
        self.user_data_dir = get_user_data_dir()
        self.new_db_path = self.user_data_dir / "events.db"

    def check_and_run(self) -> None:
        """Check if a migration is needed and run if confirmed."""
        if self.settings_manager.get("first_run_complete"):
            clicycle.info("Existing configuration found. Skipping migration.")
            return

        if clicycle.confirm("Check for a previous installation to migrate data from?"):
            self._run_migration()

    def migrate_from_path(self, source_path: Path) -> bool:
        """Migrate data from the specified path."""
        clicycle.info(f"Migrating data from {source_path}...")
        success = self._migrate_env_file(source_path) and self._migrate_database(
            source_path
        )
        if success:
            clicycle.success("Data migration complete.")
        else:
            clicycle.error("Data migration failed.")
        return success

    def _run_migration(self) -> None:
        """Orchestrate the data migration process."""
        source_path = self._get_old_install_path()
        if not source_path:
            clicycle.info("Skipping data migration.")
            return

        self.migrate_from_path(source_path)

    def _get_old_install_path(self) -> Path | None:
        """Get the path to migrate from - just ask the user."""
        return self._prompt_for_manual_path()

    def _prompt_for_manual_path(self) -> Path | None:
        """Prompt user to manually enter the path to an old installation."""
        path_str = clicycle.prompt("Enter the full path to your old installation")
        if not path_str:
            return None
        return Path(path_str).expanduser().resolve()

    def _migrate_env_file(self, source_path: Path) -> bool:
        """Read API keys from an .env file and save them to the new config.json."""
        env_path = source_path / ".env"
        if not env_path.exists():
            return True  # Nothing to migrate

        try:
            env_data = dotenv_values(env_path)
            for key, value in env_data.items():
                if value:
                    self.settings_manager.set(key.lower(), value)
            clicycle.success("API keys migrated from .env file.")
            return True
        except Exception as e:
            clicycle.error(f"Failed to migrate .env file: {e}")
            return False

    def _migrate_database(self, source_path: Path) -> bool:
        """Copy the events.db file from the old data directory."""
        old_db_path = source_path / "data" / "events.db"
        if not old_db_path.exists():
            clicycle.info("No old database found to migrate.")
            return True

        try:
            shutil.copy(old_db_path, self.new_db_path)
            clicycle.success("Database file (events.db) migrated.")
            return True
        except (OSError, shutil.Error) as e:
            clicycle.error(f"Failed to migrate database file: {e}")
            return False
