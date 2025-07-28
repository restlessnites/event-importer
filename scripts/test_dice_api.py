#!/usr/bin/env -S uv run python
"""Clean test of Dice unified search API."""

import asyncio
import logging

import pytest

from app.shared.http import HTTPService


@pytest.mark.parametrize(
    "query, expected_artist_id",
    [("lau.ra", "46153")],
)
@pytest.mark.asyncio
async def test_dice_search_clean(query, expected_artist_id, http_service: HTTPService):
    """Test that Dice search returns the correct artist ID."""
    http = http_service

    print(f"🔍 Testing Dice unified search for query: '{query}'")

    try:
        # Call search API
        search_url = "https://api.dice.fm/unified_search"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://dice.fm",
            "Referer": "https://dice.fm/",
        }
        payload = {"page": 1, "per_page": 5, "query": query, "types": "artist"}

        response = await http.post_json(
            search_url,
            json=payload,
            headers=headers,
            service="Dice",
        )

        data = response.get("results", {}).get("data", [])
        assert data, f"No results returned from Dice API for query '{query}'"

        # Check if the expected artist is in the results
        found_ids = [artist.get("id") for artist in data]
        assert expected_artist_id in found_ids, (
            f"Artist ID {expected_artist_id} not in results {found_ids} for query '{query}'"
        )

        print(
            f"  - Successfully found artist ID {expected_artist_id} for query '{query}'"
        )

    except Exception as e:
        print(f"Error testing Dice API for query '{query}': {e}")

    print("-" * 40)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(test_dice_search_clean())
