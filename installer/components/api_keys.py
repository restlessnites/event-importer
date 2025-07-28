"""API key configuration component."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table

from installer.utils import Console

from .environment import EnvironmentSetup


class APIKeyManager:
    """Handle API key configuration."""

    # Key definitions: (key_name, description, required)
    API_KEYS = [
        # Required keys
        ("ANTHROPIC_API_KEY", "Anthropic API key for Claude", True),
        ("ZYTE_API_KEY", "Zyte API key for web scraping", True),
        # Optional keys
        ("OPENAI_API_KEY", "OpenAI API key (fallback LLM)", False),
        ("TICKETMASTER_API_KEY", "Ticketmaster API key", False),
        ("GOOGLE_API_KEY", "Google API key (for image/genre enhancement)", False),
        ("GOOGLE_CSE_ID", "Google Custom Search Engine ID", False),
        ("TICKETFAIRY_API_KEY", "TicketFairy API key (for event submission)", False),
    ]

    _OPTIONAL_KEY_INSTRUCTIONS = {
        "OPENAI_API_KEY": [
            "Provides fallback if Claude is unavailable",
            "Get your key at: https://platform.openai.com",
        ],
        "TICKETMASTER_API_KEY": [
            "Enables direct Ticketmaster event imports",
            "Get your key at: https://developer.ticketmaster.com",
        ],
        "GOOGLE_API_KEY": [
            "Enables AI-powered genre discovery and image enhancement",
            "Setup at: https://console.cloud.google.com",
        ],
        "GOOGLE_CSE_ID": [
            "Works with Google API key for enhanced features",
            "Setup at: https://programmablesearchengine.google.com",
        ],
        "TICKETFAIRY_API_KEY": ["Enables event submission to TicketFairy"],
    }

    def __init__(self, console: Console):
        self.console = console
        self.env_setup = EnvironmentSetup(console)

    def show_key_status(self, project_root: Path):
        """Show current API key configuration status."""
        env_vars = self.env_setup.get_env_vars(project_root)

        self.console.info("\nCurrent API key status:")
        table = Table(box=None, show_header=False, pad_edge=False)
        table.add_column(no_wrap=True)
        table.add_column(style="dim")

        for key_name, description, required in self.API_KEYS:
            has_key = env_vars.get(key_name) and env_vars.get(key_name).strip()
            status = "[green]✓[/green]" if has_key else "[red]✗[/red]"
            req_text = " (REQUIRED)" if required else " (optional)"
            key_text = f"{status} {key_name}{req_text}"
            table.add_row(key_text, description)

        self.console.print(table)

    def has_missing_optional_keys(self, project_root: Path) -> bool:
        """Check if there are any optional keys that are not configured."""
        env_vars = self.env_setup.get_env_vars(project_root)
        optional_keys = [k for k, _, r in self.API_KEYS if not r]
        missing_optional = [k for k in optional_keys if not env_vars.get(k)]
        return len(missing_optional) > 0

    def configure_required_keys(self, project_root: Path) -> bool:
        """Configure required API keys."""
        env_vars = self.env_setup.get_env_vars(project_root)
        required_keys = [(k, d, r) for k, d, r in self.API_KEYS if r]

        missing_required = [k for k, _, _ in required_keys if not env_vars.get(k)]

        if not missing_required:
            self.console.success("Required API keys present")
            return True

        self.console.warning(
            f"\nYou need to configure {len(missing_required)} required API key(s)."
        )

        for key_name, description, _ in required_keys:
            if key_name not in missing_required:
                continue

            self.console.info(f"\n{description}")

            # Provide specific instructions for each key
            if key_name == "ANTHROPIC_API_KEY":
                self.console.info("Get your key at: https://console.anthropic.com")
            elif key_name == "ZYTE_API_KEY":
                self.console.info("Get your key at: https://www.zyte.com")

            value = self.console.prompt(f"Enter {key_name}", secret=True)

            if value:
                if self.env_setup.update_env_var(project_root, key_name, value):
                    self.console.success(f"{key_name} saved")
                else:
                    self.console.error(f"Failed to save {key_name}")
                    return False
            else:
                self.console.error(f"{key_name} is required to continue")
                return False

        return True

    def _prompt_for_single_optional_key(
        self,
        project_root: Path,
        key_name: str,
        description: str,
    ):
        """Prompt user for a single optional key and save it."""
        self.console.info(f"\n{description}")

        if instructions := self._OPTIONAL_KEY_INSTRUCTIONS.get(key_name):
            for line in instructions:
                self.console.info(line)

        if self.console.confirm(f"Configure {key_name}?", default=False):
            value = self.console.prompt(f"Enter {key_name}", secret=True)

            if value:
                if self.env_setup.update_env_var(project_root, key_name, value):
                    self.console.success(f"{key_name} saved")
                else:
                    self.console.error(f"Failed to save {key_name}")

    def configure_optional_keys(self, project_root: Path):
        """Configure optional API keys."""
        env_vars = self.env_setup.get_env_vars(project_root)
        optional_keys = [(k, d, r) for k, d, r in self.API_KEYS if not r]

        self.console.info("\nOptional API keys enable additional features:")

        for key_name, description, _ in optional_keys:
            if not env_vars.get(key_name):
                self._prompt_for_single_optional_key(
                    project_root,
                    key_name,
                    description,
                )

    def validate_keys(self, project_root: Path) -> tuple[bool, list[str]]:
        """Validate that all required keys are present."""
        env_vars = self.env_setup.get_env_vars(project_root)
        missing = []

        for key_name, _, required in self.API_KEYS:
            if required and not env_vars.get(key_name):
                missing.append(key_name)

        return len(missing) == 0, missing
