#!/usr/bin/env -S uv run python
"""Test script for genre enhancement functionality with CLI."""

import asyncio
import logging
from dotenv import load_dotenv

from app.config import get_config
from app.schemas import EventData
from app.services.genre import GenreService
from app.services.claude import ClaudeService
from app.http import get_http_service, close_http_service
from app.data.genres import MusicGenres
from app.cli import get_cli

# Load environment variables
load_dotenv()

# Set logging to WARNING to reduce noise
logging.basicConfig(level=logging.WARNING)


async def test_genre_data():
    """Test the genre data and validation utilities."""
    cli = get_cli()

    cli.section("Testing Genre Data & Validation")

    # Test genre normalization
    test_genres = [
        "Electronic Music",  # Should normalize to "electronic"
        "Hip-Hop",  # Should normalize to "hip hop"
        "Alternative Rock",  # Should stay as "alternative rock"
        "EDM",  # Should alias to "electronic"
        "Indie",  # Should alias to "indie rock"
        "Random Genre",  # Should be filtered out
        "Techno",  # Should stay as "techno"
    ]

    results = []
    for genre in test_genres:
        normalized = MusicGenres.normalize_genre(genre)
        category = MusicGenres.get_category(normalized)
        is_valid = normalized in MusicGenres.ALL_GENRES

        results.append(
            {
                "Input": genre,
                "Normalized": normalized,
                "Category": category,
                "Valid": "✓" if is_valid else "✗",
            }
        )

    cli.table(results, title="Genre Normalization Tests")

    # Test validation
    cli.console.print()
    cli.info("Testing genre validation:")

    test_list = ["Electronic Music", "Hip-Hop", "Random Genre", "Techno", "Pop"]
    validated = MusicGenres.validate_genres(test_list)

    cli.info(f"Input: {test_list}")
    cli.info(f"Validated: {validated}")


async def test_genre_service():
    """Test the genre enhancement service."""
    cli = get_cli()

    cli.section("Testing Genre Service")

    config = get_config()
    http = get_http_service()
    claude = ClaudeService(config)
    genre_service = GenreService(config, http, claude)

    # Check if service is enabled
    if not genre_service.google_enabled:
        cli.error("Google Search API not configured!")
        cli.info("Set GOOGLE_API_KEY and GOOGLE_CSE_ID in .env file")
        return

    cli.success("Genre service enabled")

    # Test cases
    test_events = [
        {
            "name": "Cursive Event",
            "event": EventData(
                title="Cursive at Zebulon",
                venue="Zebulon",
                date="2024-09-13",
                lineup=["Cursive"],
                genres=[],  # No genres - should be enhanced
            ),
        },
        {
            "name": "Electronic Event",
            "event": EventData(
                title="Bonobo Live",
                venue="The Greek Theatre",
                date="2024-10-15",
                lineup=["Bonobo"],
                genres=[],  # No genres - should be enhanced
            ),
        },
        {
            "name": "Already Has Genres",
            "event": EventData(
                title="Some Event",
                venue="Venue",
                date="2024-12-01",
                lineup=["Artist"],
                genres=["Rock"],  # Already has genres - should be skipped
            ),
        },
    ]

    # Start capturing errors
    with cli.error_capture.capture():
        for test_case in test_events:
            cli.console.print()
            cli.info(f"Testing: {test_case['name']}")
            cli.console.print()

            event_info = {
                "Title": test_case["event"].title,
                "Lineup": ", ".join(test_case["event"].lineup),
                "Current Genres": ", ".join(test_case["event"].genres) or "None",
            }
            cli.table([event_info], title="Event Data")

            # Test enhancement
            with cli.spinner("Enhancing genres"):
                enhanced_event = await genre_service.enhance_genres(test_case["event"])

            if enhanced_event.genres:
                cli.success(f"Enhanced with genres: {enhanced_event.genres}")
            else:
                cli.warning("No genres found or event skipped")


