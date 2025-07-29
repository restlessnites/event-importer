"""Update manager component."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.config import get_config
from installer.utils import Console, Downloader, FileUtils

logger = logging.getLogger(__name__)

# Constants
BACKUP_DIR_NAME = "backup"


class UpdateManager:
    """Manages the application update process."""

    def __init__(self: UpdateManager, console: Console, project_root: Path) -> None:
        """Initialize the update manager."""
        self.console = console
        self.project_root = project_root
        self.downloader = Downloader(self.console)
        self.file_utils = FileUtils(self.console)
        self.config = get_config()

    def run_update(self) -> bool:
        """Run the complete update process."""
        self.console.header("Starting application update")

        if not self.config.update.file_url:
            self.console.warning("Update check skipped: URL not configured.")
            return True

        temp_dir = self.project_root / "tmp_update"
        try:
            temp_dir.mkdir(exist_ok=True)
            zip_path = temp_dir / "update.zip"
            extract_path = temp_dir / "extracted"

            # Step 1: Download
            if not self.downloader.download_file(self.config.update.file_url, zip_path):
                return False
            self.console.success("Download complete.")

            # Step 2: Check Version
            with self.console.rich_console.status(
                "Checking for new version..."
            ) as status:
                if not self.file_utils.unzip_file(zip_path, extract_path):
                    return False

                version_file = self.file_utils.find_file_up(".version", extract_path)
                if not version_file:
                    self.console.error("Could not find .version file in the update.")
                    return False

                latest_version = version_file.read_text().strip()
                current_version = self._get_current_version()

                if current_version and latest_version <= current_version:
                    self.console.success(
                        f"You are already on the latest version ({current_version})."
                    )
                    return True
                status.update(f"New version found: {latest_version}")

            # Step 3: Install
            with self.console.rich_console.status("Installing update...") as status:
                status.update("Backing up current installation...")
                if not self._backup_current_version():
                    return False

                status.update("Replacing files...")
                if not self._replace_files(extract_path):
                    self._restore_from_backup()
                    return False

            self.console.success(f"Update to version {latest_version} complete.")
            return True

        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def _backup_current_version(self) -> bool:
        """Create a backup of the current installation."""
        backup_dir = self.project_root / BACKUP_DIR_NAME
        try:
            self.console.info(f"Backing up current version to {backup_dir}...")
            shutil.copytree(self.project_root, backup_dir, dirs_exist_ok=True)
            self.console.success("Backup created successfully.")
            return True
        except Exception as e:
            self.console.error(f"Backup failed: {e}")
            return False

    def _replace_files(self, source_dir: Path) -> bool:
        """Replace old files with new ones, searching for the source."""
        try:
            self.console.info("Replacing application files...")

            # Find the actual source directory inside the extracted folder
            app_source_dir = source_dir
            if not (source_dir / "app").exists():
                for child in source_dir.iterdir():
                    if child.is_dir() and (child / "app").exists():
                        app_source_dir = child
                        break

            shutil.copytree(
                app_source_dir,
                self.project_root,
                dirs_exist_ok=True,
            )
            self.console.success("Files replaced successfully.")
            return True
        except Exception as e:
            self.console.error(f"File replacement failed: {e}")
            return False

    def _restore_from_backup(self) -> None:
        """Restore the installation from a backup."""
        backup_dir = self.project_root / BACKUP_DIR_NAME
        self.console.info("Restoring from backup...")
        try:
            shutil.copytree(backup_dir, self.project_root, dirs_exist_ok=True)
            self.console.success("Restored from backup.")
        except Exception as e:
            self.console.error(f"Restore failed: {e}")

    def _get_current_version(self) -> str | None:
        """Get the current installed version from the project root."""
        version_file = self.project_root / ".version"
        if version_file.exists():
            return version_file.read_text().strip()
        return None
