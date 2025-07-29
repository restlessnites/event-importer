"""Installation validation component."""

import subprocess  # noqa S404
from pathlib import Path

from installer.components.api_keys import APIKeyManager
from installer.components.claude_desktop import ClaudeDesktopConfig
from installer.components.environment import EnvironmentSetup
from installer.utils import ProcessRunner, Console


class InstallationValidator:
    """Validate the Event Importer installation."""

    def __init__(self):
        self.console = Console()
        self.runner = ProcessRunner()

    def validate(self, project_root: Path) -> dict[str, any]:
        """Run comprehensive validation checks."""
        results = {
            "success": True,
            "errors": [],
            "warnings": [],
            "checks": {
                "Dependencies": {},
                "Environment": {},
                "API Keys": {},
                "CLI": {},
                "Integration": {},
            }
        }

        # Check 1: Dependencies installed
        self._check_dependencies(results)

        # Check 2: Environment setup
        self._check_environment(project_root, results)

        # Check 3: API keys configured
        self._check_api_keys(project_root, results)

        # Check 4: Test import functionality
        self._check_import_functionality(project_root, results)

        # Check 5: Claude Desktop configuration
        self._check_claude_desktop(project_root, results)

        # Determine overall success
        results["success"] = len(results["errors"]) == 0

        return results

    def _check_dependencies(self, results: dict):
        """Check if all dependencies are properly installed."""
        try:
            # Check uv
            result = self.runner.run(
                ["uv", "--version"], capture_output=True, check=False
            )
            uv_installed = result.returncode == 0
            results["checks"]["Dependencies"]["uv installed"] = uv_installed
            if not uv_installed:
                results["errors"].append("uv is not installed or not in PATH")

            # Check Python version
            result = subprocess.run(  # noqa: S603,S607 - python version check is safe
                ["python", "--version"],  # noqa: S607
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                results["checks"]["Dependencies"]["python version"] = result.stdout.strip()
            else:
                results["errors"].append("Python is not accessible")
        except Exception as e:
            results["errors"].append(f"Failed to check dependencies: {e}")

    def _check_environment(self, project_root: Path, results: dict):
        """Check environment setup."""
        # Check .env file
        env_file = project_root / ".env"
        results["checks"]["Environment"][".env file exists"] = env_file.exists()
        if not env_file.exists():
            results["errors"].append(".env file not found")

        # Check virtual environment
        venv_path = project_root / ".venv"
        results["checks"]["Environment"]["virtual environment"] = venv_path.exists()
        if not venv_path.exists():
            results["warnings"].append(
                "Virtual environment not found - uv sync may not have completed"
            )

        # Check required directories
        for dir_name in ["app", "data", "scripts"]:
            dir_path = project_root / dir_name
            results["checks"]["Environment"][f"{dir_name} directory"] = dir_path.exists()
            if not dir_path.exists():
                results["errors"].append(f"Required directory '{dir_name}' not found")

    def _check_api_keys(self, project_root: Path, results: dict):
        """Check API key configuration."""
        from installer.components.api_keys import ALL_KEYS
        
        api_key_manager = APIKeyManager(self.console, project_root)
        valid = api_key_manager.are_required_keys_present(project_root)

        results["checks"]["API Keys"]["required API keys"] = valid
        if not valid:
            env_setup = EnvironmentSetup(self.console, project_root)
            env_vars = env_setup.get_env_vars(project_root)
            for key, details in ALL_KEYS.items():
                if details["required"] and not env_vars.get(key):
                    results["errors"].append(f"Required API key not configured: {key}")

        # Check optional keys as well
        env_setup = EnvironmentSetup(self.console, project_root)
        env_vars = env_setup.get_env_vars(project_root)
        optional_keys = [
            ("OPENAI_API_KEY", "OpenAI API key"),
            ("TICKETMASTER_API_KEY", "Ticketmaster API key"),
            ("GOOGLE_API_KEY", "Google API key"),
            ("GOOGLE_CSE_ID", "Google CSE ID"),
        ]

        for key, desc in optional_keys:
            if key in env_vars and env_vars[key]:
                results["checks"]["API Keys"][f"{desc} (optional)"] = True

    def _check_import_functionality(self, project_root: Path, results: dict):
        """Test basic import functionality."""
        try:
            # Test if we can run the CLI help
            result = self.runner.run(
                ["uv", "run", "event-importer", "--help"],
                cwd=str(project_root),
                capture_output=True,
            )

            results["checks"]["CLI"]["CLI accessible"] = result.returncode == 0
            if result.returncode != 0:
                results["errors"].append("CLI tool not accessible")
                if result.stderr:
                    results["errors"].append(f"CLI error: {result.stderr}")
        except Exception as e:
            results["errors"].append(f"Failed to test CLI: {e}")

    def _check_claude_desktop(self, project_root: Path, results: dict):
        """Check Claude Desktop configuration."""
        claude_config = ClaudeDesktopConfig(self.console)

        # Check if Claude Desktop is installed
        is_installed = claude_config.is_claude_desktop_installed()
        results["checks"]["Integration"]["Claude Desktop installed"] = is_installed
        
        if not is_installed:
            results["warnings"].append(
                "Claude Desktop not found - MCP integration unavailable"
            )

    def print_report(self, results: dict):
        """Print a formatted validation report."""
        self.console.header("Installation Validation Report")

        # Print checks
        self.console.info("\nValidation Checks:")
        self.console.info("-" * 50)
        for category, checks in results["checks"].items():
            if checks:
                self.console.info(f"\n{category}:")
                for check, result in checks.items():
                    if isinstance(result, bool):
                        status = "✓" if result else "✗"
                        if result:
                            self.console.success(f"  {check}")
                        else:
                            self.console.error(f"  {check}")
                    else:
                        self.console.info(f"  ℹ {check} ({result})")

        # Print errors
        if results["errors"]:
            self.console.error("\nErrors:")
            for error in results["errors"]:
                self.console.error(f"  • {error}")

        # Print warnings
        if results["warnings"]:
            self.console.warning("\nWarnings:")
            for warning in results["warnings"]:
                self.console.warning(f"  • {warning}")

        # Overall status
        self.console.info("\n" + "-" * 50)
        if results["success"]:
            self.console.success("✅ Installation validation PASSED")
        else:
            self.console.error("❌ Installation validation FAILED")
