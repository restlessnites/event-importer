"""CLI commands implementation."""

import asyncio

import click
import clicycle

from app import __version__
from app.interfaces.api.server import run as api_run
from app.interfaces.cli.events import event_details, list_events
from app.interfaces.cli.import_event import run_import
from app.interfaces.cli.rebuild import (
    rebuild_description,
    rebuild_genres,
    rebuild_image,
    update_event,
)
from app.interfaces.cli.settings import get_value, list_settings, set_value
from app.interfaces.cli.stats import show_stats
from app.interfaces.mcp.server import run as mcp_run
from app.services.integration_discovery import get_available_integrations

# Configure clicycle
clicycle.configure(app_name="event-importer")


@click.group()
@click.version_option(version=__version__, prog_name="event-importer")
def cli():
    """Event Importer - Extract structured event data from websites."""
    pass


@cli.group()
def events():
    """Manage events - import, list, update, and rebuild."""
    pass


@events.group()
def rebuild():
    """Rebuild event data - descriptions, genres, and images."""
    pass


@events.command(name="import")
@click.argument("url")
@click.option(
    "--method",
    "-m",
    type=click.Choice(["api", "web", "image"]),
    help="Force import method",
)
@click.option("--timeout", "-t", type=int, default=60, help="Timeout in seconds")
@click.option("--ignore-cache", is_flag=True, help="Skip cache and force fresh import")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def import_event_command(
    url: str, method: str, timeout: int, ignore_cache: bool, verbose: bool
):
    """Import an event from a URL."""
    run_import(url, method, timeout, ignore_cache, verbose)


@events.command(name="details")
@click.argument("event_id", type=int)
def event_details_command(event_id: int):
    """Show details of a specific event."""
    event_details(event_id)


@events.command(name="list")
@click.option("--limit", "-n", type=int, default=10, help="Number of events to list")
@click.option("--source", "-s", help="Filter by source")
def list_events_command(limit: int, source: str):
    """List recent events."""
    list_events(limit, source)


@rebuild.command(name="description")
@click.argument("event_id", type=int)
@click.option(
    "--type",
    "-t",
    "description_type",
    type=click.Choice(["short", "long"]),
    required=True,
    help="Which description to rebuild",
)
@click.option(
    "--context",
    "-c",
    help="Additional context to help regenerate the description",
)
def rebuild_description_command(event_id: int, description_type: str, context: str):
    """Rebuild a description for an event (preview only)."""
    rebuild_description(event_id, description_type, context)


@rebuild.command(name="genres")
@click.argument("event_id", type=int)
@click.option(
    "--context",
    "-c",
    help="Additional context to help identify genres (e.g., artist names if no lineup)",
)
def rebuild_genres_command(event_id: int, context: str):
    """Rebuild genres for an event (preview only)."""
    rebuild_genres(event_id, context)


@rebuild.command(name="image")
@click.argument("event_id", type=int)
@click.option(
    "--context",
    "-c",
    help="Additional context to help find better images",
)
def rebuild_image_command(event_id: int, context: str):
    """Rebuild image for an event (preview only)."""
    rebuild_image(event_id, context)


@events.command(name="update")
@click.argument("event_id", type=int)
@click.option("--title", help="Update event title")
@click.option("--venue", help="Update venue name")
@click.option("--date", help="Update event date (YYYY-MM-DD)")
@click.option("--end-date", help="Update end date for multi-day events (YYYY-MM-DD)")
@click.option("--short-description", help="Update short description")
@click.option("--long-description", help="Update long description")
@click.option("--genres", help="Update genres (comma-separated)")
@click.option("--lineup", help="Update lineup (comma-separated)")
@click.option("--minimum-age", help="Update minimum age requirement")
@click.option("--cost", help="Update cost information")
@click.option("--ticket-url", help="Update ticket URL")
@click.option("--promoters", help="Update promoters (comma-separated)")
def update_event_command(event_id: int, **kwargs):
    """Update event fields."""
    # Filter out None values and process list fields
    updates = {}
    for field, value in kwargs.items():
        if value is not None:
            # Convert underscores to camelCase for the API
            field_name = field.replace("-", "_")

            # Handle comma-separated lists
            if field_name in ["genres", "lineup", "promoters"]:
                updates[field_name] = [item.strip() for item in value.split(",")]
            else:
                updates[field_name] = value

    if not updates:
        clicycle.error("No fields to update specified")
        raise click.Abort()

    update_event(event_id, updates)


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
@click.option("--combined", "-c", is_flag=True, help="Show combined statistics")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed breakdown")
def stats(combined: bool, detailed: bool):
    """Show database statistics."""
    show_stats(detailed, combined)


@cli.command()
def mcp():
    """Start the MCP server."""
    # Don't output anything to stdout for MCP - it expects only JSON
    try:
        asyncio.run(mcp_run())
    except KeyboardInterrupt:
        # Don't try to print anything on KeyboardInterrupt - just exit cleanly
        raise click.Abort() from None
    except Exception as e:
        raise click.ClickException(f"MCP server error: {e}") from e


@cli.group()
def settings():
    """View and modify application settings."""
    pass


@settings.command(name="list")
def list_settings_command():
    """List all settings."""
    list_settings()


@settings.command(name="get")
@click.argument("setting_name")
def get_value_command(setting_name: str):
    """Get a specific setting value."""
    get_value(setting_name)


@settings.command(name="set")
@click.argument("setting_name")
@click.argument("setting_value")
def set_value_command(setting_name: str, setting_value: str):
    """Set a setting value."""
    set_value(setting_name, setting_value)


def _add_integration_commands():
    """Dynamically add integration CLI commands to the main CLI."""
    integrations = get_available_integrations()

    for name, integration_class in integrations.items():
        try:
            integration = integration_class()
            cli_module = integration.get_cli_commands()

            if cli_module and hasattr(cli_module, "cli"):
                # Add the integration's CLI commands as a subgroup
                cli.add_command(cli_module.cli, name=name)
        except Exception as e:
            clicycle.warning(f"Failed to load CLI commands for {name}: {e}")


# Add integration commands after CLI is defined
_add_integration_commands()
