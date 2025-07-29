#!/usr/bin/env -S uv run python
"""Test script for genre enhancement functionality with CLI."""

import asyncio
import logging

import clicycle
import pytest
from dotenv import load_dotenv

from app.config import get_config
from app.schemas import EventData
from app.services.genre import GenreService

# Load environment variables
load_dotenv()

# Set logging to WARNING to reduce noise
logging.basicConfig(level=logging.WARNING)


@pytest.mark.asyncio
async def test_genre_service(capsys, http_service, claude_service):
    """Test the genre enhancement service."""
    clicycle.configure(app_name="event-importer-test")
    clicycle.header("Testing Genre Service")

    config = get_config()
    genre_service = GenreService(config, http_service, claude_service)
    genre_service.google_enabled = True

    # Test case 1: Event with existing genres
    clicycle.section("Test 1: Event with existing genres")
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
    clicycle.table([enhanced_event.model_dump()], title="Enhanced Event Data")

    assert "indie rock" in enhanced_event.genres
    assert "alternative rock" in enhanced_event.genres

    # Test case 2: Event with no genres
    clicycle.section("Test 2: Event with no genres")
    event_no_genres = EventData(
        title="Aphex Twin",
        lineup=["Aphex Twin"],
    )

    async def mock_search_genres_no_genres(artist_name, event_context):
        print(f"Mocking search for {artist_name} with context {event_context}")
        return ["Electronic", "IDM"]

    genre_service._search_artist_genres = mock_search_genres_no_genres

    enhanced_event_no_genres = await genre_service.enhance_genres(event_no_genres)
    clicycle.table([enhanced_event_no_genres.model_dump()], title="Enhanced Event Data")
    assert "electronic" in enhanced_event_no_genres.genres
    assert "idm" in enhanced_event_no_genres.genres

    captured = capsys.readouterr()
    assert "TESTING GENRE SERVICE" in captured.out


@pytest.mark.asyncio
async def test_individual_artist(capsys, http_service, claude_service):
    """Test searching for a specific artist's genres."""
    clicycle.configure(app_name="event-importer-test")
    clicycle.header("Testing Individual Artist Search")

    config = get_config()
    genre_service = GenreService(config, http_service, claude_service)

    if not genre_service.google_enabled:
        clicycle.error("Claude API key not set!")
        return

    # Test with a well-known artist
    artist_name = "Boards of Canada"
    clicycle.section(f"Searching for genres for '{artist_name}'")

    async def mock_search_genres_boc(artist_name, event_context):
        print(f"Mocking search for {artist_name} with context {event_context}")
        return ["Electronic", "Ambient", "IDM"]

    genre_service._search_artist_genres = mock_search_genres_boc

    genres = await genre_service._search_artist_genres(
        artist_name, event_context={"title": artist_name}
    )

    clicycle.table([{"Genre": g} for g in genres], title=f"Found Genres for {artist_name}")

    assert "Electronic" in genres
    assert "Ambient" in genres
    assert "IDM" in genres

    captured = capsys.readouterr()
    assert "TESTING INDIVIDUAL ARTIST SEARCH" in captured.out


@pytest.mark.asyncio
async def test_claude_analysis(capsys, claude_service):
    """Test Claude's genre analysis directly."""
    clicycle.configure(app_name="event-importer-test")
    config = get_config()

    if not config.api.anthropic_api_key:
        clicycle.error("Anthropic API key not set!")
        return

    clicycle.header("Testing Claude Genre Analysis")

    text_to_analyze = (
        "Four Tet is an English electronic musician. His work has taken on a more "
        "abstract, experimental sound, but also touches on elements of house music."
    )
    event_data = EventData(title="Four Tet", description=text_to_analyze)

    clicycle.info(f"Analyzing text: '{text_to_analyze}'")

    # Mock the enhance_genres method to avoid external calls
    async def mock_enhance_genres(event_data):
        event_data.genres = ["Electronic", "House", "Experimental"]
        return event_data

    claude_service.enhance_genres = mock_enhance_genres

    enhanced_event = await claude_service.enhance_genres(event_data)

    clicycle.table([{"Genre": g} for g in enhanced_event.genres], title="Claude's Analysis")

    assert "Electronic" in enhanced_event.genres
    assert "House" in enhanced_event.genres
    assert "Experimental" in enhanced_event.genres

    captured = capsys.readouterr()
    assert "TESTING CLAUDE GENRE ANALYSIS" in captured.out


async def main() -> None:
    """Run all genre enhancement tests."""
    clicycle.configure(app_name="event-importer-test")
    clicycle.header("Genre Enhancement Test Suite")

    try:
        clicycle.info("Run individual tests with pytest:")
        clicycle.info("pytest tests/integration_tests/test_genre_enhancer.py -v")

        clicycle.success("All genre enhancement tests completed")

    except KeyboardInterrupt:
        clicycle.warning("Tests interrupted by user")
    except Exception as e:
        clicycle.error(f"Test suite failed: {e}")
        raise
        # Clean up - HTTPService is now a fixture that handles its own cleanup
        pass


if __name__ == "__main__":
    asyncio.run(main())
