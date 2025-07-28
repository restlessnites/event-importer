#!/usr/bin/env python3
"""Event Importer Installation Script."""

import subprocess
import sys

# List of dependencies required by the installer itself
INSTALLER_DEPS = ["rich"]


def check_and_install_deps():
    """Check for installer dependencies and install them if missing."""
    try:
        # Check if all dependencies can be imported
        for dep in INSTALLER_DEPS:
            __import__(dep)
    except ImportError:
        print("Installer dependencies not found. Installing them now...")
        try:
            # Use pip to install the missing dependencies
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", *INSTALLER_DEPS]
            )
            print("Dependencies installed successfully.")
        except subprocess.CalledProcessError:
            print(
                "Error: Could not install installer dependencies. "
                "Please ensure you have pip installed and an internet connection."
            )
            sys.exit(1)


def run_installer():
    """Run the main installer logic after ensuring deps are present."""
    from installer.core import main

    main()


if __name__ == "__main__":
    check_and_install_deps()
    run_installer()
