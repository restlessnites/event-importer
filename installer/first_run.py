"""First run detection and installer launch."""

import sys

from config.storage import SettingsStorage
from installer.paths import get_user_data_dir


def is_first_run() -> bool:
    """Check if this is the first run of the application."""
    # Check if we have settings in SQLite storage
    try:
        storage = SettingsStorage()
        first_run_complete = storage.get("first_run_complete")
        return first_run_complete != "true"
    except Exception:
        # If SQLite fails, check for legacy config.json
        config_path = get_user_data_dir() / "config.json"
        return not config_path.exists()


def should_run_installer() -> bool:
    """Determine if the installer should run.

    Only run installer if:
    1. This is a packaged app (frozen)
    2. AND it's the first run
    """
    # Only run installer in packaged app
    if not getattr(sys, "frozen", False):
        return False

    return is_first_run()
