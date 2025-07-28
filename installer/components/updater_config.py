"""Update configuration component."""

from __future__ import annotations

from pathlib import Path

from installer.utils import Console

from .environment import EnvironmentSetup


class UpdaterConfig:
    """Handle update configuration."""

    def __init__(self, console: Console):
        """Initialize the updater config."""
        self.console = console
        self.env_setup = EnvironmentSetup(console)

    def configure_update_url(self, project_root: Path) -> bool:
        """Configure the update file URL."""
        env_vars = self.env_setup.get_env_vars(project_root)
        if env_vars.get("UPDATE_FILE_URL"):
            self.console.success("Update URL is already configured.")
            return True

        self.console.info("\nConfigure the update file URL.")
        self.console.info("This URL points to a JSON file with update information.")
        url = self.console.prompt(
            "Enter UPDATE_FILE_URL",
            default="https://raw.githubusercontent.com/gregorry/event-importer/main/updates.json",
        )

        if url:
            if self.env_setup.update_env_var(project_root, "UPDATE_FILE_URL", url):
                self.console.success("UPDATE_FILE_URL saved")
                return True
            self.console.error("Failed to save UPDATE_FILE_URL")
            return False
        return True  # User can skip this
