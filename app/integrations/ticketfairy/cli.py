""" TicketFairy CLI. """

import argparse
import asyncio

from ...interfaces.cli.core import CLI
from ...shared.database.connection import init_db
from ...shared.http import close_http_service
from .submitter import TicketFairySubmitter


async def submit_command(
    filter_type: str = "unsubmitted", url: str | None = None, dry_run: bool = False
) -> None:
    """Submit events to TicketFairy"""
    submitter = TicketFairySubmitter()
    cli = CLI()

    try:
        if url:
            cli.info(f"Submitting specific URL: {url}")
            result = await submitter.submit_by_url(url, dry_run=dry_run)
        else:
            cli.info(f"Submitting events with filter: {filter_type}")
            result = await submitter.submit_events(filter_type, dry_run=dry_run)

        # Summary
        cli.header(f"Submission Results for '{submitter.service_name}'")
        cli.info(f"Selector: {result['selector']}")
        cli.info(f"Total events processed: {result['total']}")

        if result["submitted"]:
            cli.success(f"Successfully submitted: {len(result['submitted'])}")
            if dry_run:
                cli.section("Dry Run - Would be submitted")

                # Show detailed transformation data for each event
                for i, submission in enumerate(result["submitted"], 1):
                    cli.console.print()
                    cli.info(f"Event {i}: ID {submission['event_id']}")
                    cli.info(f"URL: {submission['url']}")

                    # Show the actual TicketFairy payload
                    if "data" in submission:
                        cli.console.print()
                        cli.info("TicketFairy API Payload:")

                        # Extract key fields from the transformed data
                        payload = submission["data"]
                        if "data" in payload and "attributes" in payload["data"]:
                            attrs = payload["data"]["attributes"]

                            # Show key transformed fields in a readable format
                            key_fields = {
                                "Title": attrs.get("title", "N/A"),
                                "Venue": attrs.get("venue", "N/A"),
                                "Ticket URL": attrs.get("url", "N/A"),
                                "Address": attrs.get("address", "N/A"),
                                "Start Date": attrs.get("startDate", "N/A"),
                                "End Date": attrs.get("endDate", "N/A"),
                                "Timezone": attrs.get("timezone", "N/A"),
                                "Status": attrs.get("status", "N/A"),
                                "Image URL": attrs.get("image", "N/A")[:60] + "..."
                                if len(attrs.get("image", "")) > 60
                                else attrs.get("image", "N/A"),
                                "Is Online": attrs.get("isOnline", "N/A"),
                                "Hosted By": attrs.get("hostedBy", "N/A"),
                            }

                            cli.table(
                                [key_fields], title=f"Event {i} - TicketFairy Fields"
                            )

                            # Show details (description) separately since it can be long
                            if attrs.get("details"):
                                cli.console.print()
                                cli.info("Description/Details:")
                                # Strip HTML tags for cleaner display
                                import re

                                details_clean = re.sub(r"<[^>]+>", "", attrs["details"])
                                cli.console.print(
                                    f"  {details_clean[:200]}..."
                                    if len(details_clean) > 200
                                    else f"  {details_clean}"
                                )

                        # Option to show full JSON payload
                        cli.console.print()
                        cli.info("Full JSON Payload (use this to debug API issues):")
                        cli.json(payload, title="Complete TicketFairy API Payload")

                        # Separator between events if multiple
                        if i < len(result["submitted"]):
                            cli.rule()
            else:
                # For actual submissions, show simpler summary
                table_data = [
                    {
                        "ID": s["event_id"],
                        "URL": s["url"],
                        "Status": s.get("status", "success"),
                    }
                    for s in result["submitted"]
                ]
                cli.table(table_data)

        if result["errors"]:
            cli.error(f"Errors: {len(result['errors'])}")
            cli.section("Error Details")
            table_data = [
                {"Event ID": e["event_id"], "URL": e["url"], "Error": e["error"]}
                for e in result["errors"]
            ]
            cli.table(table_data)

        if not result["submitted"] and not result["errors"]:
            cli.warning("No events found to submit.")

    except Exception as e:
        cli.error(f"An unexpected error occurred: {e}")
        return


def status_command() -> None:
    """Show submission status"""
    from sqlalchemy import func, select

    from ...interfaces.cli.core import CLI
    from ...shared.database.connection import get_db_session
    from ...shared.database.models import EventCache, Submission

    # Initialize CLI with theme
    cli = CLI()

    with get_db_session() as db:
        # Get submission counts by status
        status_counts = (
            db.query(Submission.status, func.count(Submission.id))
            .filter(Submission.service_name == "ticketfairy")
            .group_by(Submission.status)
            .all()
        )

        # Get total cached events
        total_events = db.query(func.count(EventCache.id)).scalar()

        # Get unsubmitted count - fix SQLAlchemy warning by using select() explicitly
        submitted_event_ids_query = select(Submission.event_cache_id).where(
            Submission.service_name == "ticketfairy"
        )
        unsubmitted_count = (
            db.query(func.count(EventCache.id))
            .filter(~EventCache.id.in_(submitted_event_ids_query))
            .scalar()
        )

        # Use CLI components for proper formatting
        cli.header("TicketFairy Submission Status")

        # Show key metrics
        cli.info(f"Total cached events: {total_events}")
        cli.info(f"Unsubmitted events: {unsubmitted_count}")

        if status_counts:
            cli.section("Submission Status Breakdown")

            # Convert to table data
            table_data = []
            for status, count in status_counts:
                table_data.append({"Status": status.capitalize(), "Count": count})

            cli.table(table_data)
        else:
            cli.warning("No submissions found.")


def main() -> None:
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="TicketFairy submission tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Submit command
    submit_parser = subparsers.add_parser("submit", help="Submit events to TicketFairy")
    submit_parser.add_argument(
        "--filter",
        "-f",
        default="unsubmitted",
        choices=["unsubmitted", "failed", "pending", "all"],
        help="Filter events to submit",
    )
    submit_parser.add_argument("--url", "-u", help="Submit specific event by URL")
    submit_parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Show what would be submitted without actually submitting",
    )

    # Status command
    subparsers.add_parser("status", help="Show submission status")

    # Retry command (alias for submit --filter failed)
    retry_parser = subparsers.add_parser(
        "retry-failed", help="Retry failed submissions"
    )
    retry_parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Show what would be retried without actually submitting",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize database
    init_db()

    if args.command == "submit":
        asyncio.run(
            submit_command(filter_type=args.filter, url=args.url, dry_run=args.dry_run)
        )
        # Close HTTP service to prevent unclosed session warnings
        asyncio.run(close_http_service())
    elif args.command == "status":
        status_command()
    elif args.command == "retry-failed":
        asyncio.run(submit_command(filter_type="failed", dry_run=args.dry_run))
        # Close HTTP service to prevent unclosed session warnings
        asyncio.run(close_http_service())


if __name__ == "__main__":
    main()
