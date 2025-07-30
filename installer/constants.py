"""Installer constants and configuration."""

from pydantic import BaseModel, HttpUrl


class InstallerConfig(BaseModel):
    """Installer configuration constants."""

    # URLs
    default_download_url: HttpUrl = "https://www.dropbox.com/scl/fi/23ei2qsvi4i1zfupueku2/event-importer.zip?rlkey=gnwj4hh5i3ghjiejhiw0mqnxp&st=1bokuegr&dl=1"

    # Paths and names
    install_dir_name: str = "event-importer"
    app_binary_name: str = "event-importer"

    # Shell configuration
    path_export_line: str = 'export PATH="$HOME/Applications/event-importer:$PATH"'


# Global instance
CONFIG = InstallerConfig()
