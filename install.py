"""
Event Importer Installation Bootstrapper.

This script ensures that the installer's own dependencies are present,
bootstrapping 'pip' if necessary. It then hands off to the main installer module.
This separation avoids import errors on a clean machine.
"""

import ensurepip
import subprocess  # noqa: S404
import sys

# A list of dependencies that the installer itself needs to run.
INSTALLER_DEPS = [
    "rich",
    "python-dotenv",
    "sqlalchemy",
    "pydantic",
    "pydantic-settings",
    "aiohttp",
    "certifi",
    "tenacity",
]


def ensure_pip_is_available():
    """Check if pip is available, and if not, try to bootstrap it."""
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("`pip` is not available. Attempting to bootstrap it...")
        try:
            ensurepip.bootstrap()
            # Verify that it's now installed
            subprocess.check_call(
                [sys.executable, "-m", "pip", "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("`pip` was successfully bootstrapped.")
            return True
        except Exception as e:
            print(f"Error: Could not bootstrap pip. {e}", file=sys.stderr)
            print(
                "Please ensure you have a full and up-to-date Python installation.",
                file=sys.stderr,
            )
            return False


def check_and_install_dependencies():
    """Check and install the installer's own dependencies."""
    try:
        for dependency in INSTALLER_DEPS:
            __import__(dependency)
        return True
    except ImportError:
        print("Installer dependencies (e.g., rich) not found. Attempting to install...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", *INSTALLER_DEPS]
            )
            print("Installer dependencies installed successfully.")
            return True
        except subprocess.CalledProcessError:
            print("Error: Could not install installer dependencies.", file=sys.stderr)
            return False


def run_main_installer():
    """Run the main installer as a separate process."""
    print("\nStarting the Event Importer installer...")
    result = subprocess.run([sys.executable, "-m", "installer"], check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    if ensure_pip_is_available() and check_and_install_dependencies():
        run_main_installer()
    else:
        print("\nInstallation aborted due to setup errors.", file=sys.stderr)
        sys.exit(1)
