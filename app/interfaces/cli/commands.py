"""CLI commands implementation."""

import asyncio

import click
import clicycle

from app import __version__
from app.integrations import get_available_integrations
from app.interfaces.api.server import run as api_run
from app.interfaces.cli.events import event_details
from app.interfaces.cli.events import list_events as list_events_cmd
from app.interfaces.cli.import_event import run_import
from app.interfaces.cli.stats import show_stats
from app.interfaces.cli.validate import run_validation
from app.interfaces.mcp.server import run as mcp_run

# Configure clicycle
clicycle.configure(app_name="event-importer")


@click.group()
@click.version_option(version=__version__, prog_name="event-importer")
def cli():
    """Event Importer - Extract structured event data from websites."""
    pass


@cli.command()
@click.argument("url")
@click.option(
    "--method",
    "-m",
    type=click.Choice(["api", "web", "image"]),
    help="Force import method",
)
@click.option("--timeout", "-t", type=int, default=60, help="Timeout in seconds")
@click.option(
    "--ignore-cache", is_flag=True, help="Skip cache and force fresh import"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def import_event(
    url: str, method: str, timeout: int, ignore_cache: bool, verbose: bool
):
    """Import an event from a URL."""
    run_import(url, method, timeout, ignore_cache, verbose)


@cli.command()
@click.option("--combined", "-c", is_flag=True, help="Show combined statistics")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed breakdown")
def stats(combined: bool, detailed: bool):
    """Show database statistics."""
    show_stats(detailed, combined)


@cli.command("event-details")
@click.argument("event_id", type=int)
def event_details_command(event_id: int):
    """Show details of a specific event."""
    event_details(event_id)


@cli.command()
@click.option("--limit", "-n", type=int, default=10, help="Number of events to list")
@click.option("--source", "-s", help="Filter by source")
def list_events(limit: int, source: str):
    """List recent events."""
    list_events_cmd(limit, source)


@cli.command()
def validate():
    """Validate the installation."""
    run_validation()


@cli.command()
def api():
    """Start the HTTP API server."""
    clicycle.info("Starting API server...")
    try:
        api_run()
    except KeyboardInterrupt:
        # Don't try to print anything on KeyboardInterrupt - just exit cleanly
        raise click.Abort() from None
    except Exception as e:
        raise click.ClickException(f"API server error: {e}") from e


@cli.command()
def mcp():
    """Start the MCP server."""
    clicycle.info("Starting MCP server...")
    try:
        asyncio.run(mcp_run())
    except KeyboardInterrupt:
        # Don't try to print anything on KeyboardInterrupt - just exit cleanly
        raise click.Abort() from None
    except Exception as e:
        raise click.ClickException(f"MCP server error: {e}") from e


def _add_integration_commands():
    """Dynamically add integration CLI commands to the main CLI."""
    integrations = get_available_integrations()
    
    for name, integration_class in integrations.items():
        try:
            integration = integration_class()
            cli_module = integration.get_cli_commands()
            
            if cli_module and hasattr(cli_module, 'cli'):
                # Add the integration's CLI commands as a subgroup
                cli.add_command(cli_module.cli, name=name)
        except Exception as e:
            clicycle.warning(f"Failed to load CLI commands for {name}: {e}")


# Add integration commands after CLI is defined
_add_integration_commands()
