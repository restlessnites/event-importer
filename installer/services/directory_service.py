"""Directory management service."""

import os
import shutil
import sys
from pathlib import Path

from config.paths import get_install_dir, get_user_data_dir


def create_installation_directory() -> Path:
    """Create and validate installation directories."""
    install_dir = get_install_dir()

    # First ensure ~/Applications exists
    apps_dir = install_dir.parent
    if not apps_dir.exists():
        apps_dir.mkdir(parents=True, exist_ok=True)

    # Now create the event-importer directory
    if not install_dir.exists():
        install_dir.mkdir(parents=True, exist_ok=True)

    # Check if we have write permissions
    if not os.access(install_dir, os.W_OK):
        raise PermissionError(f"No write permission to: {install_dir}")

    return install_dir


def move_installer_to_install_dir(install_dir: Path) -> Path | None:
    """Move installer to installation directory if needed."""
    current_path = Path(sys.argv[0]).resolve()
    if current_path.parent != install_dir:
        new_installer_path = install_dir / current_path.name
        shutil.copy2(current_path, new_installer_path)
        return new_installer_path
    return None


def create_data_directory() -> Path:
    """Create data directory if needed."""
    data_dir = get_user_data_dir()
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def cleanup_download_location(installer_path: Path):
    """Clean up the original download location."""
    parent_dir = installer_path.parent
    # Look for zip files in the parent directory
    for zip_file in parent_dir.glob("*.zip"):
        if zip_file.stem in installer_path.stem:
            zip_file.unlink()
            break

    # Remove the temporary directory if it looks like a download location
    if (
        parent_dir.name.startswith("event-importer")
        and len(list(parent_dir.iterdir())) <= 1
    ):
        shutil.rmtree(parent_dir, ignore_errors=True)
