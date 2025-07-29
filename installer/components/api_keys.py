"""API key configuration component."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table

from installer.components.environment import EnvironmentSetup
from installer.utils import Console

ALL_KEYS = {
    "ANTHROPIC_API_KEY": {
        "description": "Anthropic API key for Claude",
        "required": True,
        "url": "https://console.anthropic.com",
    },
    "ZYTE_API_KEY": {
        "description": "Zyte API key for web scraping",
        "required": True,
        "url": "https://www.zyte.com",
    },
    "OPENAI_API_KEY": {
        "description": "OpenAI API key (fallback LLM)",
        "required": False,
        "url": "https://platform.openai.com",
    },
    "TICKETMASTER_API_KEY": {
        "description": "Ticketmaster API key",
        "required": False,
        "url": "https://developer.ticketmaster.com",
    },
    "GOOGLE_API_KEY": {
        "description": "Google API key (for image/genre enhancement)",
        "required": False,
        "url": "https://developers.google.com/custom-search",
    },
    "GOOGLE_CSE_ID": {
        "description": "Google Custom Search Engine ID",
        "required": False,
        "url": None,
    },
    "TICKETFAIRY_API_KEY": {
        "description": "TicketFairy API key (for event submission)",
        "required": False,
        "url": None,
    },
}


class APIKeyManager:
    """Manages API key configuration."""

    def __init__(self, console: Console, project_root: Path):
        self.console = console
        self.project_root = project_root
        self.env_setup = EnvironmentSetup(console, project_root)

    def show_key_status(self, project_root: Path):
        """Display the current status of all API keys."""
        self.console.print()
        self.console.print("Current API key status:")

        env_vars = self.env_setup.get_env_vars(project_root)
        missing_required_keys = 0

        table = Table(box=None, show_header=False, pad_edge=False)
        table.add_column(no_wrap=True)
        table.add_column(style="dim")

        for key, details in ALL_KEYS.items():
            has_key = env_vars.get(key) and env_vars.get(key).strip()
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

    def configure_required_keys(self, project_root: Path) -> bool:
        """Configure all required API keys."""
        for key, details in ALL_KEYS.items():
            if details["required"] and not self._configure_key(
                key, details, project_root
            ):
                return False
        return True

    def configure_optional_keys(self, project_root: Path):
        """Configure all optional API keys."""
        for key, details in ALL_KEYS.items():
            if not details["required"]:
                self._configure_key(key, details, project_root)

    def _configure_key(self, key: str, details: dict, project_root: Path) -> bool:
        """Prompt user for a single API key."""
        self.console.print()
        self.console.header(details["description"])
        if details["url"]:
            self.console.print(f"Get your key at: {details['url']}")

        value = self.console.prompt(f"Enter {key}")
        if value:
            self.env_setup.update_env_var(key, value, project_root)
        return True

    def are_required_keys_present(self, project_root: Path) -> bool:
        """Check if all required API keys are present."""
        env_vars = self.env_setup.get_env_vars(project_root)
        missing_required_keys = 0
        for key, details in ALL_KEYS.items():
            if details["required"] and not env_vars.get(key):
                missing_required_keys += 1
        return missing_required_keys == 0

    def has_missing_optional_keys(self, project_root: Path) -> bool:
        """Check if there are any missing optional keys."""
        env_vars = self.env_setup.get_env_vars(project_root)
        for key, details in ALL_KEYS.items():
            if not details["required"] and not env_vars.get(key):
                return True
        return False
