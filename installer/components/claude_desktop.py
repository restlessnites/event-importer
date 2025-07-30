"""Claude Desktop configuration component."""

import json
import os
import platform
import shutil
from pathlib import Path

from config.paths import get_install_dir
from installer.utils.system import SystemCheck


class ClaudeDesktopConfig:
    """Handles Claude Desktop integration."""

    def __init__(self, is_packaged: bool = False):
        self.system_check = SystemCheck()
        self.is_packaged = is_packaged

    def is_claude_desktop_installed(self) -> bool:
        """Check if Claude Desktop is installed."""
        system = platform.system()

        if system == "Darwin":  # macOS
            app_paths = [
                "/Applications/Claude Desktop.app",
                "/Applications/Claude.app",
                Path.home() / "Applications" / "Claude Desktop.app",
                Path.home() / "Applications" / "Claude.app",
            ]
        elif system == "Windows":
            program_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
            program_files_x86 = os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")
            localappdata = os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")

            app_paths = [
                Path(program_files) / "Claude Desktop" / "Claude Desktop.exe",
                Path(program_files) / "Claude" / "Claude.exe",
                Path(program_files_x86) / "Claude Desktop" / "Claude Desktop.exe",
                Path(program_files_x86) / "Claude" / "Claude.exe",
                Path(localappdata) / "Claude Desktop" / "Claude Desktop.exe",
                Path(localappdata) / "Claude" / "Claude.exe",
            ]
        else:  # Linux
            app_paths = [
                Path.home() / ".local" / "bin" / "claude-desktop",
                Path("/usr/bin/claude-desktop"),
                Path("/usr/local/bin/claude-desktop"),
                Path("/opt/claude-desktop/claude-desktop"),
            ]

        return any(Path(p).exists() for p in app_paths)

    def is_configured(self) -> bool:
        """Check if Event Importer is already configured in Claude Desktop."""
        config_path = self._get_claude_config_path()
        if not config_path or not config_path.exists():
            return False

        config = self._load_config(config_path)
        return "event-importer" in config.get("mcpServers", {})

    def configure_for_packaged(self) -> bool:
        """Configure Claude Desktop for packaged app."""
        config_path = self._get_claude_config_path()
        if not config_path:
            return False

        # Get the appropriate install path for the platform
        install_dir = get_install_dir()
        if platform.system() == "Windows":
            app_path = install_dir / "event-importer.exe"
        else:
            app_path = install_dir / "event-importer"

        mcp_config = {
            "command": str(app_path),
            "args": ["mcp"],
            "env": {},
        }

        return self._apply_config(config_path, mcp_config)

    def configure_for_development(self, enable_all_features: bool = True) -> bool:
        """Configure Claude Desktop for development."""
        config_path = self._get_claude_config_path()
        if not config_path:
            return False

        # Get uv path
        uv_path = self.system_check.get_command_path("uv")
        if not uv_path:
            return False

        # Get project root
        project_root = Path.cwd()

        mcp_config = {
            "command": uv_path,
            "args": ["--directory", str(project_root), "run", "event-importer", "mcp"],
            "env": {"PYTHONPATH": str(project_root)},
        }

        if enable_all_features:
            mcp_config["env"]["TICKETFAIRY_ENABLED"] = "true"

        return self._apply_config(config_path, mcp_config)

    def _get_claude_config_path(self) -> Path | None:
        """Get the path to the Claude Desktop config file."""
        system = platform.system()

        if system == "Darwin":  # macOS
            config_paths = [
                Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
                Path.home() / ".claude" / "claude_desktop_config.json",
            ]
            default = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        elif system == "Windows":
            appdata = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
            config_paths = [
                Path(appdata) / "Claude" / "claude_desktop_config.json",
                Path.home() / ".claude" / "claude_desktop_config.json",
            ]
            default = Path(appdata) / "Claude" / "claude_desktop_config.json"
        else:  # Linux
            config_paths = [
                Path.home() / ".config" / "claude" / "claude_desktop_config.json",
                Path.home() / ".claude" / "claude_desktop_config.json",
            ]
            default = Path.home() / ".config" / "claude" / "claude_desktop_config.json"

        # Check existing configs
        for path in config_paths:
            if path.exists():
                return path

        # Return the most likely default path
        return default

    def _load_config(self, config_path: Path) -> dict:
        """Load existing config or return empty dict."""
        if not config_path.exists():
            return {}

        try:
            with config_path.open() as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_config(self, config_path: Path, config: dict) -> bool:
        """Save config to file."""
        try:
            # Ensure parent directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write config
            with config_path.open("w") as f:
                json.dump(config, f, indent=2)
            return True
        except Exception:
            return False

    def _backup_config(self, config_path: Path) -> Path | None:
        """Create a backup of existing config."""
        if not config_path.exists():
            return None

        backup_path = config_path.with_suffix(".json.backup")
        try:
            shutil.copy2(config_path, backup_path)
            return backup_path
        except Exception:
            return None

    def _apply_config(self, config_path: Path, mcp_config: dict) -> bool:
        """Apply MCP configuration to Claude Desktop."""
        # Backup existing config
        self._backup_config(config_path)

        # Load or create config
        config = self._load_config(config_path)
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Add or update event-importer config
        config["mcpServers"]["event-importer"] = mcp_config

        # Save config
        return self._save_config(config_path, config)
