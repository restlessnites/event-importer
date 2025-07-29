from __future__ import annotations

import shutil
from pathlib import Path

from dotenv import dotenv_values

from installer.components.app_config import AppConfigManager
from installer.paths import get_user_data_dir
from installer.ui import get_console


class MigrationManager:
    """Manages migrating data from a previous installation."""

    def __init__(self) -> None:
        self.console = get_console()
        self.app_config = AppConfigManager()
        self.user_data_dir = get_user_data_dir()
        self.new_db_path = self.user_data_dir / "events.db"

    def check_and_run(self) -> None:
        """Check if a migration is needed and run if confirmed."""
        if self.app_config.config:
            self.console.info("Existing configuration found. Skipping migration.")
            return

        if self.console.confirm(
            "Check for a previous installation to migrate data from?", default=True
        ):
            self._run_migration()

    def _run_migration(self) -> None:
        """Orchestrate the data migration process."""
        source_path = self._get_old_install_path()
        if not source_path:
            self.console.info("Skipping data migration.")
            return

        self.console.step(f"Migrating data from {source_path}...")
        if self._migrate_env_file(source_path) and self._migrate_database(source_path):
            self.console.success("Data migration complete.")
        else:
            self.console.error("Data migration failed.")

    def _find_previous_installations(self) -> list[Path]:
        """Find potential previous installations by searching common locations for .env files."""
        self.console.info("Searching for previous installations...")
        search_roots = {
            Path.home(),
            Path.home() / "Documents",
            Path.home() / "Code",
            Path.home() / "Projects",
            Path.home() / "dev",
            Path.home() / "Development",
        }

        potential_paths = set()
        for root in search_roots:
            if root.is_dir():
                for path in root.glob("event-importer*/.env"):
                    potential_paths.add(path.parent.resolve())
        return sorted(list(potential_paths))

    def _get_old_install_path(self) -> Path | None:
        """Find and prompt for the path to the old installation."""
        previous_installs = self._find_previous_installations()
        if previous_installs:
            choice = self._prompt_for_install_choice(previous_installs)
            if isinstance(choice, Path):
                return choice
            if choice == "cancel":
                return None
        else:
            self.console.warning("No previous installations found automatically.")

        if self.console.confirm("Enter the path manually?", default=False):
            return self._prompt_for_manual_path()
        return None

    def _prompt_for_install_choice(self, choices: list[Path]) -> Path | str:
        """Prompt user to select from a list of found installations."""
        self.console.info("\nFound potential previous installations:")
        for i, path in enumerate(choices, 1):
            self.console.info(f"  [cyan]{i}[/cyan]: {path}")
        self.console.info("  [cyan]m[/cyan]: Enter path manually")
        self.console.info("  [cyan]c[/cyan]: Cancel migration")

        while True:
            choice = self.console.prompt("\nSelect an option", default="c")
            if choice.lower() in ("c", "cancel"):
                return "cancel"
            if choice.lower() in ("m", "manual"):
                return "manual"
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(choices):
                    return choices[idx]
            except ValueError:
                pass
            self.console.error("Invalid selection. Please try again.")

    def _prompt_for_manual_path(self) -> Path | None:
        """Prompt user to manually enter the path to an old installation."""
        while True:
            path_str = self.console.prompt(
                "\nEnter the full path to your old installation (leave blank to cancel)"
            )
            if not path_str:
                return None
            path = Path(path_str).expanduser().resolve()
            if (path / ".env").exists():
                return path
            self.console.error(f"No '.env' file found in '{path}'. Please try again.")

    def _migrate_env_file(self, source_path: Path) -> bool:
        """Read API keys from an .env file and save them to the new config.json."""
        env_path = source_path / ".env"
        if not env_path.exists():
            return True  # Nothing to migrate

        try:
            env_data = dotenv_values(env_path)
            for key, value in env_data.items():
                if value:
                    self.app_config.set_value(key, value)
            self.console.success("API keys migrated from .env file.")
            return True
        except Exception as e:
            self.console.error(f"Failed to migrate .env file: {e}")
            return False

    def _migrate_database(self, source_path: Path) -> bool:
        """Copy the events.db file from the old data directory."""
        old_db_path = source_path / "data" / "events.db"
        if not old_db_path.exists():
            self.console.info("No old database found to migrate.")
            return True

        try:
            shutil.copy(old_db_path, self.new_db_path)
            self.console.success("Database file (events.db) migrated.")
            return True
        except (OSError, shutil.Error) as e:
            self.console.error(f"Failed to migrate database file: {e}")
            return False
