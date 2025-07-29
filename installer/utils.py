"""Installer utility functions."""

from __future__ import annotations

import platform
import re
import shutil
import subprocess  # noqa: S404
import sys
import zipfile
from pathlib import Path

import requests

# Import Console from ui module to avoid circular imports
# The ui module now provides the Console class using clicycle


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
            subprocess.run(
                ["which", command],
                capture_output=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def get_command_path(self, command: str) -> str | None:
        """Get the full path to a command."""
        try:
            result = subprocess.run(
                ["which", command],
                capture_output=True,
                check=True,
                text=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None


class FileDownloader:
    """Handles file downloads with progress display."""

    def __init__(self, console):
        self.console = console

    def download_file(self, url: str, output_path: Path) -> None:
        """Download a file from a URL to a local path."""
        try:
            self.console.info(f"Downloading from {url}...")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Get the total file size
            total_size = int(response.headers.get("content-length", 0))
            block_size = 8192
            downloaded = 0

            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Download and write the file
            with output_path.open("wb") as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            self.console.info(f"Progress: {progress:.1f}%")

            self.console.success(f"Downloaded to {output_path}")

        except requests.RequestException as e:
            self.console.error(f"Download failed: {e}")
            raise


class DirectoryUtils:
    """Utilities for directory operations."""

    @staticmethod
    def ensure_directory(path: Path) -> None:
        """Ensure a directory exists."""
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def clean_directory(path: Path) -> None:
        """Remove all contents of a directory."""
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def copy_tree(src: Path, dst: Path) -> None:
        """Copy a directory tree."""
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)


def extract_zip(zip_path: Path, extract_to: Path) -> None:
    """Extract a zip file."""
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)


def run_command(command: list[str], cwd: Path | None = None) -> str:
    """Run a command and return its output."""
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=cwd,
        check=True,
    )
    return result.stdout.strip()


def is_valid_email(email: str) -> bool:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def is_valid_url(url: str) -> bool:
    """Validate URL format."""
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, url))
