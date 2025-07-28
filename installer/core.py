"""Core installer functionality."""

from __future__ import annotations

import sys
from pathlib import Path

from installer.components.api_keys import APIKeyManager
from installer.components.claude_desktop import ClaudeDesktopConfig
from installer.components.dependencies import DependencyInstaller
from installer.components.environment import EnvironmentSetup
from installer.utils import SystemCheck, get_rich_console
from installer.validators import InstallationValidator


class EventImporterInstaller:
    """Main installer orchestrator."""

    def __init__(self):
        self.console = get_rich_console()
        self.system_check = SystemCheck()
        self.dependency_installer = DependencyInstaller()
        self.env_setup = EnvironmentSetup()
        self.claude_config = ClaudeDesktopConfig()
        self.api_key_manager = APIKeyManager()
        self.validator = InstallationValidator()
        self.project_root = Path(__file__).parent.parent

    def run(self) -> bool:
        """Run the complete installation process."""
        self.console.print_header("Event Importer Setup")
        self.console.print_info("This installer will check and configure all required components.")
        self.console.print_info("Already installed components will be skipped.\n")

        try:
            # Pre-flight checks
            if not self._pre_flight_checks():
                return False

            # Install dependencies
            if not self._install_dependencies():
                return False

            # Setup environment
            if not self._setup_environment():
                return False

            # Configure API keys
            if not self._configure_api_keys():
                return False

            # Configure Claude Desktop
            if not self._configure_claude_desktop():
                return False

            # Validate installation
            if not self._validate_installation():
                return False

            self.console.print_success("\n✅ Event Importer is ready to use!")
            self._print_next_steps()
            return True

        except KeyboardInterrupt:
            self.console.print_error("\n\nInstallation cancelled by user.")
            return False
        except Exception as e:
            self.console.print_error(f"\n\nInstallation failed: {e}")
            return False

    def _pre_flight_checks(self) -> bool:
        """Perform pre-installation checks."""
        self.console.print_step("Performing system checks...")

        # Check OS
        if not self.system_check.is_macos():
            self.console.print_error(
                "This installer is currently only supported on macOS."
            )
            return False

        # Check Python version
        python_version = self.system_check.get_python_version()
        if python_version < (3, 10):
            self.console.print_error(f"Python 3.10+ required. Found: {python_version}")
            return False

        self.console.print_success("✓ System checks passed")
        return True

    def _install_dependencies(self) -> bool:
        """Install required dependencies."""
        self.console.print_step("Checking dependencies...")

        # Check and install Homebrew if needed
        if self.dependency_installer.check_homebrew():
            self.console.print_success("✓ Homebrew is already installed")
        else:
            if not self.console.confirm("Homebrew is required. Install it now?"):
                self.console.print_error("Homebrew is required to continue.")
                return False
            if not self.dependency_installer.install_homebrew():
                return False

        # Check and install uv if needed
        if self.dependency_installer.check_uv():
            self.console.print_success("✓ uv is already installed")
        else:
            self.console.print_info("uv not found, installing...")
            if not self.dependency_installer.install_uv():
                return False

        # Install Python dependencies
        self.console.print_info("Syncing Python dependencies...")
        if not self.env_setup.install_dependencies(self.project_root):
            return False

        self.console.print_success("✓ All dependencies ready")
        return True

    def _setup_environment(self) -> bool:
        """Setup the project environment."""
        self.console.print_step("Setting up environment...")

        # Create .env file if it doesn't exist
        if not self.env_setup.create_env_file(self.project_root):
            return False

        self.console.print_success("✓ Environment configured")
        return True

    def _configure_api_keys(self) -> bool:
        """Configure API keys interactively."""
        self.console.print_step("Configuring API keys...")

        # Show current status
        self.api_key_manager.show_key_status(self.project_root)

        # Configure required keys
        if not self.api_key_manager.configure_required_keys(self.project_root):
            return False

        # Offer to configure optional keys
        if self.console.confirm(
            "\nWould you like to configure optional API keys for enhanced features?"
        ):
            self.api_key_manager.configure_optional_keys(self.project_root)

        self.console.print_success("✓ API keys configured")
        return True

    def _configure_claude_desktop(self) -> bool:
        """Configure Claude Desktop MCP integration."""
        self.console.print_step("Checking Claude Desktop configuration...")

        # Check if Claude Desktop is installed
        if not self.claude_config.is_claude_desktop_installed():
            self.console.print_warning(
                "Claude Desktop not found. Skipping MCP configuration."
            )
            self.console.print_info(
                "You can manually configure it later following the documentation."
            )
            return True

        # Check if already configured
        if self.claude_config.is_already_configured(self.project_root):
            self.console.print_success("✓ Claude Desktop already configured for this project")
            if self.console.confirm("Would you like to update the configuration?") and not self.claude_config.configure(self.project_root):
                self.console.print_error("Failed to update Claude Desktop configuration.")
                return bool(
                    self.console.confirm("Continue without updating Claude Desktop configuration?")
                )
        else:
            # Configure MCP
            if not self.claude_config.configure(self.project_root):
                self.console.print_error("Failed to configure Claude Desktop.")
                return bool(
                    self.console.confirm("Continue without Claude Desktop configuration?")
                )

        self.console.print_success("✓ Claude Desktop ready")
        return True

    def _validate_installation(self) -> bool:
        """Validate the installation."""
        self.console.print_step("Validating installation...")

        results = self.validator.validate(self.project_root)

        if not results["success"]:
            self.console.print_error("\nValidation found issues:")
            for error in results["errors"]:
                self.console.print_error(f"  ✗ {error}")
            if results.get("warnings"):
                self.console.print_warning("\nWarnings:")
                for warning in results["warnings"]:
                    self.console.print_warning(f"  ⚠ {warning}")
            return bool(self.console.confirm("\nContinue anyway?"))

        self.console.print_success("✓ All components validated")
        return True

    def _print_next_steps(self):
        """Print next steps for the user."""
        self.console.print_header("Next Steps")
        print("\n1. Test the CLI:")
        print('   uv run event-importer import "https://ra.co/events/1234567"')
        print("\n2. Start the API server:")
        print("   uv run event-importer api")
        print("\n3. Use with Claude Desktop:")
        print("   - Restart Claude Desktop")
        print("   - Ask Claude to 'import an event from [URL]'")
        print("\nFor more information, see the README.md file.")


def main():
    """Entry point for the installer."""
    installer = EventImporterInstaller()
    success = installer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
