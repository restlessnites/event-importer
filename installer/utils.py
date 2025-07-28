"""Installer utility functions."""

from __future__ import annotations

import platform
import shutil
import subprocess  # noqa S404
import sys
import zipfile
from pathlib import Path

import requests
from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.prompt import Confirm, Prompt


class Console:
    """A styled console wrapper for consistent output."""

    def __init__(self):
        self._rich_console = RichConsole()
        self._error_console = RichConsole(stderr=True)

    def header(self, text: str):
        """Prints a stylized header."""
        self._rich_console.print()
        self._rich_console.print(Panel(text, style="bold blue", expand=False))
        self._rich_console.print()

    def step(self, text: str):
        """Prints a step message."""
        self._rich_console.print(f"\n[bold cyan]→ {text}[/bold cyan]")

    def success(self, text: str):
        """Prints a success message."""
        self._rich_console.print(f"[green]✓ {text}[/green]")

    def error(self, text: str):
        """Prints an error message."""
        self._error_console.print(f"[bold red]✗ {text}[/bold red]")

    def warning(self, text: str):
        """Prints a warning message."""
        self._rich_console.print(f"[yellow]⚠ {text}[/yellow]")

    def info(self, text: str):
        """Prints an informational message."""
        self._rich_console.print(text)

    def confirm(self, prompt: str, default: bool = False) -> bool:
        """Asks for user confirmation."""
        return Confirm.ask(prompt, console=self._rich_console, default=default)

    def prompt(
        self, prompt: str, default: str | None = None, secret: bool = False
    ) -> str:
        """Gets user input."""
        return Prompt.ask(
            prompt,
            console=self._rich_console,
            default=default,
            password=secret,
        )

    def print(self, *args, **kwargs):
        """Prints to the console using rich."""
        self._rich_console.print(*args, **kwargs)

    @property
    def rich_console(self) -> RichConsole:
        """Returns the underlying rich console instance."""
        return self._rich_console


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


class Downloader:
    """Handles file downloads with progress."""

    def __init__(self, console: Console):
        """Initialize the downloader."""
        self.console = console

    def get_latest_version(self, version_url: str) -> str | None:
        """Get the latest version from a URL."""
        try:
            response = requests.get(version_url, timeout=10)
            response.raise_for_status()
            return response.text.strip()
        except requests.RequestException as e:
            self.console.error(f"Failed to check for new version: {e}")
            return None

    def get_json(self, url: str) -> dict | None:
        """Fetch and parse JSON from a URL."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.console.error(f"Failed to fetch JSON from {url}: {e}")
            return None
        except ValueError:
            self.console.error(f"Invalid JSON response from {url}")
            return None

    def download_file(self, url: str, dest: Path) -> bool:
        """Download a file with a progress bar."""
        self.console.info(f"Downloading {url}...")
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))

            with dest.open("wb") as f, self.console.rich_console.progress() as progress:
                task = progress.add_task("Downloading...", total=total_size)
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    progress.update(task, advance=len(chunk))
            self.console.success(f"Downloaded successfully to {dest}")
            return True
        except requests.RequestException as e:
            self.console.error(f"Download failed: {e}")
            return False


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

    def unzip_file(self, zip_path: Path, extract_to: Path) -> bool:
        """Unzip a file."""
        self.console.info(f"Unzipping {zip_path}...")
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_to)
            self.console.success(f"Unzipped successfully to {extract_to}")
            return True
        except zipfile.BadZipFile:
            self.console.error("Invalid zip file.")
            return False
        except Exception as e:
            self.console.error(f"Unzip failed: {e}")
            return False

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
                console = Console()
                console.error(f"Failed to create backup for {file_path}: {e}")
        return None
