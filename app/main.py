"""Event Importer - Main entry point."""

import logging
import sys
from multiprocessing import freeze_support

from app.core.startup import startup_checks
from app.interfaces.cli.commands import cli

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    freeze_support()  # For Windows support

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
