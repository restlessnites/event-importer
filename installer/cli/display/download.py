"""Download display functions."""

from pathlib import Path

import clicycle


def display_download_progress(download_url: str, app_path: Path):
    """Display download information."""
    clicycle.section("Downloading Event Importer")
    clicycle.info(f"Downloading from: {download_url}")
    clicycle.info(f"Installing to: {app_path}")


def create_progress_callback():
    """Create a progress callback for downloads."""
    progress = None

    def callback(downloaded: int, total: int):
        nonlocal progress
        if progress is None and total > 0:
            progress = clicycle.progress(
                total=total, description="Downloading Event Importer"
            )
            progress.__enter__()

        if progress and total > 0:
            progress.update(downloaded - progress.n)

        if progress and downloaded >= total:
            progress.__exit__(None, None, None)

    return callback
