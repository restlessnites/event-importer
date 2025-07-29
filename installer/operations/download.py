"""Download operation."""

from collections.abc import Callable
from pathlib import Path

from config.paths import get_install_dir
from installer.constants import CONFIG
from installer.services.download_service import AppDownloader
from installer.services.settings_service import SettingsService


async def download_app(
    settings_manager: SettingsService,
    progress_callback: Callable[[int, int], None] | None = None
) -> Path | None:
    """Download the Event Importer app."""
    # Get download URL from config
    download_url = settings_manager.get("update_url")
    if not download_url:
        return None

    # Use centralized install directory
    install_dir = get_install_dir()
    app_path = install_dir / CONFIG.app_binary_name

    downloader = AppDownloader(download_url)
    await downloader.download(app_path, progress_callback)
    return app_path
