"""Installer entry point."""

import asyncio
import sys

import click

from installer.cli.app import run_installer


def main():
    """Main entry point."""
    try:
        asyncio.run(run_installer())
    except (KeyboardInterrupt, click.exceptions.Abort):
        # Exit cleanly without showing traceback
        sys.exit(0)
    except Exception as e:
        # Show clean error message instead of full traceback
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
