"""Core installer functionality."""

from __future__ import annotations

import sys
from pathlib import Path

from rich.padding import Padding
from rich.panel import Panel

from app.config import clear_config_cache
from app.shared.project import get_project
from app.validators import InstallationValidator
from installer.components.api_keys import APIKeyManager
from installer.components.claude_desktop import ClaudeDesktopConfig
from installer.components.migration import MigrationManager
from installer.components.updater import UpdateManager
from installer.paths import get_user_data_dir
from installer.ui import get_console
from installer.utils import SystemCheck


class EventImporterInstaller:
    """Main installer orchestrator."""

    def __init__(self):
        self.console = get_console()
        self.is_packaged = self._is_packaged()
        self.project_root = self._get_project_root()
        project = get_project()
        self.version_file = self.project_root / ".version"
        self.new_version = project.version
        self.system_check = SystemCheck()
        self.claude_config = ClaudeDesktopConfig(self.console, self.is_packaged)
        self.api_key_manager = APIKeyManager()
        self.validator = InstallationValidator()
        self.migration_manager = MigrationManager()
        self.update_manager = UpdateManager(self.console, self.project_root)

    def _is_packaged(self) -> bool:
        """Check if the application is running as a packaged executable."""
        return getattr(sys, "frozen", False)

    def _get_project_root(self) -> Path:
        """Get the project root, handling both normal and packaged execution."""
        if getattr(sys, "frozen", False):
            # Running in a PyInstaller bundle, use the app support directory
            return get_user_data_dir()

        # Running in a normal Python environment
        return Path(__file__).parent.parent

    def _handle_upgrade_or_new_install(self) -> bool:
        """Handle the initial user interaction for upgrades or new installs."""
        is_upgrade = self.version_file.exists()
        current_version = self._get_current_version()

        self.console.header(f"RESTLESS / EVENT IMPORTER v{self.new_version}")

        if self.is_packaged:
            self.console.info(
                "This setup tool will guide you through configuring your application."
            )
            self.console.print()
            return True

        if is_upgrade:
            self.console.info("An existing installation was found.")
            self.console.print()
            if current_version == self.new_version:
                self.console.info(
                    f"Version [bold green]{self.new_version}[/bold green] is already installed."
                )
                prompt = "Do you want to re-check dependencies and configurations?"
            else:
                version_info = f" from v{current_version}" if current_version else ""
                self.console.info(f"Upgrading{version_info} to v{self.new_version}.")
                prompt = "Do you want to proceed with the upgrade?"

            self.console.print()
            if not self.console.confirm(prompt, default=True):
                self.console.info("Installation cancelled.")
                return False
            self.console.print()
        else:
            self.console.info(
                "This installer will check and configure all required components."
            )
            self.console.info("Previously installed components will be skipped.")
            self.console.print()
            self.migration_manager.check_and_run()
        return True

    def _handle_update_or_new_install(self) -> bool:
        """Determine whether to run an update or a new installation."""
        current_version = self._get_current_version()
        if current_version:
            self.console.header(
                f"Event Importer v{current_version} is already installed."
            )
            if self.console.confirm("Check for updates?", default=True):
                return self.update_manager.run_update()
            return True

        self.console.header(f"Installing Event Importer v{self.new_version}")
        return True

    def _run_installation_steps(self) -> bool:
        """Run the core installation steps in sequence."""
        return all(
            [
                self._pre_flight_checks(),
                self._configure_api_keys(),
                self._configure_updater(),
                self._configure_claude_desktop(),
                self._validate_installation(),
            ]
        )

    def _validate_installation(self) -> bool:
        """Run post-installation validation checks."""
        self.console.step("Validating installation...")
        clear_config_cache()
        is_valid, messages = self.validator.validate()
        if is_valid:
            self.console.success("Validation passed")
            return True

        self.console.error("Validation failed:")
        for message in messages:
            self.console.error(f"  - {message}")
        return False

    def run(self, is_packaged: bool = False) -> bool:
        """Run the complete installation process."""
        self.is_packaged = is_packaged or self._is_packaged()
        self.claude_config.is_packaged = self.is_packaged

        try:
            if not self._handle_upgrade_or_new_install():
                return True

            if self.is_packaged:
                if not self._run_packaged_install():
                    return False
            else:
                if not self._run_full_install():
                    return False

            self._write_version_file()
            self.console.print()
            self.console.success("Event Importer is ready to use!")
            self._print_next_steps()
            return True

        except KeyboardInterrupt:
            self.console.print()
            self.console.error("Installation cancelled by user.")
            return False
        except Exception as e:
            self.console.print()
            self.console.error(f"Installation failed: {e}")
            return False

    def run_update(self) -> bool:
        """Run the update process."""
        return self.update_manager.run_update()

    def _configure_updater(self) -> bool:
        """Configure the updater."""
        self.console.step("Configuring updater...")
        # TODO: Implement a more robust updater configuration
        self.console.success("Updater configured (skipping for now)")
        return True

    def _get_current_version(self) -> str | None:
        """Reads the version from the .version file."""
        if not self.version_file.exists():
            return None
        return self.version_file.read_text().strip()

    def _get_new_version(self) -> str:
        """Get the version from pyproject.toml."""
        return get_project().version

    def _write_version_file(self) -> None:
        """Writes the current app version to the .version file."""
        # This is only relevant for non-packaged installs
        self.version_file.write_text(self.new_version)

    def _pre_flight_checks(self) -> bool:
        """Perform pre-installation checks."""
        self.console.step("Performing system checks...")

        # Check OS
        if not self.system_check.is_macos():
            self.console.error("This installer is currently only supported on macOS.")
            return False

        # Check Python version
        if self.is_packaged:  # Skip Python check in packaged app
            self.console.success("System checks passed")
            return True

        python_version = self.system_check.get_python_version()
        if python_version < (3, 10):
            self.console.error(f"Python 3.10+ required. Found: {python_version}")
            return False

        self.console.success("System checks passed")
        return True

    def _configure_api_keys(self) -> bool:
        """Configure API keys interactively."""
        self.console.step("Configuring API keys...")

        # Show current status
        self.api_key_manager.show_key_status()

        # Configure required keys
        if not self.api_key_manager.configure_required_keys():
            return False

        # Offer to configure optional keys
        if self.api_key_manager.has_missing_optional_keys() and self.console.confirm(
            "\nWould you like to configure optional API keys for enhanced features?"
        ):
            self.api_key_manager.configure_optional_keys()

        self.console.success("API access configured")
        return True

    def _configure_claude_desktop(self) -> bool:
        """Configure Claude Desktop MCP integration."""
        self.console.step("Checking Claude Desktop configuration...")

        # Check if Claude Desktop is installed
        if not self.claude_config.is_claude_desktop_installed():
            self.console.warning(
                "Claude Desktop not found. Skipping MCP configuration."
            )
            self.console.info(
                "You can manually configure it later following the documentation."
            )
            return True

        # Configure MCP for a new installation
        if not self.console.confirm("Configure Claude Desktop for project?"):
            return True

        if not self.claude_config.configure(self.project_root):
            return bool(
                self.console.confirm(
                    "Failed to configure. Continue without Claude Desktop?"
                )
            )

        self.console.success("Claude Desktop ready")
        return True

    def _print_next_steps(self):
        """Print next steps for the user."""
        self.console.print()
        self.console.print(
            Panel(
                Padding(
                    "\n"
                    "1. Test the CLI:\n"
                    '   [cyan]make import URL="https://ra.co/events/1234567"[/cyan]\n\n'
                    "2. Start the API server:\n"
                    "   [cyan]make run-api[/cyan]\n\n"
                    "3. Use with Claude Desktop:\n"
                    "   - Restart Claude Desktop\n"
                    "   - Ask Claude to 'import an event from [URL]'\n\n"
                    "For more information, see the [bold]README.md[/bold] file.",
                    (1, 2),
                ),
                title="Next Steps",
                border_style="green",
                expand=False,
            )
        )

    def _run_full_install(self) -> bool:
        """Run the installation steps for a development environment."""
        (self.project_root / "data").mkdir(exist_ok=True)

        return all(
            [
                self._pre_flight_checks(),
                self._configure_api_keys(),
                self._configure_updater(),
                self._configure_claude_desktop(),
                self._validate_installation(),
            ]
        )

    def _run_packaged_install(self) -> bool:
        """Run the installation steps for a packaged application."""
        self.migration_manager.check_and_run()  # Run migrations first
        return all(
            [
                self._configure_api_keys(),
                self._configure_updater(),
                self._configure_claude_desktop(),
                self._validate_installation(),
            ]
        )


def main():
    """Entry point for the installer."""
    installer = EventImporterInstaller()
    success = installer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
