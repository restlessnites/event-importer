#!/usr/bin/env python3
"""Diagnose why dry run returns empty results."""

import asyncio

from sqlalchemy import desc

from app.integrations.ticketfairy.shared.submitter import TicketFairySubmitter
from app.shared.database.connection import get_db_session
from app.shared.database.models import Event, Submission


async def diagnose_dry_run():
    """Diagnose why dry run returns empty results."""

    url = "https://ra.co/events/2213092"

    # Check database for the event
    with get_db_session() as db:
        print("=== Checking Database ===")

        # Look for the event by URL
        event = db.query(Event).filter(Event.source_url == url).first()

        if event:
            print("✓ Event found in database!")
            print(f"  ID: {event.id}")
            print(f"  URL: {event.source_url}")
            print(f"  Scraped at: {event.scraped_at}")

            # Check if already submitted
            submission = (
                db.query(Submission)
                .filter(
                    Submission.event_cache_id == event.id,
                    Submission.service_name == "ticketfairy",
                )
                .first()
            )

            if submission:
                print("\n✓ Event already submitted to TicketFairy")
                print(f"  Submission ID: {submission.id}")
                print(f"  Status: {submission.status}")
                print(f"  Submitted at: {submission.created_at}")
            else:
                print("\n✗ Event NOT submitted to TicketFairy yet")

        else:
            print("✗ Event NOT found in database!")
            print(f"  Looking for URL: {url}")

            # Show recent events
            print("\nRecent events in database:")
            recent = db.query(Event).order_by(desc(Event.scraped_at)).limit(5).all()
            for e in recent:
                print(f"  - ID {e.id}: {e.source_url} (scraped {e.scraped_at})")

    # Try the dry run
    print("\n=== Running Dry Run ===")
    submitter = TicketFairySubmitter()
    result = await submitter.submit_by_url(url, dry_run=True)

    print(f"Dry run result: {result}")

    if not result.get("submitted"):
        print("\nNo events in dry run result. Possible reasons:")
        print("1. Event not in database")
        print("2. Event already submitted successfully")
        print("3. Event filtered by transformer criteria")


if __name__ == "__main__":
    asyncio.run(diagnose_dry_run())
