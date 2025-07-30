"""
Centralized path management for the application and installer.
"""

import os
import platform
from pathlib import Path

from config.project import get_project

APP_NAME = get_project().name


def get_user_data_dir() -> Path:
    """Get the user data directory for the application."""
    system = platform.system()

    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if system == "Windows":
        # Use APPDATA environment variable or fallback
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / APP_NAME
        return Path.home() / "AppData" / "Roaming" / APP_NAME
    # Linux and others
    # Follow XDG Base Directory Specification
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return Path(xdg_data) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def get_install_dir() -> Path:
    """Get the installation directory for the application."""
    system = platform.system()

    if system == "Darwin":  # macOS
        return Path.home() / "Applications" / "event-importer"
    if system == "Windows":
        # Use LOCALAPPDATA or Program Files
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            return Path(localappdata) / "event-importer"
        return Path.home() / "AppData" / "Local" / "event-importer"
    # Linux and others
    return Path.home() / ".local" / "bin" / "event-importer"


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


__all__ = ["APP_NAME", "get_user_data_dir", "get_install_dir", "get_project_root"]
