"""Core installer functionality."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import app
from app.shared.project import get_project
from app.validators import InstallationValidator
from installer.components.api_keys import APIKeyManager
from installer.components.claude_desktop import ClaudeDesktopConfig
from installer.components.migration import MigrationManager
from installer.components.updater import UpdateManager
from installer.paths import get_user_data_dir
from installer.utils import SystemCheck


@dataclass
class InstallationStatus:
    """Status of the installation."""

    is_upgrade: bool = False
    current_version: str | None = None
    new_version: str = ""
    needs_migration: bool = False
    is_packaged: bool = False


@dataclass
class InstallationResult:
    """Result of an installation step."""

    success: bool
    message: str
    details: dict | None = None


class EventImporterInstaller:
    """Main installer orchestrator - handles business logic only."""

    def __init__(self):
        self.is_packaged = self._is_packaged()
        self.project_root = self._get_project_root()
        project = get_project()
        self.version_file = self.project_root / ".version"
        self.new_version = project.version
        self.system_check = SystemCheck()
        self.claude_config = ClaudeDesktopConfig(self.is_packaged)
        self.api_key_manager = APIKeyManager()
        self.validator = InstallationValidator()
        self.migration_manager = MigrationManager()
        self.update_manager = UpdateManager(self.project_root)

    def _is_packaged(self) -> bool:
        """Check if the application is running as a packaged executable."""
        return getattr(sys, "frozen", False)

    def _get_project_root(self) -> Path:
        """Get the project root, handling both normal and packaged execution."""
        if getattr(sys, "frozen", False):
            # Running in a PyInstaller bundle, use the app support directory
            return get_user_data_dir()

        # Running in a normal Python environment
        return Path(app.__file__).parent.parent

    def _get_current_version(self) -> str | None:
        """Get the currently installed version, if any."""
        if self.version_file.exists():
            return self.version_file.read_text().strip()
        return None

    def get_status(self) -> InstallationStatus:
        """Get the current installation status."""
        current_version = self._get_current_version()
        return InstallationStatus(
            is_upgrade=bool(current_version),
            current_version=current_version,
            new_version=self.new_version,
            needs_migration=self.migration_manager.has_previous_installation(),
            is_packaged=self.is_packaged,
        )

    def check_system_requirements(self) -> InstallationResult:
        """Check system requirements."""
        # Check OS
        if not self.system_check.is_macos():
            return InstallationResult(
                success=False,
                message="This installer is currently only supported on macOS.",
            )

        # Check Python version
        python_version = self.system_check.get_python_version()
        if python_version < (3, 10):
            return InstallationResult(
                success=False,
                message=f"Python 3.10+ required. Found: {python_version[0]}.{python_version[1]}",
            )

        return InstallationResult(success=True, message="System checks passed")

    def configure_api_keys(self, interactive: bool = True) -> InstallationResult:
        """Configure API keys."""
        # Load existing keys
        self.api_key_manager.load_keys()

        # Get status
        missing_required = self.api_key_manager.get_missing_required_keys()
        missing_optional = self.api_key_manager.get_missing_optional_keys()

        if not missing_required and not missing_optional:
            return InstallationResult(
                success=True,
                message="All API keys configured",
                details={"missing_required": [], "missing_optional": []},
            )

        if not interactive:
            return InstallationResult(
                success=False,
                message="API keys need configuration",
                details={
                    "missing_required": missing_required,
                    "missing_optional": missing_optional,
                },
            )

        # This will be handled by the CLI layer
        return InstallationResult(
            success=False,
            message="API keys need configuration",
            details={
                "missing_required": missing_required,
                "missing_optional": missing_optional,
            },
        )

    def configure_claude_desktop(self) -> InstallationResult:
        """Configure Claude Desktop integration."""
        if not self.claude_config.is_claude_desktop_installed():
            return InstallationResult(
                success=True,
                message="Claude Desktop not found - skipping configuration",
            )

        # Check if already configured
        if self.claude_config.is_configured():
            return InstallationResult(
                success=True, message="Claude Desktop already configured"
            )

        return InstallationResult(
            success=False,
            message="Claude Desktop needs configuration",
            details={"config_needed": True},
        )

    def apply_claude_desktop_config(
        self, enable_all_features: bool = True
    ) -> InstallationResult:
        """Apply Claude Desktop configuration."""
        try:
            if self.is_packaged:
                success = self.claude_config.configure_for_packaged()
            else:
                success = self.claude_config.configure_for_development(
                    enable_all_features
                )

            if success:
                return InstallationResult(
                    success=True, message="Claude Desktop configured successfully"
                )
            return InstallationResult(
                success=False, message="Failed to configure Claude Desktop"
            )
        except Exception as e:
            return InstallationResult(
                success=False, message=f"Error configuring Claude Desktop: {e}"
            )

    def run_migration(self, source_path: Path | None = None) -> InstallationResult:
        """Run data migration."""
        if source_path:
            success = self.migration_manager.migrate_from_path(source_path)
            if success:
                return InstallationResult(
                    success=True, message=f"Data migrated from {source_path}"
                )
            return InstallationResult(
                success=False, message=f"Failed to migrate data from {source_path}"
            )

        # Auto-detect migration
        candidates = self.migration_manager.find_previous_installations()
        if not candidates:
            return InstallationResult(
                success=True, message="No previous installation found"
            )

        return InstallationResult(
            success=False,
            message="Previous installation found",
            details={"candidates": candidates},
        )

    def validate_installation(self) -> InstallationResult:
        """Validate the installation."""
        is_valid, messages = self.validator.validate()

        if is_valid:
            return InstallationResult(
                success=True, message="Installation validated successfully"
            )
        return InstallationResult(
            success=False,
            message="Installation validation failed",
            details={"errors": messages},
        )

    def save_version(self) -> InstallationResult:
        """Save the current version."""
        try:
            self.version_file.write_text(self.new_version)
            return InstallationResult(
                success=True, message=f"Version {self.new_version} saved"
            )
        except Exception as e:
            return InstallationResult(
                success=False, message=f"Failed to save version: {e}"
            )

    def create_data_directory(self) -> InstallationResult:
        """Create the data directory."""
        try:
            data_dir = self.project_root / "data"
            data_dir.mkdir(exist_ok=True)
            return InstallationResult(success=True, message="Data directory created")
        except Exception as e:
            return InstallationResult(
                success=False, message=f"Failed to create data directory: {e}"
            )
