"""Event management commands."""

from urllib.parse import urlparse

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

            # Extract data from scraped_data JSON
            data = event.scraped_data or {}
            title = data.get("title", "Untitled Event")

            clicycle.header(f"Event #{event.id}: {title}")
            clicycle.info(f"URL: {event.source_url}")
            clicycle.info(f"Scraped: {event.scraped_at}")

            # Show additional fields if available
            if data.get("start_datetime"):
                clicycle.info(f"Start: {data['start_datetime']}")
            if data.get("end_datetime"):
                clicycle.info(f"End: {data['end_datetime']}")
            if data.get("venue_name"):
                clicycle.info(f"Venue: {data['venue_name']}")
            if data.get("description"):
                clicycle.section("Description")
                clicycle.info(data["description"])

            # Show scraped data fields
            clicycle.section("Available Fields")
            for key in sorted(data.keys()):
                if key not in ["title", "description"]:
                    clicycle.info(f"{key}: {data[key]}")
    except Exception as e:
        raise click.ClickException(f"Failed to show event: {e}") from e


def list_events(limit: int, source: str):
    """List recent events."""
    try:
        with get_db_session() as db:
            query = db.query(EventCache)

            # Filter by source domain if specified
            if source:
                # Filter by domain in source_url
                query = query.filter(EventCache.source_url.like(f"%{source}%"))

            # Order by scraped_at instead of created_at
            events = query.order_by(EventCache.scraped_at.desc()).limit(limit).all()

            if not events:
                clicycle.warning("No events found")
                return

            clicycle.header(f"Recent Events (showing {len(events)})")

            table_data = []
            for event in events:
                data = event.scraped_data or {}
                title = data.get("title", "Untitled Event")

                # Extract domain from URL
                parsed_url = urlparse(event.source_url)
                domain = (
                    parsed_url.netloc.replace("www.", "")
                    if parsed_url.netloc
                    else "Unknown"
                )

                start_date = data.get("date", "No date")

                table_data.append(
                    {
                        "ID": str(event.id),
                        "Title": title[:50] + "..." if len(title) > 50 else title,
                        "Domain": domain,
                        "Event Date": start_date,
                        "Scraped": event.scraped_at.strftime("%Y-%m-%d %H:%M"),
                    }
                )

            clicycle.table(table_data)

            clicycle.info("View details with: event-importer events details <id>")
    except AttributeError as e:
        # More specific error for missing attributes
        clicycle.error(f"Database schema issue: {e}")
        clicycle.info("The events table may need to be updated or recreated.")
        raise click.Abort() from e
    except Exception as e:
        raise click.ClickException(f"Failed to list events: {e}") from e
