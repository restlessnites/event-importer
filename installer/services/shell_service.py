"""Shell PATH configuration service."""

import os
from pathlib import Path

from installer.constants import CONFIG


def get_shell_profile_path() -> Path:
    """Detect and return the appropriate shell profile file."""
    shell = os.environ.get("SHELL", "/bin/bash")
    if "zsh" in shell:
        return Path.home() / ".zshrc"
    if "bash" in shell:
        return Path.home() / ".bash_profile"
    return Path.home() / ".profile"


def is_path_configured() -> bool:
    """Check if PATH is already configured."""
    profile_file = get_shell_profile_path()
    if profile_file.exists():
        content = profile_file.read_text()
        return CONFIG.install_dir_name in content
    return False


def add_to_path():
    """Add installation directory to PATH."""
    profile_file = get_shell_profile_path()

    # Add to shell profile
    with profile_file.open("a") as f:
        f.write(f"\n# Event Importer PATH\n{CONFIG.path_export_line}\n")
