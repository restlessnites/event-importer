"""CLI interface for event listing and viewing commands."""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING, Any

from sqlalchemy import asc, desc, or_

from app.core.importer import EventImporter
from app.interfaces.cli.core import CLI
from app.shared.database.connection import get_db_session, init_db
from app.shared.database.models import EventCache
from app.shared.statistics import get_statistics

if TYPE_CHECKING:
    pass


def format_event_data(event_data: dict[str, Any]) -> dict[str, Any]:
    """Format event data for display"""
    # Extract key fields for table display
    return {
        "Title": event_data.get("title", "N/A"),
        "Venue": event_data.get("venue", "N/A"),
        "Date": event_data.get("date", "N/A"),
        "Time": event_data.get("time", {}).get("start", "N/A")
        if isinstance(event_data.get("time"), dict)
        else "N/A",
        "City": event_data.get("location", {}).get("city", "N/A")
        if isinstance(event_data.get("location"), dict)
        else "N/A",
        "Genres": ", ".join(event_data.get("genres", []))
        if event_data.get("genres")
        else "N/A",
        "Cost": event_data.get("cost", "N/A"),
    }


def show_stats(args: argparse.Namespace) -> None:
    """Show database statistics"""
    cli = CLI()

    stats_service = get_statistics()

    # Use args to allow filtering by date range
    days = getattr(args, "days", None)

    # Get combined statistics
    combined_stats = stats_service.get_combined_statistics()

    # Get trends if days parameter is provided
    trends = None
    if days:
        trends = stats_service.get_event_trends(days)

    cli.header("Database Statistics")

    # Event statistics
    event_stats = combined_stats["events"]
    event_data = [
        {"Metric": "Total Events", "Count": event_stats["total_events"]},
        {"Metric": "Events Today", "Count": event_stats["events_today"]},
        {"Metric": "Events This Week", "Count": event_stats["events_this_week"]},
        {"Metric": "Unsubmitted Events", "Count": event_stats["unsubmitted_events"]},
    ]

    cli.section("Event Statistics")
    cli.table(event_data)

    # Submission statistics (only if there are any submissions)
    submission_stats = combined_stats["submissions"]
    if submission_stats["total_submitted_events"] > 0:
        cli.section("Integration Statistics")

        # Basic submission stats
        submission_data = [
            {
                "Metric": "Total Submitted Events",
                "Count": submission_stats["total_submitted_events"],
            },
            {"Metric": "Success Rate", "Count": f"{submission_stats['success_rate']}%"},
        ]

        # Add status breakdown
        for status, count in submission_stats["by_status"].items():
            submission_data.append(
                {"Metric": f"{status.title()} Submissions", "Count": count},
            )

        cli.table(submission_data)

        # Service breakdown if multiple services exist
        if len(submission_stats["by_service"]) > 1:
            cli.section("By Service")
            service_data = [
                {"Service": service, "Submissions": count}
                for service, count in submission_stats["by_service"].items()
            ]
            cli.table(service_data)

    # Show trends if requested
    if trends:
        cli.section(f"Event Trends (Last {days} Days)")
        trend_data = []
        for entry in trends["daily_counts"]:
            trend_data.append(
                {"Date": entry["date"], "Events Imported": entry["count"]}
            )

        if trend_data:
            cli.table(trend_data)
            cli.info(f"Total events in period: {trends['total_in_period']}")
            cli.info(f"Average per day: {trends['average_per_day']:.1f}")
    else:
        cli.info("No integration submissions found")


async def run_events_cli(args: argparse.Namespace) -> None:
    """Run the events CLI with the given args."""
    # Initialize database
    init_db()

    try:
        if args.command == "list":
            list_events(args)
        elif args.command == "show":
            show_event_details(args)
        elif args.command == "stats":
            show_stats(args)
        elif args.command == "rebuild-descriptions":
            await rebuild_descriptions_cli(args)
    except KeyboardInterrupt:
        cli = CLI()
        cli.warning("\nInterrupted by user")
        sys.exit(1)
    except (ValueError, TypeError, KeyError) as e:
        cli = CLI()
        cli.error(f"Error: {e}")
        sys.exit(1)


