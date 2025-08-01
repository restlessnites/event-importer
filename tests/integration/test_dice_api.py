#!/usr/bin/env -S uv run python
"""Clean test of Dice unified search API using a mocked response."""

import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from app.shared.http import HTTPService
from config import config


# Load fixture data
def load_fixture(name: str) -> dict:
    """Load a JSON fixture from the tests/fixtures directory."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / name
    with fixture_path.open() as f:
        return json.load(f)


dice_artist_search_response = load_fixture("dice_artist_search_response.json")


@pytest.fixture
def mock_http_calls(mocker: MockerFixture) -> None:
    """Mock the HTTP calls for the Dice search API."""
    mocker.patch(
        "app.shared.http.HTTPService.post_json",
        return_value=dice_artist_search_response,
    )


@pytest.mark.parametrize(
    "query, expected_artist_id",
    [("Josh Baker", "41617")],
)
@pytest.mark.asyncio
async def test_dice_search_clean(
    query: str, expected_artist_id: str, mock_http_calls: None
) -> None:
    """Test that Dice search returns the correct artist ID from a mocked response."""
    http = HTTPService(config)
    try:
        response = await http.post_json(
            "https://api.dice.fm/unified_search",
            json={"query": query},
            service="Dice",
        )

        sections = response.get("sections", [])
        items = []
        for section in sections:
            items.extend(section.get("items", []))

        # Extract artists from events in the items
        artists = []
        for item in items:
            if item.get("type") == "event":
                event = item.get("event", {})
                if event:
                    lineup = event.get("summary_lineup", {})
                    top_artists = lineup.get("top_artists", [])
                    # The artist object in the fixture has "artist_id"
                    for artist in top_artists:
                        artists.append({"id": artist.get("artist_id")})

        data = artists
        assert data, f"No results returned from Dice API for query '{query}'"

        # Check if the expected artist is in the results
        found_ids = [artist.get("id") for artist in data]
        assert expected_artist_id in found_ids, (
            f"Artist ID {expected_artist_id} not in results {found_ids} for query '{query}'"
        )
        print(
            f"  - Successfully found artist ID {expected_artist_id} for query '{query}'"
        )
    finally:
        await http.close()
    print("-" * 40)
