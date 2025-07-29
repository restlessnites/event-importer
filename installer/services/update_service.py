"""Update service for Event Importer."""


from config.paths import get_install_dir
from installer.constants import CONFIG
from installer.services.download_service import AppDownloader
from installer.services.settings_service import SettingsService


class UpdateService:
    """Handle app updates."""

    def __init__(self, settings_manager: SettingsService):
        self.settings_manager = settings_manager

    async def check_and_update(self) -> tuple[bool, str]:
        """Check for updates and download if available."""
        download_url = self.settings_manager.get("update_url")
        if not download_url:
            return False, "No update URL configured"

        install_dir = get_install_dir()
        app_path = install_dir / CONFIG.app_binary_name
        backup_path = app_path.with_suffix(".backup")

        try:
            # Backup current version
            if app_path.exists():
                app_path.rename(backup_path)

            # Download new version
            downloader = AppDownloader(download_url)
            await downloader.download(app_path)

            # Remove backup on success
            if backup_path.exists():
                backup_path.unlink()

            return True, "Update completed successfully"

        except Exception as e:
            # Restore backup on failure
            if backup_path.exists() and not app_path.exists():
                backup_path.rename(app_path)
            return False, f"Update failed: {e}"
