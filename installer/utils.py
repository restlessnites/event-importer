"""Installer utility functions."""

import getpass
import platform
import shutil
import subprocess  # noqa S404
import sys
from pathlib import Path

from rich.console import Console

_console: Console | None = None


def get_rich_console() -> Console:
    """Get a rich console instance."""
    global _console
    if _console is None:
        _console = Console()
    return _console


class Console:
    """Console output utilities with consistent formatting."""

    # ANSI color codes
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"

    def print_header(self, text: str):
        """Print a header."""
        print(f"\n{self.BOLD}{self.BLUE}{'=' * 50}{self.RESET}")
        print(f"{self.BOLD}{self.BLUE}{text.center(50)}{self.RESET}")
        print(f"{self.BOLD}{self.BLUE}{'=' * 50}{self.RESET}\n")

    def print_step(self, text: str):
        """Print a step message."""
        print(f"\n{self.BOLD}{self.CYAN}→ {text}{self.RESET}")

    def print_success(self, text: str):
        """Print a success message."""
        print(f"{self.GREEN}{text}{self.RESET}")

    def print_error(self, text: str):
        """Print an error message."""
        print(f"{self.RED}{text}{self.RESET}", file=sys.stderr)

    def print_warning(self, text: str):
        """Print a warning message."""
        print(f"{self.YELLOW}{text}{self.RESET}")

    def print_info(self, text: str):
        """Print an info message."""
        print(f"{text}")

    def confirm(self, prompt: str, default: bool = True) -> bool:
        """Ask for user confirmation."""
        default_str = "Y/n" if default else "y/N"
        while True:
            response = input(f"{prompt} [{default_str}]: ").strip().lower()
            if not response:
                return default
            if response in ["y", "yes"]:
                return True
            if response in ["n", "no"]:
                return False
            print("Please enter 'y' or 'n'")

    def get_input(
        self, prompt: str, default: str | None = None, hide_input: bool = False
    ) -> str:
        """Get user input with optional default."""
        prompt = f"{prompt} [{default}]: " if default else f"{prompt}: "

        value = getpass.getpass(prompt) if hide_input else input(prompt).strip()

        return value or default or ""


class SystemCheck:
    """System checking utilities."""

    def is_macos(self) -> bool:
        """Check if running on macOS."""
        return platform.system() == "Darwin"

    def get_python_version(self) -> tuple[int, int]:
        """Get Python version as tuple."""
        return (sys.version_info.major, sys.version_info.minor)

    def command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            subprocess.run(  # noqa: S603,S607 - which is a safe system command
                ["which", command],  # noqa: S607
                capture_output=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def get_command_path(self, command: str) -> str | None:
        """Get the full path to a command."""
        try:
            result = subprocess.run(  # noqa: S603,S607 - which is a safe system command
                ["which", command],  # noqa: S607
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None


class ProcessRunner:
    """Run external processes with proper error handling."""

    def __init__(self):
        self.console = Console()

    def run(
        self,
        command: list[str],
        check: bool = True,
        capture_output: bool = True,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        """Run a command with error handling."""
        try:
            return subprocess.run(  # noqa: S603 - commands are validated by callers
                command, check=check, capture_output=capture_output, text=True, **kwargs
            )
        except subprocess.CalledProcessError as e:
            self.console.print_error(f"Command failed: {' '.join(command)}")
            self.console.print_error(f"  Exit code: {e.returncode}")
            if e.stdout:
                self.console.print_error(f"  Stdout: {e.stdout.strip()}")
            if e.stderr:
                self.console.print_error(f"  Stderr: {e.stderr.strip()}")
            raise
        except FileNotFoundError:
            self.console.print_error(f"Command not found: {command[0]}")
            raise


class FileUtils:
    """File system utilities."""

    @staticmethod
    def find_file_up(filename: str, start_path: Path) -> Path | None:
        """Find a file by searching up the directory tree."""
        current = start_path
        while current != current.parent:
            file_path = current / filename
            if file_path.exists():
                return file_path
            current = current.parent
        return None

    @staticmethod
    def ensure_directory(path: Path) -> bool:
        """Ensure a directory exists."""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    @staticmethod
    def backup_file(file_path: Path) -> Path | None:
        """Create a backup of a file."""
        if file_path.exists():
            backup_path = file_path.with_suffix(f"{file_path.suffix}.bak")
            try:
                shutil.copy2(file_path, backup_path)
                return backup_path
            except Exception as e:
                console = get_rich_console()
                console.print(
                    f"Failed to create backup for {file_path}: {e}", style="bold red"
                )
        return None


def get_user_input(
    prompt: str,
    default: str | None = None,
    hide_input: bool = False,
) -> str:
    """Get user input with a prompt and optional default."""
    console = get_rich_console()
    while True:
        value = getpass.getpass(prompt) if hide_input else input(prompt).strip()

        if not value and default is not None:
            return default
        if value:
            return value
        if not value and not default:
            console.print("Please enter a value.", style="bold red")
