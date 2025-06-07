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

# Set logging to WARNING to reduce noise (but still capture them)
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

    event_info = {
        "Title": cursive_event.title,
        "Lineup": ", ".join(cursive_event.lineup),
        "Genres": ", ".join(cursive_event.genres),
        "Venue": cursive_event.venue,
    }
    cli.table([event_info], title="Event Data")

    # Test query building
    queries = image_service._build_search_queries(cursive_event)
    cli.console.print()
    cli.info(f"Generated {len(queries)} search queries:")
    for q in queries:
        cli.info(f"  • {q}")

    # Search for images
    cli.console.print()
    with cli.spinner("Searching for images"):
        candidates = await image_service.search_event_images(cursive_event)

    cli.success(f"Found {len(candidates)} image candidates")

    # Rate candidates
    if candidates:
        cli.console.print()
        cli.info("Rating top 5 candidates:")
        rated_results = []

        with cli.progress("Rating images") as progress:
            for i, candidate in enumerate(candidates[:5]):
                progress.update_progress(
                    (i / min(5, len(candidates))) * 100, f"Rating image {i+1}"
                )

                rated = await image_service.rate_image(candidate.url)
                rated_results.append(
                    {
                        "Score": rated.score,
                        "Dimensions": rated.dimensions or "Unknown",
                        "URL": candidate.url,
                    }
                )

        cli.console.print()
        cli.table(rated_results, title="Image Ratings")

    # Test case 2: Event with no lineup
    cli.section("Test 2: Event with title only")

    title_only_event = EventData(
        title="DJ Shadow & Cut Chemist at The Fillmore",
        venue="The Fillmore",
        date="2024-12-31",
    )

    event_info = {
        "Title": title_only_event.title,
        "Venue": title_only_event.venue,
        "Lineup": "None",
    }
    cli.table([event_info], title="Event Data")

    # Test artist extraction
    artist = image_service._extract_artist_from_title(title_only_event.title)
    cli.console.print()
    cli.info(f"Extracted artist from title: {artist or 'None'}")

    queries = image_service._build_search_queries(title_only_event)
    cli.info(f"Generated {len(queries)} search queries:")
    for q in queries:
        cli.info(f"  • {q}")

    await close_http_service()
    cli.console.print()
    cli.success("Image search test completed")


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

    # Display results
    result = {
        "Score": candidate.score,
        "Dimensions": candidate.dimensions or "Unknown",
        "Reason": candidate.reason or "Valid event image",
    }

    cli.console.print()
    cli.table([result], title="Rating Result")

    # Show scoring breakdown
    if candidate.score > 0 and candidate.dimensions:
        cli.section("Scoring Details")
        w, h = map(int, candidate.dimensions.split("x"))
        aspect_ratio = h / w

        cli.info(f"Base score: 50")

        if w >= 1000 or h >= 1000:
            cli.info(f"Size bonus (large): +100")
        elif w >= 800 or h >= 800:
            cli.info(f"Size bonus (medium): +50")
        elif w >= 600 or h >= 600:
            cli.info(f"Size bonus (small): +25")

        if aspect_ratio >= 1.4:
            cli.info(f"Aspect ratio (portrait): +300")
        elif aspect_ratio >= 1.2:
            cli.info(f"Aspect ratio (portrait): +250")
        elif 0.9 <= aspect_ratio <= 1.1:
            cli.info(f"Aspect ratio (square): +150")
        elif aspect_ratio >= 0.7:
            cli.info(f"Aspect ratio (landscape): +50")

        cli.info(f"Final score: {candidate.score}")

    await close_http_service()
    cli.console.print()
    cli.success("Image rating test completed")


async def main():
    """Run tests based on command line arguments."""
    import sys

    cli = get_cli()

    try:
        # Start capturing errors
        with cli.error_capture.capture():
            if len(sys.argv) > 1 and sys.argv[1] == "url":
                await test_specific_url()
            else:
                await test_image_search()

        # Show any captured errors
        if cli.error_capture.has_errors() or cli.error_capture.has_warnings():
            cli.show_captured_errors("Issues During Test")

    except KeyboardInterrupt:
        cli.warning("\nTest interrupted by user")
    except Exception as e:
        cli.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
