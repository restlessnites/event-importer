#!/usr/bin/env -S uv run python
"""Test script to check genre data in RA GraphQL API."""

import logging

import clicycle
import pytest

from app.agents.ra_agent import ResidentAdvisorAgent
from app.config import get_config
from app.shared.http import close_http_service

# Set logging to reduce noise
logging.basicConfig(level=logging.WARNING)


@pytest.mark.asyncio
async def test_ra_genres(http_service, claude_service) -> None:
    """Test RA API for genre data."""
    clicycle.configure(app_name="event-importer-test")
    clicycle.header("RA Genre Data Test")
    clicycle.info("Testing RA API for genre data")

    config = get_config()
    agent = ResidentAdvisorAgent(
        config=config, services={"http": http_service, "llm": claude_service}
    )

    await _test_individual_events(agent)
    _print_summary()

    await close_http_service()


if __name__ == "__main__":
    try:
        # This would need proper fixtures when run standalone
        print("Run with pytest for proper fixture support")
    except KeyboardInterrupt:
        clicycle.warning("Test interrupted by user")


async def _test_individual_events(agent) -> None:
    """Test individual RA events for genre data."""
    clicycle.section("Testing Individual Events")
    event_ids = [
        "1908868",  # Has genres
        "1804533",  # No genres
    ]
    results = []
    summary = []
    for _, event_id in enumerate(event_ids):
        clicycle.info(f"Testing event ID: {event_id}")

        clicycle.info("Fetching event...")
        event = await agent._fetch_event(event_id)

        if not event:
            clicycle.error(f"Event {event_id} not found")
            continue

        genres = [g["name"] for g in event.get("genres", [])]
        results.append(
            {
                "ID": event_id,
                "Title": event.get("title", "Unknown"),
                "Date": event.get("date"),
                "Venue": event.get("venue", {}).get("name"),
                "Genres": ", ".join(genres) if genres else "None",
            }
        )
        summary.append(
            {
                "ID": event_id,
                "Title": event.get("title", "Unknown"),
                "Date": event.get("date"),
                "Venue": event.get("venue", {}).get("name"),
                "Genres": ", ".join(genres) if genres else "None",
            }
        )

    clicycle.table(results, title="Individual Event Results")


async def _test_event_listings(agent) -> None:
    """Test event listings for genre data."""
    clicycle.section("Event Listings Test")

    clicycle.info("Fetching event listings...")
    events = await agent._fetch_event_listings(20)

    if not events:
        clicycle.error("No event listings found")
        return

    summary = []
    for event in events:
        genres = [g["name"] for g in event.get("genres", [])]
        if genres:
            summary.append(
                {
                    "ID": event["id"],
                    "Title": event["title"],
                    "Date": event["date"],
                    "Venue": event.get("venue", {}).get("name"),
                    "Has Genres": "Yes",
                    "Genre Count": len(genres),
                }
            )

    clicycle.table(summary, title="Event Listing Genre Summary")


async def _test_genre_list(agent) -> None:
    """Attempt to fetch the genre list from RA."""
    clicycle.section("Genre List Test")

    clicycle.info("Fetching genre list...")
    genres = await agent._fetch_genre_list()

    if genres:
        clicycle.success(f"Found {len(genres)} genres")
        clicycle.table([{"Genre": g} for g in genres[:10]], title="Sample Genres")
    else:
        clicycle.warning("No genres found or method not implemented")


def _print_summary():
    """Print the summary of findings."""
    clicycle.section("Summary")
    clicycle.info("Key findings:")
    clicycle.list_item("Many RA events don't have genre tags")
    clicycle.list_item("Genre data appears to be optional in their system")
    clicycle.list_item("Events are often just categorized as 'Electronic music'")
    clicycle.list_item("Consider using artist/venue data to infer genres if needed")
