"""Update manager component."""

from __future__ import annotations

import logging
import shutil
import tempfile
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
        self.file_utils = FileUtils()
        self.config = get_config()

    def is_update_available(self, current_version: str) -> tuple[bool, str | None]:
        """Check if a new version is available."""
        self.console.info("Checking for new version...")
        if not self.config.update.file_url:
            self.console.warning("Update check skipped: manifest URL not configured.")
            return False, None

        manifest = self.downloader.get_json(self.config.update.file_url)
        if not manifest:
            return False, None

        latest_version = manifest.get("version")
        if latest_version and latest_version > current_version:
            self.console.success(f"New version available: {latest_version}")
            return True, manifest.get("url")

        self.console.info("You are on the latest version.")
        return False, None

    def run_update(self) -> bool:
        """Run the complete update process."""
        current_version = self._get_current_version()
        if not current_version:
            self.console.error("Cannot determine current version.")
            return False

        is_available, release_url = self.is_update_available(current_version)
        if not is_available or not release_url:
            return True

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            if not self._download_and_extract(release_url, temp_dir):
                return False

            if not self._backup_current_version():
                return False

            if not self._replace_files(temp_dir):
                self._restore_from_backup()
                return False

            self.console.success("Update completed successfully.")
            return True

    def _download_and_extract(self, release_url: str, temp_dir: Path) -> bool:
        """Download and extract the latest release."""
        zip_path = temp_dir / "event-importer.zip"
        extract_path = temp_dir / "extracted"
        if not self.downloader.download_file(release_url, zip_path):
            return False
        return self.file_utils.unzip_file(zip_path, extract_path)

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
        """Replace old files with new ones."""
        try:
            self.console.info("Replacing application files...")
            shutil.copytree(
                source_dir / "event-importer",
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
