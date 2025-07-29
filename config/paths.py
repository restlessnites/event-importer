"""
Centralized path management for the application and installer.
"""

from pathlib import Path

from config.project import get_project

APP_NAME = get_project().name


def get_user_data_dir() -> Path:
    """Get the user data directory for the application."""
    return Path.home() / "Library" / "Application Support" / APP_NAME


def get_install_dir() -> Path:
    """Get the installation directory for the application."""
    return Path.home() / "Applications" / "event-importer"


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


__all__ = ["APP_NAME", "get_user_data_dir", "get_install_dir", "get_project_root"]
