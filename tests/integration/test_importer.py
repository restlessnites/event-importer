#!/usr/bin/env -S uv run python
"""Test script for the event importer using mocked API responses."""

import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from app.core.importer import EventImporter
from app.core.schemas import ImportRequest
from config import config

# Define the URLs for the tests
RA_URL = "https://ra.co/events/1908868"
DICE_URL = "https://dice.fm/event/l86kmr-framework-presents-paradise-los-angeles-25th-oct-the-dock-at-the-historic-sears-building-los-angeles-tickets"


# Load fixture data
def load_fixture(name: str) -> dict:
    """Load a JSON fixture from the tests/fixtures directory."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / name
    with fixture_path.open() as f:
        return json.load(f)


ra_graphql_response = load_fixture("ra_graphql_response.json")
dice_search_response = load_fixture("dice_search_response.json")
dice_event_response = load_fixture("dice_event_response.json")


@pytest.fixture
def mock_http_calls(mocker: MockerFixture) -> None:
    """Mock the HTTP calls for the agents."""

    async def mock_post_json(url: str, *args, **kwargs) -> dict:
        if "ra.co" in url:
            return ra_graphql_response
        if "dice.fm" in url:
            return dice_search_response
        return {}

    async def mock_get_json(url: str, *args, **kwargs) -> dict:
        if "dice.fm" in url:
            return dice_event_response
        return {}

    mocker.patch("app.shared.http.HTTPService.post_json", side_effect=mock_post_json)
    mocker.patch("app.shared.http.HTTPService.get_json", side_effect=mock_get_json)


@pytest.mark.parametrize(
    "url",
    [RA_URL, DICE_URL],
)
@pytest.mark.asyncio
async def test_import(url: str, db_session, mock_http_calls, monkeypatch) -> None:
    """Test importing an event with mocked API responses."""
    monkeypatch.setattr("app.shared.database.utils.get_db_session", lambda: db_session)
    request = ImportRequest(url=url)
    importer = EventImporter(config)

    result = await importer.import_event(request.url)

    assert result, f"Import failed for {url}"
    assert result.event_data, f"Event data is missing for {url}"
    assert result.event_data.title, f"Event title is missing for {url}"
    assert result.event_data.venue, f"Event venue is missing for {url}"
    assert result.event_data.date, f"Event date is missing for {url}"
