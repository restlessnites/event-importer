"""Event management commands."""

import click
import clicycle

from app.shared.database.connection import get_db_session
from app.shared.database.models import EventCache


def event_details(event_id: int):
    """Show details of a specific event."""
    try:
        with get_db_session() as db:
            event = db.query(EventCache).filter(EventCache.id == event_id).first()
            if not event:
                raise click.ClickException(f"Event with ID {event_id} not found")

            clicycle.header(f"Event #{event.id}: {event.title}")
            clicycle.info(f"URL: {event.url}")
            clicycle.info(f"Source: {event.source}")
            clicycle.info(f"Start: {event.start_datetime}")
            if event.end_datetime:
                clicycle.info(f"End: {event.end_datetime}")
            if event.venue_name:
                clicycle.info(f"Venue: {event.venue_name}")
            if event.description:
                clicycle.info("Description:")
                clicycle.info(event.description)
    except Exception as e:
        raise click.ClickException(f"Failed to show event: {e}") from e


def list_events(limit: int, source: str):
    """List recent events."""
    try:
        with get_db_session() as db:
            query = db.query(EventCache)
            if source:
                query = query.filter(EventCache.source == source)
            events = query.order_by(EventCache.created_at.desc()).limit(limit).all()

            if not events:
                clicycle.warning("No events found")
                return

            clicycle.header(f"Recent Events (showing {len(events)})")
            for event in events:
                clicycle.info(f"#{event.id} - {event.title}")
                clicycle.info(
                    f"  Source: {event.source} | Date: {event.start_datetime}"
                )
                clicycle.info(f"  URL: {event.url}")
    except Exception as e:
        raise click.ClickException(f"Failed to list events: {e}") from e
