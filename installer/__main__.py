"""Installer entry point."""

import asyncio

from installer.cli.app import run_installer


def main():
    """Main entry point."""
    asyncio.run(run_installer())


if __name__ == "__main__":
    main()