def _build_event_query(db_session, args: argparse.Namespace):
    """Build the event query based on CLI arguments."""
    query = db_session.query(EventCache)

    if args.search:
        search_term = f"%{args.search}%"
        query = query.filter(
            or_(
                EventCache.source_url.like(search_term),
                EventCache.scraped_data.like(search_term),
            )
        )

    sort_map = {"date": EventCache.scraped_at, "url": EventCache.source_url}
    if args.sort in sort_map:
        sort_column = sort_map[args.sort]
        order_func = desc if args.order == "desc" else asc
        query = query.order_by(order_func(sort_column))

    if args.limit:
        query = query.limit(args.limit)

    return query


def _display_detailed_events(cli: CLI, events: list[EventCache]) -> None:
    """Display events in a detailed format."""
    for i, event in enumerate(events, 1):
        cli.section(f"Event {i}")
        cli.info(f"ID: {event.id}")
        cli.info(f"Source URL: {event.source_url}")
        cli.info(f"Scraped at: {event.scraped_at}")
        cli.info(f"Updated at: {event.updated_at}")

        formatted_data = format_event_data(event.scraped_data)
        cli.table([formatted_data])

        if event.submissions:
            submission_data = [
                {
                    "Service": sub.service_name,
                    "Status": sub.status,
                    "Submitted": (
                        sub.submitted_at.strftime("%Y-%m-%d %H:%M")
                        if sub.submitted_at
                        else "N/A"
                    ),
                    "Retries": sub.retry_count,
                }
                for sub in event.submissions
            ]
            cli.info("Submissions:")
            cli.table(submission_data)
        else:
            cli.info("No submissions for this event")

        if i < len(events):
            cli.spacer()


def _display_table_events(cli: CLI, events: list[EventCache]) -> None:
    """Display events in a table format."""
    table_data = [
        {
            "ID": event.id,
            "Scraped": event.scraped_at.strftime("%Y-%m-%d %H:%M"),
            **format_event_data(event.scraped_data),
        }
        for event in events
    ]
    cli.table(table_data, title="Imported Events")


def list_events(args: argparse.Namespace) -> None:
    """List imported events"""
    cli = CLI()
    with get_db_session() as db:
        query = _build_event_query(db, args)
        events = query.all()

    if not events:
        cli.warning("No events found in database.")
        return

    cli.header("Imported Events", f"Found {len(events)} events")

    if args.details:
        _display_detailed_events(cli, events)
    else:
        _display_table_events(cli, events)


async def rebuild_descriptions_cli(args: argparse.Namespace) -> None:
    """CLI handler for rebuilding descriptions."""
    cli = CLI()
    event_id = args.event_id

    cli.header("Rebuild Event Descriptions", f"Event ID: {event_id}")

    try:
        importer = EventImporter()
        with cli.spinner("Rebuilding descriptions..."):
            updated_event = await importer.rebuild_descriptions(event_id)

        if updated_event:
            cli.success("Successfully rebuilt descriptions.")
            cli.section("Updated Event Data")
            cli.event_card(updated_event.model_dump(mode="json"))
        else:
            cli.error(f"Failed to rebuild descriptions for event ID: {event_id}")
            cli.info("Check if the event ID is correct and exists in the database.")

    except Exception as e:
        cli.error(f"An unexpected error occurred: {e}")
        sys.exit(1)


def show_event_details(args: argparse.Namespace) -> None:
    """Show detailed information for a specific event"""
    cli = CLI()

    with get_db_session() as db:
        event = db.query(EventCache).filter(EventCache.id == args.event_id).first()

        if not event:
            cli.error(f"Event with ID {args.event_id} not found.")
            sys.exit(1)

        cli.header("Event Details", f"ID: {args.event_id}")

        # Basic info
        cli.info(f"Source URL: {event.source_url}")
        cli.info(f"Scraped at: {event.scraped_at}")
        cli.info(f"Updated at: {event.updated_at}")
        cli.info(f"Data hash: {event.data_hash}")

        # Event data
        cli.section("Event Data")
        cli.json(event.scraped_data)

        # Submissions
        if event.submissions:
            cli.section("Submissions")
            submission_data = []
            for sub in event.submissions:
                submission_data.append(
                    {
                        "ID": sub.id,
                        "Service": sub.service_name,
                        "Status": sub.status,
                        "Submitted": sub.submitted_at.strftime("%Y-%m-%d %H:%M")
                        if sub.submitted_at
                        else "N/A",
                        "Retries": sub.retry_count,
                        "Error": sub.error_message[:100] + "..."
                        if sub.error_message and len(sub.error_message) > 100
                        else sub.error_message or "N/A",
                    },
                )
            cli.table(submission_data)
        else:
            cli.info("No submissions for this event")
