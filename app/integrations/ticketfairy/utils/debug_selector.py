"""Debug version of URL selector with verbose logging."""

from __future__ import annotations

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.integrations.base import BaseSelector
from app.shared.database.models import Event, Submission


class DebugURLSelector(BaseSelector):
    """Debug version of URL selector that logs what it finds."""

    def __init__(
        self: DebugURLSelector, url: str, check_submitted: bool = True
    ) -> None:
        self.url = url
        self.check_submitted = check_submitted

    def select_events(
        self: DebugURLSelector,
        db: Session,
        service_name: str,
    ) -> list[Event]:
        print("\n=== DebugURLSelector ===")
        print(f"Looking for URL: {self.url}")
        print(f"Service name: {service_name}")
        print(f"Check submitted: {self.check_submitted}")

        # First, show all events in database
        all_events = db.query(Event).all()
        print(f"\nTotal events in database: {len(all_events)}")
        if all_events:
            print("Recent 5 events:")
            for event in all_events[:5]:
                print(f"  - ID {event.id}: {event.source_url}")

        # Look for the specific event
        event = db.query(Event).filter(Event.source_url == self.url).first()

        if not event:
            print(f"\n✗ Event NOT found with URL: {self.url}")

            # Try partial match
            partial_matches = (
                db.query(Event).filter(Event.source_url.contains("2213092")).all()
            )
            if partial_matches:
                print(f"\nFound {len(partial_matches)} partial matches for '2213092':")
                for match in partial_matches:
                    print(f"  - ID {match.id}: {match.source_url}")

            return []

        print("\n✓ Event found!")
        print(f"  ID: {event.id}")
        print(f"  URL: {event.source_url}")
        print(f"  Scraped at: {event.scraped_at}")

        # If check_submitted is True, only return if not already submitted to this service
        if self.check_submitted:
            existing_submission = (
                db.query(Submission)
                .filter(
                    and_(
                        Submission.event_cache_id == event.id,
                        Submission.service_name == service_name,
                        Submission.status.in_(["success", "pending"]),
                    )
                )
                .first()
            )
            if existing_submission:
                print(f"\n✗ Event already submitted to {service_name}")
                print(f"  Submission ID: {existing_submission.id}")
                print(f"  Status: {existing_submission.status}")
                print(f"  Created at: {existing_submission.created_at}")
                return []  # Already submitted
            print(f"\n✓ Event not yet submitted to {service_name}")

        print("\nReturning event for submission")
        return [event]
