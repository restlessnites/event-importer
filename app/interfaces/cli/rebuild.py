"""CLI commands for rebuilding event data."""

import asyncio

import click
import clicycle

from app.config import get_config
from app.core.importer import EventImporter
from app.shared.service_errors import ServiceErrorFormatter


def rebuild_description(
    event_id: int,
    description_type: str,
    supplementary_context: str | None = None,
):
    """Rebuild description for an event."""
    clicycle.configure(app_name="event-importer")

    async def _rebuild():
        config = get_config()
        importer = EventImporter(config)
        return await importer.rebuild_description(
            event_id,
            description_type=description_type,
            supplementary_context=supplementary_context,
        )

    try:
        clicycle.header(f"Rebuilding {description_type} description")
        clicycle.info(f"Event ID: {event_id}")

        if supplementary_context:
            clicycle.info(f"Context: {supplementary_context}")

        result = asyncio.run(_rebuild())

        if result:
            clicycle.success(
                f"{description_type.capitalize()} description rebuilt successfully"
            )

            # Show the new description
            if description_type == "short":
                clicycle.section("New Short Description")
                clicycle.info(result.short_description)
            else:
                clicycle.section("New Long Description")
                clicycle.info(result.long_description)

            clicycle.warning("This is a preview - use 'update' command to save changes")
        else:
            clicycle.error(f"Event with ID {event_id} not found")
            raise click.Abort()

    except Exception as e:
        clicycle.error(f"Failed to rebuild description: {e}")
        raise click.Abort() from e


def _display_genre_rebuild_results(result, service_failures):
    """Display results and failures for genre rebuild."""
    if service_failures:
        failure_info = ServiceErrorFormatter.format_for_cli(
            [f.model_dump() if hasattr(f, 'model_dump') else f for f in service_failures]
        )
        if failure_info:
            clicycle.warning("Some services failed:")
            for msg in failure_info:
                clicycle.list_item(msg)

    if not result:
        return

    clicycle.success("Genres rebuilt successfully")
    if result.genres:
        clicycle.section("New Genres")
        for genre in result.genres:
            clicycle.list_item(genre)
    else:
        clicycle.warning("No genres found")
    clicycle.warning("This is a preview - use 'update' command to save changes")


def rebuild_genres(
    event_id: int,
    supplementary_context: str | None = None,
):
    """Rebuild genres for an event."""
    clicycle.configure(app_name="event-importer")

    async def _rebuild():
        config = get_config()
        importer = EventImporter(config)
        return await importer.rebuild_genres(
            event_id,
            supplementary_context=supplementary_context,
        )

    try:
        clicycle.header("Rebuilding genres")
        clicycle.info(f"Event ID: {event_id}")
        if supplementary_context:
            clicycle.info(f"Context: {supplementary_context}")

        result, service_failures = asyncio.run(_rebuild())
        _display_genre_rebuild_results(result, service_failures)

        if not result:
            clicycle.error(f"Event with ID {event_id} not found")
            raise click.Abort()

    except ValueError as e:
        if "no lineup" in str(e).lower():
            clicycle.error(str(e))
            clicycle.info("Tip: Use --context to provide artist names")
        else:
            clicycle.error(f"Failed to rebuild genres: {e}")
        raise click.Abort() from e
    except Exception as e:
        clicycle.error(f"Failed to rebuild genres: {e}")
        raise click.Abort() from e


def _display_image_rebuild_results(result, service_failures):
    """Display results and failures for image rebuild."""
    if service_failures:
        failure_info = ServiceErrorFormatter.format_for_cli(
            [f.model_dump() if hasattr(f, 'model_dump') else f for f in service_failures]
        )
        if failure_info:
            clicycle.warning("Some services failed:")
            for msg in failure_info:
                clicycle.list_item(msg)

    if not (result and result.image_search):
        return

    clicycle.success("Image search completed")

    if result.image_search.candidates:
        clicycle.section("Image Candidates Found")
        candidates_data = [
            {
                "Score": c.score,
                "Source": c.source,
                "Dimensions": c.dimensions or "Unknown",
                "Reason": c.reason,
                "URL": (c.url[:50] + "...") if len(c.url) > 50 else c.url,
            }
            for c in result.image_search.candidates
        ]
        clicycle.table(candidates_data, title="All Candidates")

    if result.image_search.selected:
        clicycle.section("Selected Image")
        clicycle.info(f"Score: {result.image_search.selected.score}")
        clicycle.info(f"URL: {result.image_search.selected.url}")

    clicycle.warning("This is a preview - use 'update' command to save changes")


def rebuild_image(
    event_id: int,
    supplementary_context: str | None = None,
):
    """Rebuild image for an event."""
    clicycle.configure(app_name="event-importer")

    async def _rebuild():
        config = get_config()
        importer = EventImporter(config)
        return await importer.rebuild_image(
            event_id,
            supplementary_context=supplementary_context,
        )

    try:
        clicycle.header("Rebuilding image")
        clicycle.info(f"Event ID: {event_id}")
        if supplementary_context:
            clicycle.info(f"Context: {supplementary_context}")

        result, service_failures = asyncio.run(_rebuild())
        _display_image_rebuild_results(result, service_failures)

        if not (result and result.image_search):
            clicycle.error(f"Event with ID {event_id} not found or no images found")
            raise click.Abort()

    except Exception as e:
        clicycle.error(f"Failed to rebuild image: {e}")
        raise click.Abort() from e


def update_event(event_id: int, updates: dict):
    """Update event fields."""
    clicycle.configure(app_name="event-importer")

    async def _update():
        config = get_config()
        importer = EventImporter(config)
        return await importer.update_event(event_id, updates)

    try:
        clicycle.header("Updating event")
        clicycle.info(f"Event ID: {event_id}")
        clicycle.info(f"Fields to update: {', '.join(updates.keys())}")

        result = asyncio.run(_update())

        if result:
            clicycle.success("Event updated successfully")

            # Show updated fields
            clicycle.section("Updated Fields")
            for field, value in updates.items():
                if isinstance(value, list):
                    value = ", ".join(value)
                elif isinstance(value, dict):
                    value = str(value)
                clicycle.info(f"{field}: {value}")
        else:
            clicycle.error(f"Event with ID {event_id} not found")
            raise click.Abort()

    except Exception as e:
        clicycle.error(f"Failed to update event: {e}")
        raise click.Abort() from e
