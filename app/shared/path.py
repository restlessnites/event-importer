from __future__ import annotations

import sys
from pathlib import Path

from app.shared.project import get_project

APP_NAME = get_project().name


def get_project_root() -> Path:
    """Get the project root directory, handling both regular and frozen modes."""
    if getattr(sys, "frozen", False):
        # The application is running in a bundled environment (e.g., PyInstaller)
        return Path.home() / "Library" / "Application Support" / "EventImporter"
    # The application is running in a normal Python environment
    return Path(Path(__file__).resolve()).parent.parent.parent


def get_user_data_dir() -> Path:
    """
    Get the platform-specific user data directory.
    This is the central location for storing user-specific data like
    configurations and the database.
    """
    if sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    elif sys.platform == "linux":
        path = Path.home() / ".local" / "share" / APP_NAME
    else:
        path = Path.home() / f".{APP_NAME.lower()}"

    # Ensure the directory exists.
    path.mkdir(parents=True, exist_ok=True)
    return path
