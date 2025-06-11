import asyncio
import argparse
import json
from typing import Optional

from .submitter import TicketFairySubmitter
from ...shared.database.connection import init_db
from ...interfaces.cli.core import CLI


async def submit_command(
    filter_type: str = "unsubmitted",
    url: Optional[str] = None,
    dry_run: bool = False
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
        
        if result['submitted']:
            cli.success(f"Successfully submitted: {len(result['submitted'])}")
            if dry_run:
                cli.section("Dry Run - Would be submitted")
                # Prepare data for the table
                table_data = [
                    {"ID": s["event_id"], "URL": s["url"]}
                    for s in result["submitted"]
                ]
                cli.table(table_data)

        if result['errors']:
            cli.error(f"Errors: {len(result['errors'])}")
            cli.section("Error Details")
            table_data = [
                {"Event ID": e["event_id"], "URL": e["url"], "Error": e["error"]}
                for e in result["errors"]
            ]
            cli.table(table_data)
        
        if not result['submitted'] and not result['errors']:
            cli.warning("No events found to submit.")
            
    except Exception as e:
        cli.error(f"An unexpected error occurred: {e}")
        return


def status_command() -> None:
    """Show submission status"""
    from ...shared.database.connection import get_db_session
    from ...shared.database.models import Submission, EventCache
    from ...interfaces.cli.core import CLI
    from sqlalchemy import func, select
    
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
                table_data.append({
                    "Status": status.capitalize(),
                    "Count": count
                })
            
            cli.table(table_data)
        else:
            cli.warning("No submissions found.")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="TicketFairy submission tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Submit command
    submit_parser = subparsers.add_parser("submit", help="Submit events to TicketFairy")
    submit_parser.add_argument(
        "--filter", "-f",
        default="unsubmitted",
        choices=["unsubmitted", "failed", "pending", "all"],
        help="Filter events to submit"
    )
    submit_parser.add_argument(
        "--url", "-u",
        help="Submit specific event by URL"
    )
    submit_parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Show what would be submitted without actually submitting"
    )
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show submission status")
    
    # Retry command (alias for submit --filter failed)
    retry_parser = subparsers.add_parser("retry-failed", help="Retry failed submissions")
    retry_parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Show what would be retried without actually submitting"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize database
    init_db()
    
    if args.command == "submit":
        asyncio.run(submit_command(
            filter_type=args.filter,
            url=args.url,
            dry_run=args.dry_run
        ))
    elif args.command == "status":
        status_command()
    elif args.command == "retry-failed":
        asyncio.run(submit_command(
            filter_type="failed",
            dry_run=args.dry_run
        ))


if __name__ == "__main__":
    main() 