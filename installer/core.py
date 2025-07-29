"""Core installer functionality."""

from __future__ import annotations

import sys
from pathlib import Path

from rich.padding import Padding
from rich.panel import Panel

from app.config import clear_config_cache
from app.validators import InstallationValidator
from installer.components.api_keys import APIKeyManager
from installer.components.claude_desktop import ClaudeDesktopConfig
from installer.components.dependencies import DependencyInstaller
from installer.components.environment import EnvironmentSetup
from installer.components.migration import MigrationManager
from installer.components.updater import UpdateManager
from installer.utils import Console, SystemCheck


class EventImporterInstaller:
    """Main installer orchestrator."""

    def __init__(self):
        self.console = Console()
        self.project_root = Path(__file__).parent.parent
        self.version_file = self.project_root / ".version"
        self.new_version = self._get_new_version()
        self.system_check = SystemCheck()
        self.dependency_installer = DependencyInstaller(self.console)
        self.env_setup = EnvironmentSetup(self.console)
        self.claude_config = ClaudeDesktopConfig(self.console)
        self.api_key_manager = APIKeyManager(self.console)
        self.validator = InstallationValidator()
        self.migration_manager = MigrationManager(self.console, self.project_root)
        self.update_manager = UpdateManager(self.console, self.project_root)

    def _handle_upgrade_or_new_install(self) -> bool:
        """Handle the initial user interaction for upgrades or new installs."""
        is_upgrade = self.version_file.exists()
        current_version = self._get_current_version()

        self.console.header(f"RESTLESS / EVENT IMPORTER v{self.new_version}")

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
                self._install_dependencies(),
                self._setup_environment(),
                self._create_data_directory(),
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
        is_valid, messages = self.validator.validate(self.project_root)
        if is_valid:
            self.console.success("Validation passed")
            return True

        self.console.error("Validation failed:")
        for message in messages:
            self.console.error(f"  - {message}")
        return False

    def run(self) -> bool:
        """Run the complete installation process."""
        try:
            if not self._handle_upgrade_or_new_install():
                return True  # User cancelled, not an error

            if not self._run_installation_steps():
                return False

            self._write_version_file()
            self.console.print()
            self.console.success("Event Importer is ready to use!")
            self._print_next_steps()
            return True

        except KeyboardInterrupt:
            self.console.print()  # Move to a new line for the cancellation message
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
        return self.env_setup.configure_update_url(self.project_root)

    def _get_current_version(self) -> str | None:
        """Reads the version from the .version file."""
        if not self.version_file.exists():
            return None
        return self.version_file.read_text().strip()

    def _get_new_version(self) -> str:
        """Get the version from pyproject.toml."""
        pyproject_path = self.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            return "N/A"

        # Simple parser to avoid heavy dependencies
        with pyproject_path.open() as f:
            for line in f:
                if line.strip().startswith("version"):
                    return line.split("=")[1].strip().replace('"', "")
        return "N/A"

    def _write_version_file(self) -> None:
        """Writes the current app version to the .version file."""
        self.version_file.write_text(self.new_version)

    def _pre_flight_checks(self) -> bool:
        """Perform pre-installation checks."""
        self.console.step("Performing system checks...")

        # Check OS
        if not self.system_check.is_macos():
            self.console.error("This installer is currently only supported on macOS.")
            return False

        # Check Python version
        python_version = self.system_check.get_python_version()
        if python_version < (3, 10):
            self.console.error(f"Python 3.10+ required. Found: {python_version}")
            return False

        self.console.success("System checks passed")
        return True

    def _install_dependencies(self) -> bool:
        """Install required dependencies."""
        self.console.step("Checking dependencies...")

        # Check and install Homebrew if needed
        if self.dependency_installer.check_homebrew():
            self.console.success("Homebrew is already installed")
        else:
            if not self.console.confirm("Homebrew is required. Install it now?"):
                self.console.error("Homebrew is required to continue.")
                return False
            if not self.dependency_installer.install_homebrew():
                return False

        # Check and install uv if needed
        if self.dependency_installer.check_uv():
            self.console.success("uv is already installed")
        else:
            self.console.info("uv not found, installing...")
            if not self.dependency_installer.install_uv():
                return False

        # Install Python dependencies
        with self.console.rich_console.status(
            "[bold green]Syncing Python dependencies..."
        ):
            if not self.env_setup.install_dependencies(self.project_root):
                self.console.error("Failed to install Python dependencies.")
                return False

        self.console.success("Python dependencies installed")
        self.console.success("All dependencies ready")
        return True

    def _setup_environment(self) -> bool:
        """Setup the project environment."""
        self.console.step("Setting up environment...")

        # Create .env file if it doesn't exist
        if not self.env_setup.create_env_file(self.project_root):
            return False

        self.console.success("Environment configured")
        return True

    def _create_data_directory(self) -> bool:
        """Create the data directory if it doesn't exist."""
        self.console.step("Creating data directory...")
        try:
            (self.project_root / "data").mkdir(exist_ok=True)
            self.console.success("Data directory ready")
            return True
        except Exception as e:
            self.console.error(f"Failed to create data directory: {e}")
            return False

    def _configure_api_keys(self) -> bool:
        """Configure API keys interactively."""
        self.console.step("Configuring API keys...")

        # Show current status
        self.api_key_manager.show_key_status(self.project_root)

        # Configure required keys
        if not self.api_key_manager.configure_required_keys(self.project_root):
            return False

        # Offer to configure optional keys
        if self.api_key_manager.has_missing_optional_keys(
            self.project_root
        ) and self.console.confirm(
            "\nWould you like to configure optional API keys for enhanced features?"
        ):
            self.api_key_manager.configure_optional_keys(self.project_root)

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

        # Check if already configured
        if self.claude_config.is_already_configured(self.project_root):
            self.console.success("Claude Desktop already configured for this project")
            # In an upgrade scenario, just verify. The user might have
            # moved the project folder, so we may need to re-configure.
            if self.claude_config.verify_configuration(self.project_root):
                return True
            self.console.info(
                "Project path seems to have changed. "
                "Updating Claude Desktop configuration..."
            )
            if not self.claude_config.configure(self.project_root):
                return bool(
                    self.console.confirm(
                        "Failed to update. Continue without Claude Desktop?"
                    )
                )
        else:
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


def main():
    """Entry point for the installer."""
    installer = EventImporterInstaller()
    success = installer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
