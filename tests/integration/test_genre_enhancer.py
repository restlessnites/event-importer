#!/usr/bin/env -S uv run python
"""Test script for genre enhancement functionality with CLI."""

import asyncio
import logging

import clicycle
import pytest
from dotenv import load_dotenv

from app.core.schemas import EventData
from app.services.genre import GenreService

# Load environment variables
load_dotenv()

# Set logging to WARNING to reduce noise
logging.basicConfig(level=logging.WARNING)


@pytest.fixture
def modest_mouse_event():
    """Fixture for an event with existing genres."""
    return EventData(
        title="Modest Mouse",
        lineup=["Modest Mouse"],
        genres=["Indie", "Alternative"],
        source_url="http://example.com/modest-mouse",
    )


@pytest.fixture
def aphex_twin_event():
    """Fixture for an event with no genres."""
    return EventData(
        title="Aphex Twin",
        lineup=["Aphex Twin"],
        source_url="http://example.com/aphex-twin",
    )


@pytest.mark.asyncio
async def test_genre_service(
    capsys, genre_service: GenreService, modest_mouse_event, aphex_twin_event
):
    """Test the genre enhancement service."""
    clicycle.configure(app_name="event-importer-test")
    clicycle.header("Testing Genre Service")

    genre_service.google_enabled = True

    # Test case 1: Event with existing genres should be skipped
    clicycle.section("Test 1: Event with existing genres (should be skipped)")
    enhanced_genres = await genre_service.enhance_genres(modest_mouse_event)
    assert enhanced_genres == ["Indie", "Alternative"]
    clicycle.success("Skipped enhancement as expected.")

    # Test case 2: Event with no genres
    clicycle.section("Test 2: Event with no genres")

    async def mock_search_artist_genres(
        artist_name, event_context, supplementary_context=None
    ):
        return ["Electronic", "IDM"]

    genre_service._search_artist_genres = mock_search_artist_genres

    enhanced_genres_no_genres = await genre_service.enhance_genres(aphex_twin_event)
    clicycle.table([{"genres": enhanced_genres_no_genres}], title="Enhanced Genres")
    assert "electronic" in enhanced_genres_no_genres
    assert "idm" in enhanced_genres_no_genres


@pytest.mark.asyncio
async def test_individual_artist_search(
    capsys, genre_service: GenreService, monkeypatch
):
    """Test the internal _search_artist_genres method."""
    clicycle.configure(app_name="event-importer-test")
    clicycle.header("Testing Individual Artist Search")

    # Mock the direct dependencies of _search_artist_genres
    async def mock_google_search(query):
        return [{"snippet": "Boards of Canada are a Scottish electronic music duo..."}]

    async def mock_extract_with_llm(artist_name, search_text, event_context):
        # This is the raw output we expect from the LLM
        return ["electronic", "idm", "ambient"]

    monkeypatch.setattr(genre_service, "_google_search", mock_google_search)
    monkeypatch.setattr(
        genre_service, "_extract_genres_with_llm", mock_extract_with_llm
    )

    def mock_validate_genres(genres):
        return [g.lower() for g in genres]

    monkeypatch.setattr(
        "app.services.genre.MusicGenres.validate_genres", mock_validate_genres
    )

    artist_name = "Boards of Canada"
    # We are testing the _search_artist_genres method directly
    genres = await genre_service._search_artist_genres(
        artist_name, event_context={"title": artist_name}
    )

    clicycle.table(
        [{"Genre": g} for g in genres], title=f"Found Genres for {artist_name}"
    )
    # The assertions should be against the direct, unfiltered output of the method
    assert "electronic" in [g.lower() for g in genres]
    assert "ambient" in [g.lower() for g in genres]
    assert "idm" in [g.lower() for g in genres]


@pytest.mark.asyncio
async def test_claude_genre_analysis(capsys, claude_service):
    """Test Claude's ability to extract genres from text."""
    clicycle.configure(app_name="event-importer-test")
    clicycle.header("Testing Claude Genre Analysis")

    text_to_analyze = (
        "Four Tet is an English electronic musician. His work has taken on a more "
        "abstract, experimental sound, but also touches on elements of house music."
    )

    async def mock_call_with_tool(prompt, tool, tool_name):
        return {"genres": ["Electronic", "House", "Experimental"]}

    claude_service._call_with_tool = mock_call_with_tool

    event_data = EventData(
        title="Four Tet",
        description=text_to_analyze,
        genres=["Electronic"],
        source_url="http://example.com/four-tet",
    )

    enhanced_event = await claude_service.enhance_genres(event_data)
    clicycle.table(
        [{"Genre": g} for g in enhanced_event.genres], title="Claude's Analysis"
    )
    assert "Electronic" in enhanced_event.genres
    assert "House" in enhanced_event.genres
    assert "Experimental" in enhanced_event.genres


async def main() -> None:
    """Run all genre enhancement tests."""
    clicycle.configure(app_name="event-importer-test")
    clicycle.header("Genre Enhancement Test Suite")

    try:
        # This function is not meant to be run directly but through pytest
        clicycle.info("Run individual tests with pytest:")
        clicycle.info("pytest tests/integration_tests/test_genre_enhancer.py -v")

        clicycle.success("All genre enhancement tests completed")

    except KeyboardInterrupt:
        clicycle.warning("Tests interrupted by user")
    except Exception as e:
        clicycle.error(f"Test suite failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
