"""Claude Desktop configuration component."""

import json
from pathlib import Path

from installer.utils import (
    Console,
    FileUtils,
    SystemCheck,
)


class ClaudeDesktopConfig:
    """Manages Claude Desktop configuration."""

    def __init__(self, console: Console):
        self.console = console
        self.file_utils = FileUtils()
        self.system_check = SystemCheck()

    def is_claude_desktop_installed(self) -> bool:
        """Check if Claude Desktop is installed."""
        # Check common installation paths
        app_paths = [
            "/Applications/Claude Desktop.app",
            "/Applications/Claude.app",
            Path.home() / "Applications" / "Claude Desktop.app",
            Path.home() / "Applications" / "Claude.app",
        ]

        return any(Path(p).exists() for p in app_paths)

    def get_config_path(self) -> Path | None:
        """Get the Claude Desktop configuration file path."""
        # Common config locations
        config_paths = [
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json",
            Path.home() / ".claude" / "claude_desktop_config.json",
            Path.home() / ".config" / "claude" / "claude_desktop_config.json",
        ]

        # Check existing configs
        for path in config_paths:
            if path.exists():
                return path

        # Return the most likely default path
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )

    def configure(self, project_root: Path) -> bool:
        """Configure Claude Desktop to use the Event Importer MCP server."""
        config_path = self.get_config_path()
        if not config_path:
            self.console.error("Could not determine Claude Desktop config location")
            return False

        # Get uv path
        uv_path = self.system_check.get_command_path("uv")
        if not uv_path:
            self.console.error("uv not found in PATH")
            return False

        # Prepare the MCP server configuration
        mcp_config = {
            "command": uv_path,
            "args": ["--directory", str(project_root), "run", "event-importer-mcp"],
            "cwd": str(project_root),
        }

        # Load or create config
        config = self._load_config(config_path)

        # Backup existing config if it exists
        backup_path = None
        if config_path.exists():
            backup_path = self.file_utils.backup_file(config_path)

        # Add our MCP server
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"]["event-importer"] = mcp_config

        # Save config
        if self._save_config(config_path, config):
            self.console.success("Claude Desktop configuration updated")
            if backup_path:
                self.console.info(
                    f"  Existing configuration backed up to: {backup_path}"
                )
            return True
        self.console.error("Failed to save Claude Desktop configuration")
        return False

    def _load_config(self, config_path: Path) -> dict:
        """Load existing config or return empty dict."""
        if not config_path.exists():
            return {}

        try:
            with config_path.open() as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_config(self, config_path: Path, config: dict) -> bool:
        """Save config to file."""
        try:
            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write config with nice formatting
            with config_path.open("w") as f:
                json.dump(config, f, indent=2)

            return True
        except Exception as e:
            self.console.error(f"Error saving config: {e}")
            return False

    def is_already_configured(self, project_root: Path) -> bool:
        """Check if Event Importer is already configured in Claude Desktop."""
        config_path = self.get_config_path()
        if not config_path or not config_path.exists():
            return False

        try:
            config = self._load_config(config_path)
            if "mcpServers" not in config:
                return False

            if "event-importer" not in config["mcpServers"]:
                return False

            server_config = config["mcpServers"]["event-importer"]

            # Verify the configuration points to the right place
            if "args" in server_config:
                args = server_config["args"]
                if "--directory" in args:
                    idx = args.index("--directory")
                    if idx + 1 < len(args):
                        configured_path = Path(args[idx + 1])
                        return configured_path == project_root
            return False
        except Exception:
            return False

    def verify_configuration(self, project_root: Path) -> bool:
        """Verify that Claude Desktop is properly configured."""
        config_path = self.get_config_path()
        if not config_path or not config_path.exists():
            return False

        try:
            config = self._load_config(config_path)
            if "mcpServers" not in config:
                return False

            if "event-importer" not in config["mcpServers"]:
                return False

            server_config = config["mcpServers"]["event-importer"]

            # Verify the configuration points to the right place
            if "args" in server_config:
                args = server_config["args"]
                if "--directory" in args:
                    idx = args.index("--directory")
                    if idx + 1 < len(args):
                        configured_path = Path(args[idx + 1])
                        return configured_path == project_root

            return True
        except Exception:
            return False
