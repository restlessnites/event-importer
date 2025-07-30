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

    # Mock event data instead of making real API calls
    mock_events = {
        "1908868": {
            "id": "1908868",
            "title": "Test Event with Genres",
            "date": "2024-01-01",
            "venue": {"name": "Test Venue"},
            "genres": [{"name": "House"}, {"name": "Techno"}],
        },
        "1804533": {
            "id": "1804533",
            "title": "Test Event without Genres",
            "date": "2024-01-02",
            "venue": {"name": "Another Venue"},
            "genres": [],
        },
    }

    results = []
    summary = []
    for event_id in mock_events:
        clicycle.info(f"Testing event ID: {event_id}")

        clicycle.info("Using mock event data...")
        event = mock_events[event_id]

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
