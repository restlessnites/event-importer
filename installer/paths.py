"""
Centralized path management for the installer and application configuration.
"""

import sys
from pathlib import Path

APP_NAME = "EventImporter"

def get_user_data_dir() -> Path:
    """
    Get the platform-specific user data directory where the application will run.
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