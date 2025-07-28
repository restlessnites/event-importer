"""CLI runner for the event importer."""

from __future__ import annotations

import asyncio
import logging
import sys
from argparse import Namespace
from pathlib import Path

from rich.logging import RichHandler

from app.config import get_config
from app.core.router import Router
from app.error_messages import CommonMessages, InterfaceMessages
from app.interfaces.cli.core import CLI
from app.shared.http import close_http_service
from app.validators import InstallationValidator

# Global instance
_cli: CLI | None = None


def get_cli() -> CLI:
    """Get the global CLI instance."""
    global _cli
    if _cli is None:
        _cli = CLI()
    return _cli


class SuppressConsoleHandler(logging.StreamHandler):
    """Custom handler that suppresses console output during CLI operations."""

    def emit(self: SuppressConsoleHandler, record: logging.LogRecord) -> None:
        # Don't emit to console - let error capture handle it
        pass


def setup_quiet_logging() -> None:
    """Set up logging to suppress console output during CLI import."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    suppress_handler = SuppressConsoleHandler()
    root_logger.addHandler(suppress_handler)
    root_logger.setLevel(logging.WARNING)


def setup_verbose_logging() -> None:
    """Set up logging for verbose mode using rich for pretty, conflict-free output."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    rich_handler = RichHandler(
        console=get_cli().console,
        show_path=False,
        rich_tracebacks=True,
        log_time_format="[%X]",
    )
    rich_handler.setLevel(logging.INFO)

    root_logger.addHandler(rich_handler)
    root_logger.setLevel(logging.INFO)
    logging.getLogger("app").setLevel(logging.INFO)


def _setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity."""
    if verbose:
        setup_verbose_logging()
        get_cli().info("Verbose logging enabled")
    else:
        setup_quiet_logging()


def _build_request_data(args: Namespace) -> dict:
    """Construct the request data from CLI arguments."""
    request_data = {
        "url": args.url,
        "timeout": args.timeout,
        "ignore_cache": getattr(args, "ignore_cache", False),
    }
    if args.method:
        request_data["force_method"] = args.method
    return request_data


def _display_import_header(cli: CLI, args: Namespace, request_data: dict) -> None:
    """Display the header and informational messages for the import."""
    cli.header("EVENT IMPORTER", f"Importing from: {args.url}")
    if request_data.get("ignore_cache"):
        cli.info("Cache ignored - forcing fresh import")
    else:
        cli.info("Cache enabled - will use cached data if available")
    if getattr(args, "verbose", False):
        cli.info("Verbose logging enabled")


async def _run_import(
    router: Router, request_data: dict, cli: CLI, verbose: bool
) -> dict:
    """Run the import process and display progress."""
    if verbose:
        with cli.spinner("Importing event data..."):
            return await router.route_request(request_data)
    else:
        with cli.progress("Importing event data..."):
            return await router.route_request(request_data)


def _handle_import_result(result: dict | None, cli: CLI, verbose: bool) -> bool:
    """Process and display the result of the import."""
    if not result:
        if not verbose:
            cli.error("Import failed: An unexpected error occurred.")
        return False

    if result.get("success"):
        cli.success("Import successful")
        cli.event_card(result["data"])
        return True

    if not verbose:
        error_msg = result.get("error", "Unknown error")
        cli.error(f"Import failed: {error_msg}")
    return False


def _handle_errors(cli: CLI, verbose: bool) -> None:
    """Handle and display any captured errors."""
    if not verbose and (
        cli.error_capture.has_errors() or cli.error_capture.has_warnings()
    ):
        cli.show_captured_errors("Error Details")


async def main(args: Namespace) -> bool:
    """Main CLI entry point with clean error handling."""
    cli = get_cli()
    verbose = getattr(args, "verbose", False)
    _setup_logging(verbose)

    try:
        get_config()
        if not args.url:
            cli.error("URL is required")
            sys.exit(1)

        if not verbose:
            cli.error_capture.start(logging.WARNING)

        router = Router()
        request_data = _build_request_data(args)
        _display_import_header(cli, args, request_data)

        result = await _run_import(router, request_data, cli, verbose)

        if not verbose:
            cli.error_capture.stop()

        success = _handle_import_result(result, cli, verbose)
        if not success:
            _handle_errors(cli, verbose)
        return success

    except (ValueError, TypeError, KeyError) as e:
        cli.error(f"{InterfaceMessages.CLI_ERROR}: {e}")
        _handle_errors(cli, verbose)
        return False
    finally:
        try:
            await close_http_service()
        except (ValueError, TypeError, KeyError) as e:
            cli.warning(f"{InterfaceMessages.CLEANUP_WARNING}: {e}")


def run_cli(args: Namespace) -> None:
    """Run the CLI with the given args."""
    try:
        success = asyncio.run(main(args))
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        cli = get_cli()
        cli.warning("Interrupted by user")
        sys.exit(1)
    except (ValueError, TypeError, KeyError) as e:
        cli = get_cli()
        cli.error(f"{CommonMessages.FATAL_ERROR}: {e}")
        sys.exit(1)


def run_validation_cli() -> None:
    """Run the validation checks from the CLI."""
    cli = CLI()
    cli.header("Validating Installation")

    project_root = Path.cwd()
    validator = InstallationValidator()
    results = validator.validate(project_root)

    # Print a summary of checks by category
    for category, checks in results["checks"].items():
        if not checks:
            continue
        cli.console.print(f"\n[bold]{category}:[/bold]")
        for check, result in sorted(checks.items()):
            if isinstance(result, bool):
                status = "[green]✓[/green]" if result else "[red]✗[/red]"
                cli.console.print(f"  {status} {check}")
            else:
                cli.console.print(f"  [cyan]ℹ[/cyan] {check}: {result}")

    # Print detailed errors if validation failed
    if not results["success"]:
        cli.console.print("\n[bold red]Issues Found:[/bold red]")
        for error in results["errors"]:
            cli.console.print(f"  [red]✗ {error}[/red]")

    # Print warnings, regardless of success
    if results["warnings"]:
        cli.console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in results["warnings"]:
            cli.console.print(f"  [yellow]⚠ {warning}[/yellow]")

    # Print final status
    if not results["success"]:
        cli.console.print("\n[bold red]✗ Validation Failed.[/bold red]")
        sys.exit(1)
    else:
        cli.console.print("\n[bold green]✓ Validation complete.[/bold green]")
