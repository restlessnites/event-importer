#!/usr/bin/env -S uv run python
"""Test script to debug image search functionality."""

import asyncio
import logging
from pprint import pprint
from dotenv import load_dotenv

from app.config import get_config
from app.schemas import EventData
from app.services.image import ImageService
from app.http import get_http_service, close_http_service

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def test_image_search():
    """Test the image search with sample data."""
    config = get_config()
    http = get_http_service()
    image_service = ImageService(config, http)

    # Test case 1: Cursive event
    print("\n" + "=" * 60)
    print("TEST 1: Cursive Event")
    print("=" * 60)

    cursive_event = EventData(
        title="Cursive",
        venue="Zebulon",
        date="2024-09-13",
        lineup=["Cursive"],
        genres=["Rock", "Indie Rock"],
    )

    print("\nEvent data:")
    print(f"Title: {cursive_event.title}")
    print(f"Lineup: {cursive_event.lineup}")
    print(f"Genres: {cursive_event.genres}")

    # Test query building
    queries = image_service._build_search_queries(cursive_event)
    print(f"\nGenerated queries: {queries}")

    # Try the search
    if image_service.google_enabled:
        print("\nSearching for images...")
        candidates = await image_service.search_event_images(cursive_event)
        print(f"\nFound {len(candidates)} candidates")

        # Rate each candidate
        for i, candidate in enumerate(candidates[:5]):  # Limit to first 5
            print(f"\nCandidate {i+1}: {candidate.url}")
            rated = await image_service.rate_image(candidate.url)
            print(f"Score: {rated.score}")
            if rated.dimensions:
                print(f"Dimensions: {rated.dimensions}")
            if rated.reason:
                print(f"Reason: {rated.reason}")
    else:
        print("\nGoogle search not enabled!")

    # Test case 2: Event with no lineup
    print("\n" + "=" * 60)
    print("TEST 2: Event with title only")
    print("=" * 60)

    title_only_event = EventData(
        title="DJ Shadow & Cut Chemist at The Fillmore",
        venue="The Fillmore",
        date="2024-12-31",
    )

    print("\nEvent data:")
    print(f"Title: {title_only_event.title}")
    print(f"Lineup: {title_only_event.lineup}")

    queries = image_service._build_search_queries(title_only_event)
    print(f"\nGenerated queries: {queries}")

    # Test artist extraction
    artist = image_service._extract_artist_from_title(title_only_event.title)
    print(f"\nExtracted artist: {artist}")

    await close_http_service()


async def test_specific_url():
    """Test rating a specific image URL."""
    config = get_config()
    http = get_http_service()
    image_service = ImageService(config, http)

    print("\n" + "=" * 60)
    print("TEST: Rate specific image")
    print("=" * 60)

    test_url = "https://dice-media.imgix.net/attachments/2025-05-21/82c48e21-b16c-4c30-a32f-395fdf4316d1.jpg"

    print(f"\nTesting URL: {test_url}")
    candidate = await image_service.rate_image(test_url)

    print(f"\nScore: {candidate.score}")
    print(f"Dimensions: {candidate.dimensions}")
    if candidate.reason:
        print(f"Reason: {candidate.reason}")

    await close_http_service()


async def main():
    """Run tests."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "url":
        await test_specific_url()
    else:
        await test_image_search()


if __name__ == "__main__":
    asyncio.run(main())
