"""Event Importer - Main entry point."""

import asyncio
import logging
import sys
from multiprocessing import freeze_support

from app.first_run import (
    should_run_installer,  # noqa: PLC0415 # First run detection for packaged app
)
from app.interfaces.cli.commands import cli
from app.startup import startup_checks

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    freeze_support()  # For Windows support

    # Check if this is first run
    # Installer needs to run in packaged app context
    if should_run_installer():
        from installer.cli.app import run_installer  # noqa: PLC0415

        asyncio.run(run_installer())

    # Run startup checks
    try:
        startup_checks()
    except Exception as e:
        logger.error(f"Startup checks failed: {e}")
        sys.exit(1)

    # Run the CLI
    cli()


if __name__ == "__main__":
    main()
