"""
Centralized path management for the installer and application configuration.
"""

from pathlib import Path

APP_NAME = "event-importer"


def get_user_data_dir() -> Path:
    """Get the user data directory for the application."""
    return Path.home() / "Library" / "Application Support" / APP_NAME


def get_install_dir() -> Path:
    """Get the installation directory for the application."""
    return Path.home() / "Applications" / "restless-event-importer"


__all__ = ["APP_NAME", "get_user_data_dir", "get_install_dir"]
