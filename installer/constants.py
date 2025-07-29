"""Installer constants and configuration."""

from pydantic import BaseModel, HttpUrl


class InstallerConfig(BaseModel):
    """Installer configuration constants."""

    # URLs
    default_download_url: HttpUrl = "https://github.com/yourusername/event-importer/releases/latest/download/event-importer-macos"

    # Paths and names
    install_dir_name: str = "event-importer"
    app_binary_name: str = "event-importer"

    # Shell configuration
    path_export_line: str = 'export PATH="$HOME/Applications/event-importer:$PATH"'


# Global instance
CONFIG = InstallerConfig()
