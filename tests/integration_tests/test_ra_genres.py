#!/usr/bin/env -S uv run python
"""Test script to check genre data in RA GraphQL API."""

import asyncio
import logging

import pytest

from app.agents.ra_agent import ResidentAdvisorAgent
from app.config import get_config
from app.interfaces.cli.runner import get_cli
from app.shared.http import close_http_service

# Set logging to reduce noise
logging.basicConfig(level=logging.WARNING)


@pytest.mark.asyncio
async def test_ra_genres(cli, http_service, claude_service) -> None:
    """Test RA API for genre data."""
    cli.header("RA Genre Data Test", "Testing RA API for genre data")

    config = get_config()
    agent = ResidentAdvisorAgent(
        config=config, services={"http": http_service, "llm": claude_service}
    )

    await _test_individual_events(cli, agent)
    _print_summary(cli)

    await close_http_service()
    cli.console.print()


if __name__ == "__main__":
    try:
        asyncio.run(test_ra_genres())
    except KeyboardInterrupt:
        cli = get_cli()
        cli.warning("\nTest interrupted by user")


async def _test_individual_events(cli, agent) -> None:
    """Test individual RA events for genre data."""
    cli.section("Testing Individual Events")
    event_ids = [
        "1908868",  # Has genres
        "1804533",  # No genres
    ]
    results = []
    summary = []
    for _, event_id in enumerate(event_ids):
        cli.info(f"Testing event ID: {event_id}")

        with cli.spinner("Fetching event"):
            event = await agent._fetch_event(event_id)

        if not event:
            cli.error(f"Event {event_id} not found")
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

    cli.table(results, title="Individual Event Results")


async def _test_event_listings(cli, agent) -> None:
    """Test event listings for genre data."""
    cli.section("Event Listings Test")

    with cli.spinner("Fetching event listings"):
        events = await agent._fetch_event_listings(20)

    if not events:
        cli.error("No event listings found")
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

    cli.table(summary, title="Event Listing Genre Summary")


async def _test_genre_list(cli, agent) -> None:
    """Attempt to fetch the genre list from RA."""
    cli.section("Genre List Test")

    with cli.spinner("Fetching genre list"):
        genres = await agent._fetch_genre_list()

    if genres:
        cli.success(f"Found {len(genres)} genres")
        cli.table([{"Genre": g} for g in genres[:10]], title="Sample Genres")
    else:
        cli.warning("No genres found or method not implemented")


def _print_summary(cli):
    """Print the summary of findings."""
    cli.section("Summary")
    cli.info("Key findings:")
    cli.info("• Many RA events don't have genre tags")
    cli.info("• Genre data appears to be optional in their system")
    cli.info("• Events are often just categorized as 'Electronic music'")
    cli.info("• Consider using artist/venue data to infer genres if needed")
