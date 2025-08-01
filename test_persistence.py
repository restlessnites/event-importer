#!/usr/bin/env python3
"""Test script to verify if events are persisting to database."""

import asyncio

from sqlalchemy import desc, func

from app.core.importer import EventImporter
from app.shared.database.connection import get_db
from app.shared.database.models import Event


async def test_import_and_verify():
    """Import an event and verify it's in the database."""

    # Test URL
    url = "https://ra.co/events/2213092"

    # Get initial count
    with get_db() as db:
        initial_count = db.query(func.count(Event.id)).scalar()
        print(f"Initial event count: {initial_count}")

    # Import the event
    print(f"\nImporting: {url}")
    importer = EventImporter()
    result = await importer.import_event(url)

    print(f"Import success: {result['success']}")
    if result["success"]:
        print(f"Event title: {result['data']['title']}")
        print(f"Event date: {result['data']['date']}")

    # Check if it's in the database
    with get_db() as db:
        final_count = db.query(func.count(Event.id)).scalar()
        print(f"\nFinal event count: {final_count}")
        print(f"Events added: {final_count - initial_count}")

        # Try to find the specific event
        event = db.query(Event).filter(Event.source_url == url).first()
        if event:
            print("\n✓ Event found in database!")
            print(f"  ID: {event.id}")
            print(f"  Title: {event.title}")
            print(f"  Source: {event.source_url}")
        else:
            print("\n✗ Event NOT found in database!")

        # Show last 3 events
        print("\nLast 3 events in database:")
        recent = db.query(Event).order_by(desc(Event.imported_at)).limit(3).all()
        for e in recent:
            print(f"  - ID {e.id}: {e.title} (from {e.source_url})")


if __name__ == "__main__":
    asyncio.run(test_import_and_verify())
