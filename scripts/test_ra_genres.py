#!/usr/bin/env -S uv run python
"""Test script to check genre data in RA GraphQL API."""

import asyncio
import json
import logging

from app.interfaces.cli import get_cli
from app.shared.http import close_http_service, get_http_service

# Set logging to reduce noise
logging.basicConfig(level=logging.WARNING)


async def test_ra_genres() -> None:
    """Test RA API for genre data."""
    cli = get_cli()
    cli.header("RA Genre Data Test", "Checking which events have genre information")

    http = get_http_service()

    # RA GraphQL endpoint
    url = "https://ra.co/graphql"
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://ra.co",
        "ra-content-language": "en",
        "referer": "https://ra.co/events",
    }

    # Test multiple event IDs
    cli.section("Testing Individual Events")

    event_ids = [
        "2141090",  # Your original event
        "2175498",  # The Cave x 6AM
        "2154601",  # WORK presents RAW
        "2133281",  # WORK presents: Matrixxman
        "1997137",  # Older event
    ]

    events_with_genres = 0

    with cli.progress("Testing events") as progress:
        for i, event_id in enumerate(event_ids):
            progress.update_progress(
                (i / len(event_ids)) * 100, f"Checking event {event_id}"
            )

            query = """
            query GET_EVENT($id: ID!) {
                event(id: $id) {
                    id
                    title
                    date
                    genres {
                        id
                        name
                    }
                }
            }
            """

            try:
                response = await http.post_json(
                    url,
                    service="RA",
                    headers=headers,
                    json={
                        "operationName": "GET_EVENT",
                        "variables": {"id": event_id},
                        "query": query,
                    },
                )

                if response.get("data", {}).get("event"):
                    event = response["data"]["event"]
                    genre_count = len(event.get("genres", []))
                    genre_names = [g["name"] for g in event.get("genres", [])]

                    if genre_count > 0:
                        events_with_genres += 1

                    cli.info(f"Event {event_id}: {event.get('title', 'Unknown')[:40]}")
                    if genre_names:
                        cli.success(f"  Genres: {', '.join(genre_names)}")
                    else:
                        cli.warning("  No genres")
                else:
                    cli.error(f"Event {event_id}: Not found")

            except Exception as e:
                cli.error(f"Event {event_id}: Error - {str(e)[:50]}")

    cli.console.print()
    cli.info(f"Summary: {events_with_genres}/{len(event_ids)} events have genre data")

    # Test event listings
    cli.section("Searching Event Listings for Genres")

    listing_query = """
    query GET_EVENT_LISTINGS($pageSize: Int, $page: Int) {
        eventListings(pageSize: $pageSize, page: $page) {
            data {
                event {
                    id
                    title
                    date
                    venue {
                        name
                    }
                    genres {
                        id
                        name
                    }
                }
            }
        }
    }
    """

    try:
        with cli.spinner("Fetching event listings"):
            response = await http.post_json(
                url,
                service="RA",
                headers=headers,
                json={
                    "operationName": "GET_EVENT_LISTINGS",
                    "variables": {"pageSize": 50, "page": 1},
                    "query": listing_query,
                },
            )

        listings = response.get("data", {}).get("eventListings", {}).get("data", [])

        # Find events with genres
        events_with_genres = [
            event for event in listings if event.get("event", {}).get("genres", [])
        ]

        cli.success(
            f"Found {len(events_with_genres)} events with genres out of {len(listings)} listings"
        )

        if events_with_genres:
            cli.console.print()
            cli.info("Sample events with genres:")
            for event_data in events_with_genres[:5]:
                event = event_data["event"]
                genres = ", ".join([g["name"] for g in event["genres"]])
                cli.info(f"• {event['title'][:50]}")
                cli.info(f"  Genres: {genres}")
                if event.get("venue", {}).get("name"):
                    cli.info(f"  Venue: {event['venue']['name']}")
                cli.console.print()

    except Exception as e:
        cli.error(f"Failed to fetch listings: {e}")

    # Try to get genre list
    cli.section("Attempting to Fetch Genre List")

    genre_query = """
    query GET_GENRES {
        genres {
            id
            name
        }
    }
    """

    try:
        with cli.spinner("Fetching genre list"):
            response = await http.post_json(
                url,
                service="RA",
                headers=headers,
                json={
                    "operationName": "GET_GENRES",
                    "variables": {},
                    "query": genre_query,
                },
            )

        if "errors" in response:
            cli.warning("Genre list query not available")
            cli.code(json.dumps(response["errors"], indent=2), "json", "GraphQL Errors")
        elif response.get("data", {}).get("genres"):
            genres = response["data"]["genres"]
            cli.success(f"Found {len(genres)} available genres")
            # Show first 10
            for genre in genres[:10]:
                cli.info(f"• {genre['id']}: {genre['name']}")
            if len(genres) > 10:
                cli.info(f"  ... and {len(genres) - 10} more")
        else:
            cli.warning("No genre data returned")

    except Exception as e:
        cli.warning(f"Genre list query failed: {e}")

    # Summary
    cli.section("Summary")
    cli.info("Key findings:")
    cli.info("• Many RA events don't have genre tags")
    cli.info("• Genre data appears to be optional in their system")
    cli.info("• Events are often just categorized as 'Electronic music'")
    cli.info("• Consider using artist/venue data to infer genres if needed")

    await close_http_service()
    cli.console.print()
    cli.success("Test completed!")


if __name__ == "__main__":
    try:
        asyncio.run(test_ra_genres())
    except KeyboardInterrupt:
        cli = get_cli()
        cli.warning("\nTest interrupted by user")
