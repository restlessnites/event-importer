"""Dependency installation component."""

import os
import subprocess  # noqa S404
from pathlib import Path

from installer.utils import (
    ProcessRunner,
    SystemCheck,
    get_rich_console,
)


class DependencyInstaller:
    """Manages the installation of dependencies."""

    def __init__(self: "DependencyInstaller") -> None:
        """Initialize the dependency manager."""
        self.console = get_rich_console()
        self.system_check = SystemCheck()
        self.runner = ProcessRunner()

    def check_homebrew(self) -> bool:
        """Check if Homebrew is installed."""
        return self.system_check.command_exists("brew")

    def install_homebrew(self) -> bool:
        """Install Homebrew."""
        self.console.print_info("Installing Homebrew...")

        install_script = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'

        try:
            # Run the installation script
            subprocess.run(install_script, shell=True, check=True)  # noqa: S602 - Homebrew official install script  # noqa S404 B602 - trusted install script

            # Add Homebrew to PATH for the current session
            self._setup_homebrew_path()

            self.console.print_success("✓ Homebrew installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.console.print_error(f"Failed to install Homebrew: {e}")
            return False

    def _setup_homebrew_path(self):
        """Setup Homebrew PATH for the current session."""
        # Common Homebrew locations
        homebrew_paths = [
            "/opt/homebrew/bin",  # Apple Silicon
            "/usr/local/bin",  # Intel Macs
        ]

        current_path = os.environ.get("PATH", "")

        for brew_path in homebrew_paths:
            if Path(brew_path).exists() and brew_path not in current_path:
                os.environ["PATH"] = f"{brew_path}:{current_path}"

    def check_uv(self) -> bool:
        """Check if uv is installed."""
        return self.system_check.command_exists("uv")

    def install_uv(self) -> bool:
        """Install uv using Homebrew."""
        self.console.print_info("Installing uv...")

        try:
            self.runner.run(["brew", "install", "uv"])
            self.console.print_success("✓ uv installed successfully")
            return True
        except subprocess.CalledProcessError:
            # Try alternative installation method
            return self._install_uv_alternative()

    def _install_uv_alternative(self) -> bool:
        """Install uv using the official installer."""
        self.console.print_info("Trying alternative uv installation method...")

        try:
            install_cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh"
            subprocess.run(install_cmd, shell=True, check=True)  # noqa: S602 - uv official install script  # noqa S404 B602 - trusted install script

            # Add to PATH
            home = Path.home()
            uv_path = home / ".cargo" / "bin"
            if uv_path.exists():
                os.environ["PATH"] = f"{uv_path}:{os.environ.get('PATH', '')}"

            self.console.print_success("✓ uv installed successfully")
            return True
        except subprocess.CalledProcessError:
            self.console.print_error("Failed to install uv")
            return False

    def check_git(self) -> bool:
        """Check if git is installed."""
        return self.system_check.command_exists("git")

    def get_uv_path(self) -> str | None:
        """Get the full path to uv."""
        return self.system_check.get_command_path("uv")
