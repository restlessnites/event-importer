"""Handles the upgrade process from a previous installation."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from installer.utils import RichConsole


class UpgradeManager:
    """Manages the logic for upgrading from a previous version."""

    def __init__(self, console: RichConsole, project_root: Path):
        self.console = console
        self.project_root = project_root

    def check_and_run(self) -> None:
        """
        Check if an upgrade is needed and run the process if confirmed.
        """
        if self.project_root.joinpath(".env").exists():
            if self.console.confirm(
                "An existing installation was found. Do you want to "
                "upgrade and migrate your data?"
            ):
                self._run_upgrade()
        else:
            if self.console.confirm(
                "Do you want to migrate data from a previous installation?"
            ):
                self._run_upgrade()

    def _run_upgrade(self) -> None:
        """
        Orchestrate the backup and restoration of user data.
        """
        old_install_path = self._get_old_install_path()
        if not old_install_path:
            self.console.print_info("Skipping data migration.")
            return

        backup_dir = self._backup_data(old_install_path)
        if backup_dir:
            self._restore_data(backup_dir)
            self.console.print_success("✅ Data migration complete.")
            shutil.rmtree(backup_dir)

    def _get_old_install_path(self) -> Path | None:
        """
        Prompt the user for the path to their old installation.
        """
        while True:
            try:
                path_str = self.console.prompt(
                    "Enter the full path to your old installation directory"
                )
                path = Path(path_str).expanduser().resolve()
                if path.joinpath(".env").exists():
                    return path
                self.console.print_error(
                    f"Could not find an '.env' file in '{path}'. "
                    "Please provide the correct path."
                )
            except (KeyboardInterrupt, EOFError):
                self.console.print_error("\nMigration cancelled.")
                return None

    def _backup_data(self, source_dir: Path) -> Path | None:
        """
        Back up .env file and data directory.
        """
        self.console.print_step(f"Backing up data from {source_dir}...")
        backup_dir = self.project_root.joinpath(".installer_backup")
        try:
            backup_dir.mkdir(exist_ok=True)

            # Backup .env
            env_file = source_dir / ".env"
            if env_file.exists():
                shutil.copy(env_file, backup_dir)
                self.console.print_info("✓ .env file backed up.")

            # Backup data directory
            data_dir = source_dir / "data"
            if data_dir.is_dir() and any(data_dir.iterdir()):
                shutil.copytree(
                    data_dir, backup_dir / "data", dirs_exist_ok=True
                )
                self.console.print_info("✓ 'data' directory backed up.")

            return backup_dir
        except Exception as e:
            self.console.print_error(f"Backup failed: {e}")
            return None

    def _restore_data(self, backup_dir: Path) -> None:
        """
        Restore backed up data to the new installation.
        """
        self.console.print_step("Restoring data to new installation...")
        try:
            # Restore .env
            backup_env = backup_dir / ".env"
            if backup_env.exists():
                shutil.copy(backup_env, self.project_root)
                self.console.print_info("✓ .env file restored.")

            # Restore data directory
            backup_data_dir = backup_dir / "data"
            if backup_data_dir.is_dir():
                target_data_dir = self.project_root / "data"
                target_data_dir.mkdir(exist_ok=True)
                shutil.copytree(
                    backup_data_dir, target_data_dir, dirs_exist_ok=True
                )
                self.console.print_info("✓ 'data' directory restored.")

        except Exception as e:
            self.console.print_error(f"Restore failed: {e}")
