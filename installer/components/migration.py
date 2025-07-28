from __future__ import annotations

import shutil
from pathlib import Path

from installer.utils import Console


class MigrationManager:
    """Manages the logic for migrating data from a previous version."""

    def __init__(self, console: Console, project_root: Path):
        self.console = console
        self.project_root = project_root

    def check_and_run(self) -> None:
        """
        Check if a migration is needed and run the process if confirmed.
        """
        if self.console.confirm(
            "Do you want to migrate data from a previous installation?",
            default=False,
        ):
            self._run_migration()
        self.console.print()

    def _run_migration(self) -> None:
        """
        Orchestrate the backup and restoration of user data.
        """
        old_install_path = self._get_old_install_path()
        if not old_install_path:
            self.console.info("Skipping data migration.")
            return

        backup_dir = self._backup_data(old_install_path)
        if backup_dir:
            self._restore_data(backup_dir)
            self.console.success("Data migration complete.")
            shutil.rmtree(backup_dir)

    def _find_previous_installations(self) -> list[Path]:
        """Finds potential previous installation directories by searching common locations."""
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
        current_project_path = self.project_root.resolve()

        for root in search_roots:
            if root.is_dir():
                for path in root.glob("event-importer*"):
                    if (
                        path.is_dir()
                        and path.resolve() != current_project_path
                        and (path / ".env").exists()
                    ):
                        potential_paths.add(path.resolve())

        return sorted(list(potential_paths))

    def _get_old_install_path(self) -> Path | None:
        """
        Find and prompt for the path to the old installation, presenting a list of
        auto-detected options if available.
        """
        previous_installs = self._find_previous_installations()

        if previous_installs:
            self.console.info("\nFound potential previous installations:")
            for i, path in enumerate(previous_installs, 1):
                self.console.info(f"  [cyan]{i}[/cyan]: {path}")

            self.console.info("  [cyan]m[/cyan]: Enter path manually")
            self.console.info("  [cyan]c[/cyan]: Cancel migration")

            while True:
                choice = self.console.prompt("\nSelect an option", default="c")
                if choice.lower() == "c":
                    self.console.error("\nMigration cancelled.")
                    return None
                if choice.lower() == "m":
                    break

                try:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(previous_installs):
                        return previous_installs[choice_idx]
                    self.console.error("Invalid selection. Please try again.")
                except ValueError:
                    self.console.error("Invalid selection. Please try again.")
        else:
            self.console.warning(
                "Could not automatically find a previous installation."
            )
            if not self.console.confirm(
                "\nWould you like to enter the path manually?", default=False
            ):
                self.console.error("\nMigration cancelled.")
                return None

        # Fallback to manual path entry
        while True:
            try:
                path_str = self.console.prompt(
                    "\nPlease enter the full path to your old installation directory (or leave blank to cancel)"
                )
                if not path_str:
                    self.console.error("\nMigration cancelled.")
                    return None

                path = Path(path_str).expanduser().resolve()
                if path.joinpath(".env").exists():
                    return path
                self.console.error(
                    f"Could not find an '.env' file in '{path}'. Please provide the correct path."
                )
            except (KeyboardInterrupt, EOFError):
                self.console.error("\nMigration cancelled.")
                return None

    def _backup_data(self, source_dir: Path) -> Path | None:
        """
        Back up .env file and data directory.
        """
        self.console.step(f"Backing up data from {source_dir}...")
        backup_dir = self.project_root.joinpath(".installer_backup")
        try:
            backup_dir.mkdir(exist_ok=True)

            # Backup .env
            env_file = source_dir / ".env"
            if env_file.exists():
                shutil.copy(env_file, backup_dir)
                self.console.success(".env file backed up.")

            # Backup data directory
            data_dir = source_dir / "data"
            if data_dir.is_dir() and any(data_dir.iterdir()):
                shutil.copytree(data_dir, backup_dir / "data", dirs_exist_ok=True)
                self.console.success("'data' directory backed up.")

            return backup_dir
        except Exception as e:
            self.console.error(f"Backup failed: {e}")
            return None

    def _restore_data(self, backup_dir: Path) -> None:
        """
        Restore backed up data to the new installation.
        """
        self.console.step("Restoring data to new installation...")
        try:
            # Restore .env
            backup_env = backup_dir / ".env"
            if backup_env.exists():
                shutil.copy(backup_env, self.project_root)
                self.console.success(".env file restored.")

            # Restore data directory
            backup_data_dir = backup_dir / "data"
            if backup_data_dir.is_dir():
                target_data_dir = self.project_root / "data"
                target_data_dir.mkdir(exist_ok=True)
                shutil.copytree(backup_data_dir, target_data_dir, dirs_exist_ok=True)
                self.console.success("'data' directory restored.")

        except Exception as e:
            self.console.error(f"Restore failed: {e}")
