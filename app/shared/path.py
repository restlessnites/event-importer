from __future__ import annotations

import os
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory, handling both regular and frozen modes."""
    if getattr(sys, "frozen", False):
        # The application is running in a bundled environment (e.g., PyInstaller)
        return Path.home() / "Library" / "Application Support" / "EventImporter"
    # The application is running in a normal Python environment
    return Path(os.path.abspath(__file__)).parent.parent.parent
