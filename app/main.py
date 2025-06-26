"""Main application entry point and factory with database initialization."""

import argparse
import logging

from app import __version__
from app.error_messages import CommonMessages
from app.startup import startup_checks


def configure_logging(verbose: bool = False) -> None:
    """Configure logging with appropriate levels."""
    if verbose:
        level = logging.INFO
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    else:
        level = logging.WARNING
        format_str = "%(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(level=level, format=format_str, force=True)


def main() -> int:
    """Main entry point that routes to appropriate interface."""
    parser = argparse.ArgumentParser(
        prog="event-importer",
        description="Event Importer - Extract structured event data from websites",
    )
    parser.add_argument(
        "--version", action="version", version=f"event-importer {__version__}"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Import command (replaces old "cli" interface)
    import_parser = subparsers.add_parser("import", help="Import an event from URL")
    import_parser.add_argument("url", help="URL to import")
    import_parser.add_argument(
        "--method", choices=["api", "web", "image"], help="Force import method"
    )
    import_parser.add_argument(
        "--timeout", type=int, default=60, help="Timeout in seconds"
    )
    import_parser.add_argument(
        "--ignore-cache", action="store_true", help="Skip cache and force fresh import"
    )
    # Add verbose flag to import subparser as well for flexibility
    import_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List imported events")
    list_parser.add_argument("--limit", "-l", type=int, help="Limit number of results")
    list_parser.add_argument("--search", "-s", help="Search in URL or event data")
    list_parser.add_argument(
        "--details", "-d", action="store_true", help="Show detailed view"
    )
    list_parser.add_argument(
        "--sort", choices=["date", "url"], default="date", help="Sort by field"
    )
    list_parser.add_argument(
        "--order", choices=["asc", "desc"], default="desc", help="Sort order"
    )

    # Show command
    show_parser = subparsers.add_parser("show", help="Show specific event details")
    show_parser.add_argument("event_id", type=int, help="Event ID to show")

    # Stats command
    subparsers.add_parser("stats", help="Show database statistics")

    # MCP interface
    subparsers.add_parser("mcp", help="Run MCP server")

    # API interface
    api_parser = subparsers.add_parser("api", help="Run HTTP API server")
    api_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    api_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    api_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    # Check for verbose flag from either global or subcommand
    verbose = getattr(args, "verbose", False)

    # Configure logging based on verbosity
    configure_logging(verbose=verbose)
    logger = logging.getLogger(__name__)



    if not args.command:
        # Default behavior - show help
        parser.print_help()
        return 0

    # Run startup checks and database initialization for all commands
    try:
        startup_checks()
    except (ValueError, TypeError, KeyError):
        logger.exception(CommonMessages.STARTUP_FAILED)
        return 1

    # Route to appropriate interface
    try:
        if args.command == "import":
            from app.interfaces.cli import run_cli

            run_cli(args)
        elif args.command in ["list", "show", "stats"]:
            from app.interfaces.cli.events import run_events_cli

            run_events_cli(args)
        elif args.command == "mcp":
            from app.interfaces.mcp.server import run as mcp_run

            mcp_run()
        elif args.command == "api":
            from app.interfaces.api.server import run as api_run

            api_run(host=args.host, port=args.port, reload=args.reload)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 0
    except (ValueError, TypeError, KeyError):
        logger.exception(CommonMessages.OPERATION_FAILED)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
