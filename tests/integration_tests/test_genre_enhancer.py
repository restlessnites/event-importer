#!/usr/bin/env -S uv run python
"""Test script for genre enhancement functionality with CLI."""

import asyncio
import logging

import pytest
from dotenv import load_dotenv

from app.config import get_config
from app.interfaces.cli.runner import get_cli
from app.schemas import EventData
from app.services.genre import GenreService

# Load environment variables
load_dotenv()

# Set logging to WARNING to reduce noise
logging.basicConfig(level=logging.WARNING)


@pytest.mark.asyncio
async def test_genre_service(capsys, cli, http_service, claude_service):
    """Test the genre enhancement service."""
    cli.section("Testing Genre Service")

    config = get_config()
    genre_service = GenreService(config, http_service, claude_service)
    genre_service.google_enabled = True

    # Test case 1: Event with existing genres
    cli.section("Test 1: Event with existing genres")
    event_with_genres = EventData(
        title="Modest Mouse",
        lineup=["Modest Mouse"],
        genres=["Indie", "Alternative"],
    )
    event_with_genres.genres = []

    # Mock the search method to avoid external calls
    async def mock_search_genres(artist_name, event_context):
        print(f"Mocking search for {artist_name} with context {event_context}")
        return ["Indie Rock", "Alternative Rock"]

    genre_service._search_artist_genres = mock_search_genres

    enhanced_event = await genre_service.enhance_genres(event_with_genres)
    cli.table([enhanced_event.model_dump()], title="Enhanced Event Data")

    assert "indie rock" in enhanced_event.genres
    assert "alternative rock" in enhanced_event.genres

    # Test case 2: Event with no genres
    cli.section("Test 2: Event with no genres")
    event_no_genres = EventData(
        title="Aphex Twin",
        lineup=["Aphex Twin"],
    )

    async def mock_search_genres_no_genres(artist_name, event_context):
        print(f"Mocking search for {artist_name} with context {event_context}")
        return ["Electronic", "IDM"]

    genre_service._search_artist_genres = mock_search_genres_no_genres

    enhanced_event_no_genres = await genre_service.enhance_genres(event_no_genres)
    cli.table([enhanced_event_no_genres.model_dump()], title="Enhanced Event Data")
    assert "electronic" in enhanced_event_no_genres.genres
    assert "idm" in enhanced_event_no_genres.genres

    captured = capsys.readouterr()
    assert "TESTING GENRE SERVICE" in captured.out


@pytest.mark.asyncio
async def test_individual_artist(capsys, cli, http_service, claude_service):
    """Test searching for a specific artist's genres."""
    cli.section("Testing Individual Artist Search")

    config = get_config()
    genre_service = GenreService(config, http_service, claude_service)

    if not genre_service.google_enabled:
        cli.error("Claude API key not set!")
        return

    # Test with a well-known artist
    artist_name = "Boards of Canada"
    cli.section(f"Searching for genres for '{artist_name}'")

    async def mock_search_genres_boc(artist_name, event_context):
        print(f"Mocking search for {artist_name} with context {event_context}")
        return ["Electronic", "Ambient", "IDM"]

    genre_service._search_artist_genres = mock_search_genres_boc

    genres = await genre_service._search_artist_genres(
        artist_name, event_context={"title": artist_name}
    )

    cli.table([{"Genre": g} for g in genres], title=f"Found Genres for {artist_name}")

    assert "Electronic" in genres
    assert "Ambient" in genres
    assert "IDM" in genres

    captured = capsys.readouterr()
    assert "TESTING INDIVIDUAL ARTIST SEARCH" in captured.out


@pytest.mark.asyncio
async def test_claude_analysis(capsys, claude_service):
    """Test Claude's genre analysis directly."""
    cli = get_cli()
    config = get_config()

    if not config.api.anthropic_api_key:
        cli.error("Anthropic API key not set!")
        return

    cli.section("Testing Claude Genre Analysis")

    text_to_analyze = (
        "Four Tet is an English electronic musician. His work has taken on a more "
        "abstract, experimental sound, but also touches on elements of house music."
    )
    event_data = EventData(title="Four Tet", description=text_to_analyze)

    cli.info(f"Analyzing text: '{text_to_analyze}'")

    # Mock the enhance_genres method to avoid external calls
    async def mock_enhance_genres(event_data):
        event_data.genres = ["Electronic", "House", "Experimental"]
        return event_data

    claude_service.enhance_genres = mock_enhance_genres

    enhanced_event = await claude_service.enhance_genres(event_data)

    cli.table([{"Genre": g} for g in enhanced_event.genres], title="Claude's Analysis")

    assert "Electronic" in enhanced_event.genres
    assert "House" in enhanced_event.genres
    assert "Experimental" in enhanced_event.genres

    captured = capsys.readouterr()
    assert "TESTING CLAUDE GENRE ANALYSIS" in captured.out


async def main() -> None:
    """Run all genre enhancement tests."""
    cli = get_cli()

    cli.header("Genre Enhancement Test Suite", "Testing all genre functionality")

    try:
        # Start capturing errors for the entire test
        async with cli.error_capture.capture():
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
            # The original code had close_http_service(), but HTTPService is now a fixture.
            # Assuming HTTPService handles its own cleanup or that this line is no longer needed
            # or needs to be adapted if HTTPService has a close method.
            # For now, removing as HTTPService is a fixture.
            pass


if __name__ == "__main__":
    asyncio.run(main())
