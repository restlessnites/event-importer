"""Launch display functions."""

import subprocess  # noqa: S404
from pathlib import Path

import clicycle


def launch_app(app_path: Path):
    """Launch the downloaded app."""
    clicycle.info("Launching Event Importer...")
    try:
        # Launch in background and exit
        subprocess.Popen(
            [str(app_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception as e:
        clicycle.error(f"Failed to launch app: {e}")
        clicycle.info(f"You can manually run: {app_path}")
