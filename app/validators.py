"""Application validation component."""

import asyncio
import logging
import subprocess  # noqa S404
from pathlib import Path

from app.config import get_config
from app.integrations.ticketfairy.config import get_ticketfairy_config
from app.shared.database.connection import init_db
from app.shared.http import close_http_service

logger = logging.getLogger(__name__)


class InstallationValidator:
    """Validate the Event Importer installation."""

    def validate(self, project_root: Path) -> dict[str, any]:
        """Run comprehensive validation checks."""
        results = {
            "success": True,
            "errors": [],
            "warnings": [],
            "checks": {
                "System": {},
                "Environment": {},
                "API Keys": {},
                "Core Components": {},
            },
        }

        # Run checks and populate sections
        self._check_system(results["checks"]["System"])
        self._check_environment(project_root, results)
        self._check_api_keys(results)
        self._check_core_components(project_root, results)

        # Determine overall success
        results["success"] = len(results["errors"]) == 0
        return results

    def _check_system(self, checks: dict):
        """Check system-level dependencies like Python and uv."""
        try:
            # Check uv
            result = subprocess.run(
                ["uv", "--version"], capture_output=True, check=False, text=True
            )
            checks["uv package manager"] = result.returncode == 0
        except Exception:
            checks["uv package manager"] = False

        # Check Python version
        try:
            result = subprocess.run(
                ["python", "--version"], capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                checks["Python interpreter"] = result.stdout.strip()
            else:
                checks["Python interpreter"] = False
        except Exception:
            checks["Python interpreter"] = False

    def _check_environment(self, project_root: Path, results: dict):
        """Check project environment setup."""
        checks = results["checks"]["Environment"]
        # Check .env file
        env_file = project_root / ".env"
        checks[".env file"] = env_file.exists()
        if not env_file.exists():
            results["errors"].append(".env file not found")

        # Check virtual environment
        venv_path = project_root / ".venv"
        checks["Virtual environment (.venv)"] = venv_path.exists()
        if not venv_path.exists():
            results["warnings"].append(
                "Virtual environment not found. Run `make setup`."
            )

        # Check required directories
        for dir_name in ["app", "data", "scripts"]:
            dir_path = project_root / dir_name
            checks[f"`{dir_name}` directory"] = dir_path.exists()
            if not dir_path.exists():
                results["errors"].append(f"Required directory '{dir_name}' not found")

    def _check_api_keys(self, results: dict):
        """Check API key configuration with detailed reporting."""
        checks = results["checks"]["API Keys"]
        config = get_config()
        tf_config = get_ticketfairy_config()

        key_definitions = {
            "ANTHROPIC_API_KEY": (config.api, "anthropic_key", True),
            "ZYTE_API_KEY": (config.api, "zyte_key", True),
            "TICKETFAIRY_API_KEY": (tf_config, "api_key", True),
            "OPENAI_API_KEY": (config.api, "openai_key", False),
            "GOOGLE_API_KEY": (config.api, "google_api_key", False),
        }

        for key, (cfg_obj, attr, is_required) in key_definitions.items():
            tag = "(required)" if is_required else "(optional)"
            check_name = f"{key} {tag}"
            is_present = bool(hasattr(cfg_obj, attr) and getattr(cfg_obj, attr))
            checks[check_name] = is_present
            if is_required and not is_present:
                results["errors"].append(f"Required API key not configured: {key}")

    def _check_core_components(self, project_root: Path, results: dict):
        """Check core application components like the CLI and database."""
        checks = results["checks"]["Core Components"]
        # Test CLI
        try:
            result = subprocess.run(
                ["uv", "run", "event-importer", "--help"],
                cwd=str(project_root),
                capture_output=True,
                check=False,
                text=True,
            )
            checks["CLI accessibility"] = result.returncode == 0
            if result.returncode != 0:
                results["errors"].append(
                    f"CLI tool is not accessible: {result.stderr.strip()}"
                )
        except Exception as e:
            checks["CLI accessibility"] = False
            results["errors"].append(f"Failed to test CLI: {e}")

        # Test Database
        try:
            init_db()
            asyncio.run(close_http_service())
            checks["Database connection"] = True
        except Exception as e:
            checks["Database connection"] = False
            results["errors"].append(f"Database connection failed: {e}")