async def test_individual_artist():
    """Test searching for a specific artist's genres."""
    cli = get_cli()

    cli.section("Testing Individual Artist Search")

    config = get_config()
    http = get_http_service()
    claude = ClaudeService(config)
    genre_service = GenreService(config, http, claude)

    if not genre_service.google_enabled:
        cli.error("Google Search API not configured!")
        return

    # Test artist
    artist_name = "Cursive"
    event_context = {
        "title": "Cursive at Zebulon",
        "venue": "Zebulon",
        "date": "2024-09-13",
        "lineup": ["Cursive"],
    }

    cli.info(f"Searching for genres for: {artist_name}")
    cli.console.print()
    cli.table(
        [
            {
                "Artist": artist_name,
                "Venue": event_context["venue"],
                "Date": event_context["date"],
            }
        ],
        title="Search Context",
    )

    with cli.error_capture.capture():
        try:
            with cli.spinner("Searching Google and analyzing with Claude"):
                # Test the internal search method
                genres = await genre_service._search_artist_genres(
                    artist_name, event_context
                )

            if genres:
                cli.success(f"Found genres: {genres}")

                # Test validation
                validated = MusicGenres.validate_genres(genres)
                cli.info(f"After validation: {validated}")
            else:
                cli.warning("No genres found")

        except Exception as e:
            cli.error(f"Search failed: {e}")
            import traceback

            cli.code(traceback.format_exc(), "python", "Exception Details")


async def test_claude_analysis():
    """Test Claude's genre analysis directly."""
    cli = get_cli()

    cli.section("Testing Claude Genre Analysis")

    config = get_config()
    http = get_http_service()
    claude = ClaudeService(config)
    genre_service = GenreService(config, http, claude)  # ADD THIS LINE

    # Mock search results
    mock_results = """Title: Cursive (band) - Wikipedia
Description: Cursive is an American indie rock band from Omaha, Nebraska. The band was formed in 1995 and consists of Tim Kasher (vocals, guitar), Matt Maginn (bass), Cully Symington (drums), Patrick Newbery (keyboards), and Gretta Cohn (cello).
Source: en.wikipedia.org

---

Title: Cursive | Discogs
Description: Indie Rock, Emo, Post-Hardcore band from Omaha, Nebraska, United States. Active from 1995 to present.
Source: discogs.com"""

    artist_name = "Cursive"
    event_context = {
        "title": "Cursive at Zebulon",
        "venue": "Zebulon",
        "lineup": ["Cursive"],
    }

    cli.info(f"Testing Claude analysis for: {artist_name}")

    with cli.error_capture.capture():
        try:
            with cli.spinner("Analyzing with Claude"):
                genres = await genre_service._extract_genres_with_claude(
                    artist_name, mock_results, event_context
                )

            if genres:
                cli.success(f"Claude extracted genres: {genres}")
            else:
                cli.warning("Claude returned no genres")

        except Exception as e:
            cli.error(f"Claude analysis failed: {e}")
            import traceback

            cli.code(traceback.format_exc(), "python", "Exception Details")


async def main():
    """Run all genre enhancement tests."""
    cli = get_cli()

    cli.header("Genre Enhancement Test Suite", "Testing all genre functionality")

    try:
        # Start capturing errors for the entire test
        with cli.error_capture.capture():
            # Test 1: Data validation
            await test_genre_data()

            # Test 2: Service functionality
            await test_genre_service()

            # Test 3: Individual artist search
            await test_individual_artist()

            # Test 4: Claude analysis
            await test_claude_analysis()

        # Show any captured errors
        if cli.error_capture.has_errors() or cli.error_capture.has_warnings():
            cli.show_captured_errors("Issues During Testing")

        cli.rule("Test Summary")
        cli.success("All genre enhancement tests completed")

    except KeyboardInterrupt:
        cli.warning("\nTests interrupted by user")
    except Exception as e:
        cli.error(f"Test suite failed: {e}")
        raise
    finally:
        # Clean up
        with cli.spinner("Cleaning up connections"):
            await close_http_service()


if __name__ == "__main__":
    asyncio.run(main())
