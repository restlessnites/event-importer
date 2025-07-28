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
        results = {"success": True, "errors": [], "warnings": [], "checks": {}}

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
            results["checks"]["uv installed"] = uv_installed
            if not uv_installed:
                results["errors"].append("uv is not installed or not in PATH")

            # Check Python version
            result = subprocess.run(  # noqa: S603,S607 - python version check is safe
                ["python", "--version"],  # noqa: S607
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                results["checks"]["python version"] = result.stdout.strip()
            else:
                results["errors"].append("Python is not accessible")
        except Exception as e:
            results["errors"].append(f"Failed to check dependencies: {e}")

    def _check_environment(self, project_root: Path, results: dict):
        """Check environment setup."""
        # Check .env file
        env_file = project_root / ".env"
        results["checks"][".env file exists"] = env_file.exists()
        if not env_file.exists():
            results["errors"].append(".env file not found")

        # Check virtual environment
        venv_path = project_root / ".venv"
        results["checks"]["virtual environment"] = venv_path.exists()
        if not venv_path.exists():
            results["warnings"].append(
                "Virtual environment not found - uv sync may not have completed"
            )

        # Check required directories
        for dir_name in ["app", "data", "scripts"]:
            dir_path = project_root / dir_name
            results["checks"][f"{dir_name} directory"] = dir_path.exists()
            if not dir_path.exists():
                results["errors"].append(f"Required directory '{dir_name}' not found")

    def _check_api_keys(self, project_root: Path, results: dict):
        """Check API key configuration."""
        api_key_manager = APIKeyManager()
        valid, missing = api_key_manager.validate_keys(project_root)

        results["checks"]["required API keys"] = valid
        if not valid:
            for key in missing:
                results["errors"].append(f"Required API key not configured: {key}")

        # Check optional keys as well
        env_setup = EnvironmentSetup()
        env_vars = env_setup.get_env_vars(project_root)
        optional_keys = [
            ("OPENAI_API_KEY", "OpenAI API key"),
            ("TICKETMASTER_API_KEY", "Ticketmaster API key"),
            ("GOOGLE_API_KEY", "Google API key"),
            ("GOOGLE_CSE_ID", "Google CSE ID"),
        ]

        for key, desc in optional_keys:
            if key in env_vars and env_vars[key]:
                results["checks"][f"{desc} (optional)"] = True

    def _check_import_functionality(self, project_root: Path, results: dict):
        """Test basic import functionality."""
        try:
            # Test if we can run the CLI help
            result = self.runner.run(
                ["uv", "run", "event-importer", "--help"],
                cwd=str(project_root),
                capture_output=True,
            )

            results["checks"]["CLI accessible"] = result.returncode == 0
            if result.returncode != 0:
                results["errors"].append("CLI tool not accessible")
                if result.stderr:
                    results["errors"].append(f"CLI error: {result.stderr}")
        except Exception as e:
            results["errors"].append(f"Failed to test CLI: {e}")

    def _check_claude_desktop(self, project_root: Path, results: dict):
        """Check Claude Desktop configuration."""
        claude_config = ClaudeDesktopConfig()

        # Check if Claude Desktop is installed
        if claude_config.is_claude_desktop_installed():
            # Check if configured for this project
            is_configured = claude_config.is_already_configured(project_root)
            results["checks"]["Claude Desktop configured"] = is_configured
            if not is_configured:
                results["warnings"].append(
                    "Claude Desktop is installed but not configured for this project"
                )
        else:
            results["checks"]["Claude Desktop installed"] = False
            results["warnings"].append(
                "Claude Desktop not found - MCP integration unavailable"
            )

    def print_report(self, results: dict):
        """Print a formatted validation report."""
        self.console.print_header("Installation Validation Report")

        # Print checks
        print("\nValidation Checks:")
        print("-" * 50)
        for check, result in results["checks"].items():
            if isinstance(result, bool):
                status = "✓" if result else "✗"
                color = self.console.GREEN if result else self.console.RED
            else:
                status = "ℹ"
                color = self.console.CYAN
                result = f" ({result})"
            print(
                f"{color}{status}{self.console.RESET} {check}{result if not isinstance(result, bool) else ''}"
            )

        # Print errors
        if results["errors"]:
            print(f"\n{self.console.RED}Errors:{self.console.RESET}")
            for error in results["errors"]:
                print(f"  • {error}")

        # Print warnings
        if results["warnings"]:
            print(f"\n{self.console.YELLOW}Warnings:{self.console.RESET}")
            for warning in results["warnings"]:
                print(f"  • {warning}")

        # Overall status
        print("\n" + "-" * 50)
        if results["success"]:
            self.console.print_success("✅ Installation validation PASSED")
        else:
            self.console.print_error("❌ Installation validation FAILED")
