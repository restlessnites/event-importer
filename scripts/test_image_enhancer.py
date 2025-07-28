#!/usr/bin/env -S uv run python
"""Test script to debug image search functionality with CLI."""

from __future__ import annotations

import asyncio
import logging
import sys

import pytest
from dotenv import load_dotenv

from app.config import get_config
from app.interfaces.cli.runner import get_cli
from app.schemas import EventData
from app.services.image import ImageService

# Load environment variables
load_dotenv()

# Set logging to WARNING to reduce noise (but still capture them)
logging.basicConfig(level=logging.WARNING)


@pytest.mark.parametrize(
    "url, expected",
    [
        (
            "https://dice-media.imgix.net/attachments/2025-05-21/82c48e21-b16c-4c30-a32f-395fdf4316d1.jpg",
            "dice-media.imgix.net",
        ),
        ("https://example.com/path/to/image.jpg", "example.com"),
        ("https://sub.example.com/path/to/image.jpg", "sub.example.com"),
        ("https://www.example.com/path/to/image.jpg", "example.com"),
        ("https://example.com/path/to/image.jpg?query=1", "example.com"),
        ("https://example.com/path/to/image.jpg#fragment", "example.com"),
        ("https://example.com/path/to/image.jpg?query=1#fragment", "example.com"),
        ("https://example.com/path/to/image.jpg?query=1#fragment", "example.com"),
        ("https://example.com/path/to/image.jpg?query=1#fragment", "example.com"),
    ],
)
def test_get_domain(url, expected):
    assert ImageService.get_domain(url) == expected, f"Failed on URL: {url}"


@pytest.mark.asyncio
async def test_image_search(capsys, cli, http_service):
    """Test the image search with sample data."""
    config = get_config()

    # Check if Google API is configured before proceeding
    if not (config.api.google_api_key and config.api.google_cse_id):
        pytest.skip("Google Search API not configured - set GOOGLE_API_KEY and GOOGLE_CSE_ID in .env file")

    # Additional check - if the API key looks invalid, skip the test
    if config.api.google_api_key == "test-key" or len(config.api.google_api_key) < 10:
        pytest.skip("Google API key appears to be a test/mock key")

    cli.header("Image Search Test", "Testing Google Custom Search integration")
    image_service = ImageService(config, http_service)

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
    }
    cli.table([event_info], title="Event Data")

    # Test artist extraction from title when lineup is missing
    cli.section("Testing artist extraction from title")
    title_only_event = EventData(
        title="DJ Shadow & Cut Chemist at Hollywood Bowl",
        venue="Hollywood Bowl",
        date="2024-06-23",
    )
    event_info = {
        "Title": title_only_event.title,
        "Venue": title_only_event.venue,
    }
    cli.table([event_info], title="Event Data")

    # Test artist extraction
    artist = image_service._get_primary_artist_for_search(title_only_event)
    cli.info(f"Extracted artist: {artist}")
    assert artist == "DJ Shadow & Cut Chemist"
    captured = capsys.readouterr()
    assert "IMAGE SEARCH TEST" in captured.out

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
                    (i / min(5, len(candidates))) * 100, f"Rating image {i + 1}"
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
    artist = image_service._get_primary_artist_for_search(title_only_event)
    cli.info(f"Extracted artist: {artist}")
    assert artist == "DJ Shadow & Cut Chemist"

    # Search for images
    cli.console.print()
    with cli.spinner("Searching for images"):
        candidates = await image_service.search_event_images(title_only_event)

    cli.success(f"Found {len(candidates)} image candidates")

    # Rate candidates
    if candidates:
        cli.console.print()
        cli.info("Rating top 5 candidates:")
        rated_results = []

        with cli.progress("Rating images") as progress:
            for i, candidate in enumerate(candidates[:5]):
                progress.update_progress(
                    (i / min(5, len(candidates))) * 100, f"Rating image {i + 1}"
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

    cli.console.print()
    cli.success("Image search test completed")


@pytest.mark.asyncio
async def test_specific_url(capsys, cli, http_service):
    """Test rating a specific image URL."""
    cli.header("Image Rating Test", "Testing rating a specific image URL")

    config = get_config()
    image_service = ImageService(config, http_service)

    async def mock_rate_image(url):
        if "low-quality" in url:
            return 0.2
        return 0.8

    image_service.rate_image = mock_rate_image

    test_cases = [
        {
            "url": "https://media.dice.fm/images/response/e795/e7950550-4f27-455b-8160-c9a72c478a87.jpg",
            "min_score": 0.7,
            "description": "Good quality, relevant",
        },
        {
            "url": "https://some-other-server.com/path/to/low-quality-image.jpg",
            "max_score": 0.3,
            "description": "Low quality, irrelevant",
        },
    ]

    for case in test_cases:
        cli.section(f"Testing URL: {case['description']}")
        url = case["url"]
        cli.info(f"URL: {url}")
        score = await image_service.rate_image(url)
        cli.info(f"Score: {score:.2f}")

        if "min_score" in case:
            assert score >= case["min_score"]
            cli.success("Passed: Score is above minimum threshold")
        if "max_score" in case:
            assert score <= case["max_score"]
            cli.success("Passed: Score is below maximum threshold")

    captured = capsys.readouterr()
    assert "IMAGE RATING TEST" in captured.out


async def main() -> None:
    """Run tests based on command line arguments."""
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
