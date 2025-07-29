"""TicketFairy CLI commands."""

import asyncio

import click
import clicycle

from app.integrations.ticketfairy.cli.display import (
    display_submission_results,
    display_submission_status,
)
from app.integrations.ticketfairy.shared.statistics import TicketFairyStatistics
from app.integrations.ticketfairy.shared.submitter import TicketFairySubmitter
from app.shared.database.connection import init_db
from app.shared.http import close_http_service


async def submit_events(
    filter_type: str = "unsubmitted",
    url: str | None = None,
    dry_run: bool = False,
) -> None:
    """Submit events to TicketFairy."""
    submitter = TicketFairySubmitter()

    try:
        if url:
            clicycle.info(f"Submitting specific URL: {url}")
            result = await submitter.submit_by_url(url, dry_run=dry_run)
        else:
            clicycle.info(f"Submitting events with filter: {filter_type}")
            result = await submitter.submit_events(filter_type, dry_run=dry_run)

        display_submission_results(submitter.service_name, result, dry_run)

    except (ValueError, TypeError, KeyError) as e:
        clicycle.error(f"An unexpected error occurred: {e}")
        return


def show_stats() -> None:
    """Show submission statistics."""
    stats_service = TicketFairyStatistics()
    stats = stats_service.get_submission_status()

    display_submission_status(
        stats["total_events"],
        stats["unsubmitted_count"],
        stats["status_counts"]
    )


@click.group()
def cli():
    """TicketFairy submission tool."""
    pass


@cli.command()
@click.option(
    "--filter",
    "-f",
    "filter_type",
    default="unsubmitted",
    type=click.Choice(["unsubmitted", "failed", "pending", "all"]),
    help="Filter events to submit",
)
@click.option("--url", "-u", help="Submit specific event by URL")
@click.option(
    "--dry-run",
    "-d",
    is_flag=True,
    help="Show what would be submitted without actually submitting",
)
def submit(filter_type: str, url: str, dry_run: bool):
    """Submit events to TicketFairy."""
    # Initialize database
    init_db()

    asyncio.run(submit_events(filter_type=filter_type, url=url, dry_run=dry_run))
    # Close HTTP service to prevent unclosed session warnings
    asyncio.run(close_http_service())


@cli.command()
def stats():
    """Show submission statistics."""
    # Initialize database
    init_db()
    show_stats()


@cli.command()
@click.option(
    "--dry-run",
    "-d",
    is_flag=True,
    help="Show what would be retried without actually submitting",
)
def retry_failed(dry_run: bool):
    """Retry failed submissions."""
    # Initialize database
    init_db()

    asyncio.run(submit_events(filter_type="failed", dry_run=dry_run))
    # Close HTTP service to prevent unclosed session warnings
    asyncio.run(close_http_service())
