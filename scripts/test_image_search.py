#!/usr/bin/env -S uv run python
"""Test script to debug image search functionality with CLI."""

import asyncio
import logging
from dotenv import load_dotenv

from app.config import get_config
from app.schemas import EventData
from app.services.image import ImageService
from app.http import get_http_service, close_http_service
from app.cli import get_cli

# Load environment variables
load_dotenv()

# Set logging to WARNING to reduce noise
logging.basicConfig(level=logging.WARNING)


async def test_image_search():
    """Test the image search with sample data."""
    cli = get_cli()

    cli.header("Image Search Test", "Testing Google Custom Search integration")

    config = get_config()
    http = get_http_service()
    image_service = ImageService(config, http)

    if not image_service.google_enabled:
        cli.error("Google Search API not configured!")
        cli.info("Set GOOGLE_API_KEY and GOOGLE_CSE_ID in .env file")
        return

    # Test case 1: Cursive event
    cli.section("Test 1: Artist with lineup")

    cursive_event = EventData(
        title="Cursive",
        venue="Zebulon",
        date="2024-09-13",
        lineup=["Cursive"],
        genres=["Rock", "Indie Rock"],
    )

    cli.info("Event Data:")
    cli.info(f"  Title: {cursive_event.title}")
    cli.info(f"  Lineup: {', '.join(cursive_event.lineup)}")
    cli.info(f"  Genres: {', '.join(cursive_event.genres)}")
    cli.info(f"  Venue: {cursive_event.venue}")

    # Test query building
    queries = image_service._build_search_queries(cursive_event)
    cli.info(f"\nGenerated {len(queries)} search queries:")
    for q in queries:
        cli.info(f"  • {q}")

    # Search for images
    with cli.spinner("Searching for images"):
        candidates = await image_service.search_event_images(cursive_event)

    cli.success(f"Found {len(candidates)} image candidates")

    # Rate ALL candidates for debugging
    if candidates:
        cli.info("\nRating all candidates:")

        with cli.progress("Rating images") as progress:
            for i, candidate in enumerate(candidates):
                progress.update_progress(
                    (i / len(candidates)) * 100, f"Rating image {i+1}"
                )

                rated = await image_service.rate_image(candidate.url)

                cli.info(f"\nCandidate {i+1}:")
                cli.info(f"  Score: {rated.score}")
                cli.info(f"  Dimensions: {rated.dimensions or 'Unknown'}")
                cli.info(f"  Source: {candidate.source}")
                cli.info(f"  URL: {candidate.url}")

    # Test case 2: Event with no lineup
    cli.section("Test 2: Event with title only")

    title_only_event = EventData(
        title="DJ Shadow & Cut Chemist at The Fillmore",
        venue="The Fillmore",
        date="2024-12-31",
    )

    cli.info("Event Data:")
    cli.info(f"  Title: {title_only_event.title}")
    cli.info(f"  Venue: {title_only_event.venue}")
    cli.info(f"  Lineup: None")

    # Test artist extraction
    artist = image_service._extract_artist_from_title(title_only_event.title)
    cli.info(f"\nExtracted artist from title: {artist or 'None'}")

    queries = image_service._build_search_queries(title_only_event)
    cli.info(f"\nGenerated {len(queries)} search queries:")
    for q in queries:
        cli.info(f"  • {q}")

    await close_http_service()
    cli.success("\nImage search test completed")


async def test_specific_url():
    """Test rating a specific image URL."""
    cli = get_cli()

    cli.header("Image Rating Test", "Testing specific image URL rating")

    config = get_config()
    http = get_http_service()
    image_service = ImageService(config, http)

    test_url = "https://dice-media.imgix.net/attachments/2025-05-21/82c48e21-b16c-4c30-a32f-395fdf4316d1.jpg"

    cli.section("Testing URL")
    cli.info(test_url)

    with cli.spinner("Downloading and rating image"):
        candidate = await image_service.rate_image(test_url)

    # Display full results
    cli.section("Rating Result")
    cli.info(f"Score: {candidate.score}")
    cli.info(f"Dimensions: {candidate.dimensions or 'Unknown'}")
    cli.info(f"Reason: {candidate.reason or 'Valid event image'}")
    cli.info(f"URL: {candidate.url}")

    await close_http_service()
    cli.success("\nImage rating test completed")


async def main():
    """Run tests based on command line arguments."""
    import sys

    cli = get_cli()

    try:
        if len(sys.argv) > 1 and sys.argv[1] == "url":
            await test_specific_url()
        else:
            await test_image_search()
    except KeyboardInterrupt:
        cli.warning("\nTest interrupted by user")
    except Exception as e:
        cli.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
