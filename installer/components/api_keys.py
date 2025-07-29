"""API key configuration component."""

from __future__ import annotations

from rich.table import Table

from app.shared.api_keys_info import ALL_KEYS
from installer.components.app_config import AppConfigManager
from installer.ui import get_console


class APIKeyManager:
    """Manages API key configuration."""

    def __init__(self) -> None:
        self.console = get_console()
        self.app_config = AppConfigManager()

    def show_key_status(self) -> None:
        """Display the current status of all API keys."""
        self.console.print()
        self.console.print("Current API key status:")

        missing_required_keys = 0

        table = Table(box=None, show_header=False, pad_edge=False)
        table.add_column(no_wrap=True)
        table.add_column(style="dim")

        for key, details in ALL_KEYS.items():
            has_key = self.app_config.get_value(key)
            status = "[green]✓[/green]" if has_key else "[red]✗[/red]"
            if not has_key and details["required"]:
                missing_required_keys += 1

            req_text = " (REQUIRED)" if details["required"] else " (optional)"
            key_text = f"{status} {key}{req_text}"
            table.add_row(key_text, details["description"])

        self.console.print(table)

        if missing_required_keys > 0:
            self.console.warning(
                f"⚠ You need to configure {missing_required_keys} required API key(s)."
            )

    def configure_required_keys(self) -> bool:
        """Configure all required API keys."""
        for key, details in ALL_KEYS.items():
            if details["required"] and not self._configure_key(key, details):
                return False
        return True

    def configure_optional_keys(self) -> None:
        """Configure all optional API keys."""
        for key, details in ALL_KEYS.items():
            if not details["required"]:
                self._configure_key(key, details)

    def _configure_key(self, key: str, details: dict) -> bool:
        """Prompt user for a single API key."""
        self.console.print()
        self.console.header(details["description"])
        if details["url"]:
            self.console.print(f"Get your key at: {details['url']}")

        value = self.console.prompt(f"Enter {key}")
        if value:
            self.app_config.set_value(key, value)
        return True

    def are_required_keys_present(self) -> bool:
        """Check if all required API keys are present."""
        for key, details in ALL_KEYS.items():
            if details["required"] and not self.app_config.get_value(key):
                return False
        return True

    def has_missing_optional_keys(self) -> bool:
        """Check if there are any missing optional keys."""
        for key, details in ALL_KEYS.items():
            if not details["required"] and not self.app_config.get_value(key):
                return True
        return False
