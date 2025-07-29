"""Directory display functions."""

from pathlib import Path

import clicycle


def display_directory_setup(
    install_dir: Path, data_dir: Path, new_installer_path: Path | None
):
    """Display directory setup information."""
    if install_dir.parent.exists():
        clicycle.info("Using installation directory:")
    else:
        clicycle.success("Created installation directory:")
    clicycle.code(str(install_dir), language="text", line_numbers=False)

    if new_installer_path:
        clicycle.info("Copied installer to:")
        clicycle.code(str(new_installer_path), language="text", line_numbers=False)

    if data_dir.exists():
        clicycle.info("Using data directory:")
    else:
        clicycle.success("Created data directory:")
    clicycle.code(str(data_dir), language="text", line_numbers=False)
