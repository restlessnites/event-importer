"""Environment setup component."""

import logging
import shutil
import subprocess  # noqa S404
from pathlib import Path

from installer.utils import (
    Console,
    FileUtils,
    ProcessRunner,
)

logger = logging.getLogger(__name__)


class EnvironmentSetup:
    """Handle environment configuration."""

    def __init__(self):
        self.console = Console()
        self.runner = ProcessRunner()
        self.file_utils = FileUtils()

    def create_env_file(self, project_root: Path) -> bool:
        """Create .env file from example if it doesn't exist."""
        env_file = project_root / ".env"
        env_example = project_root / "env.example"

        if env_file.exists():
            self.console.print_info(".env file already exists")
            return True

        if not env_example.exists():
            self.console.print_error("env.example file not found")
            return False

        try:
            shutil.copy(env_example, env_file)
            self.console.print_success("✓ Created .env file from template")
            return True
        except Exception as e:
            self.console.print_error(f"Failed to create .env file: {e}")
            return False

    def install_dependencies(self, project_root: Path) -> bool:
        """Install Python dependencies using uv."""
        self.console.print_info("Installing Python dependencies...")

        try:
            # Run uv sync in the project directory
            self.runner.run(["uv", "sync"], cwd=str(project_root), check=True)
            self.console.print_success("✓ Python dependencies installed")
            return True
        except subprocess.CalledProcessError:
            self.console.print_error("Failed to install Python dependencies")
            return False

    def get_env_vars(self, project_root: Path) -> dict[str, str]:
        """Read environment variables from .env file."""
        env_file = project_root / ".env"
        env_vars = {}

        if not env_file.exists():
            return env_vars

        try:
            with env_file.open() as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip().strip("\"'")
        except Exception as e:  # noqa: S110
            # Log but continue - we don't want to fail just because of a malformed line
            logger.debug(f"Skipping malformed line in .env file: {e}")

        return env_vars

    def update_env_var(self, project_root: Path, key: str, value: str) -> bool:
        """Update or add an environment variable."""
        env_file = project_root / ".env"

        if not env_file.exists():
            return False

        try:
            # Read all lines
            with env_file.open() as f:
                lines = f.readlines()

            # Update or add the variable
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    updated = True
                    break

            if not updated:
                # Add new variable
                lines.append(f"\n{key}={value}\n")

            # Write back
            with env_file.open("w") as f:
                f.writelines(lines)

            return True
        except Exception:
            return False

    def validate_environment(self, project_root: Path) -> dict[str, bool]:
        """Validate the environment setup."""
        results = {}

        # Check .env file exists
        results[".env file"] = (project_root / ".env").exists()

        # Check virtual environment
        results["virtual environment"] = (project_root / ".venv").exists()

        # Check key directories
        results["app directory"] = (project_root / "app").exists()
        results["data directory"] = (project_root / "data").exists()

        return results
