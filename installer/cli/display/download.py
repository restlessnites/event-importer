"""Download display functions."""

from pathlib import Path

import clicycle


def display_download_progress(download_url: str, app_path: Path):
    """Display download information."""
    clicycle.section("Downloading")
    clicycle.info(f"Downloading from: {download_url}")
    clicycle.info(f"Installing to: {app_path}")
    clicycle.info("This may take a few minutes...")
