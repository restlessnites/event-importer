"""Main application entry point and factory with database initialization."""

import asyncio
import logging.config
from argparse import ArgumentParser, Namespace

from app import __version__
from app.error_messages import CommonMessages
from app.integrations.ticketfairy.cli import main as run_ticketfairy_cli
from app.interfaces.api.server import run as api_run
from app.interfaces.cli.events import run_events_cli
from app.interfaces.cli.runner import run_cli, run_validation_cli
from app.interfaces.mcp.server import run as mcp_run
from app.startup import startup_checks
from installer.core import EventImporterInstaller


def configure_logging(verbose: bool = False) -> None:
    """Configure logging with appropriate levels."""
    if verbose:
        level = logging.INFO
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    else:
        level = logging.WARNING
        format_str = "%(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(level=level, format=format_str, force=True)


def create_parser() -> ArgumentParser:
    """Create and configure the argument parser."""
    parser = ArgumentParser(
        prog="event-importer",
        description="Event Importer - Extract structured event data from websites",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"event-importer {__version__}",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Import command
    import_parser = subparsers.add_parser("import", help="Import an event from URL")
    import_parser.add_argument("url", help="URL to import")
    import_parser.add_argument(
        "--method",
        choices=["api", "web", "image"],
        help="Force import method",
    )
    import_parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds",
    )
    import_parser.add_argument(
        "--ignore-cache",
        action="store_true",
        help="Skip cache and force fresh import",
    )
    import_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List imported events")
    list_parser.add_argument("--limit", "-l", type=int, help="Limit number of results")
    list_parser.add_argument("--search", "-s", help="Search in URL or event data")
    list_parser.add_argument(
        "--details",
        "-d",
        action="store_true",
        help="Show detailed view",
    )
    list_parser.add_argument(
        "--sort",
        choices=["date", "url"],
        default="date",
        help="Sort by field",
    )
    list_parser.add_argument(
        "--order",
        choices=["asc", "desc"],
        default="desc",
        help="Sort order",
    )

    # Show command
    show_parser = subparsers.add_parser("show", help="Show specific event details")
    show_parser.add_argument("event_id", type=int, help="Event ID to show")

    # Stats command
    subparsers.add_parser("stats", help="Show database statistics")

    # Rebuild descriptions command
    rebuild_parser = subparsers.add_parser(
        "rebuild-descriptions", help="Rebuild descriptions for a specific event"
    )
    rebuild_parser.add_argument("event_id", type=int, help="Event ID to rebuild")

    # Validate command
    subparsers.add_parser("validate", help="Validate the installation")

    # Update command
    subparsers.add_parser("update", help="Update to the latest version")

    # MCP interface
    subparsers.add_parser("mcp", help="Run MCP server")

    # API interface
    api_parser = subparsers.add_parser("api", help="Run HTTP API server")
    api_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    api_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    api_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # Ticketfairy interface
    subparsers.add_parser("ticketfairy", help="Run Ticketfairy CLI")

    return parser


def route_command(parser: ArgumentParser, args: Namespace) -> None:
    """Route to the appropriate interface based on the command."""
    if args.command == "import":
        run_cli(args)
    elif args.command in ["list", "show", "stats", "rebuild-descriptions"]:
        asyncio.run(run_events_cli(args))
    elif args.command == "update":
        installer = EventImporterInstaller()
        installer.run_update()
    elif args.command == "mcp":
        mcp_run()
    elif args.command == "api":
        api_run(host=args.host, port=args.port, reload=args.reload)
    elif args.command == "ticketfairy":
        run_ticketfairy_cli(args)
    else:
        parser.print_help()


def main() -> int:
    """Main entry point that routes to appropriate interface."""
    parser = create_parser()
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

    # For commands that don't need the full startup procedure
    if args.command == "validate":
        run_validation_cli()
        return 0

    # Run startup checks and database initialization for all commands
    try:
        startup_checks()
    except (ValueError, TypeError, KeyError):
        logger.exception(CommonMessages.STARTUP_FAILED)
        return 1

    # Route to appropriate interface
    try:
        route_command(parser, args)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 0
    except (ValueError, TypeError, KeyError):
        logger.exception(CommonMessages.OPERATION_FAILED)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
