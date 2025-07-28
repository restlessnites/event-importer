"""
Event Importer Installation Bootstrapper.

This script's only job is to ensure that the installer's own dependencies
are present. It then hands off to the main installer module.
This separation avoids import errors on a clean machine.
"""

import subprocess  # noqa: S404
import sys

# A list of dependencies that the installer itself needs to run.
# These are not the application's dependencies.
INSTALLER_DEPS = ["rich", "python-dotenv"]


def check_and_install_dependencies():
    """
    Check if the installer's dependencies (e.g., 'rich') are installed.
    If not, attempt to install them using pip.
    """
    try:
        for dependency in INSTALLER_DEPS:
            __import__(dependency)
        return True
    except ImportError:
        print("Installer dependencies not found. Attempting to install...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", *INSTALLER_DEPS]
            )
            print("Installer dependencies installed successfully.")
            return True
        except subprocess.CalledProcessError:
            print(
                "Error: Could not install installer dependencies.",
                "Please ensure you have pip installed and an internet connection.",
                file=sys.stderr,
            )
            return False


def run_main_installer():
    """
    Run the main installer as a separate process.
    This ensures that it runs after dependencies are available.
    """
    print("\nStarting the Event Importer installer...")
    result = subprocess.run([sys.executable, "-m", "installer"], check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    if check_and_install_dependencies():
        run_main_installer()
    else:
        sys.exit(1)
