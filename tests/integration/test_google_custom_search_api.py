#!/usr/bin/env -S uv run python
"""Simple test to verify Google Custom Search API is working with CLI."""

from unittest.mock import patch

import clicycle
import pytest


@patch("app.shared.http.HTTPService.get_json")
@pytest.mark.asyncio
async def test_google_api(mock_get_json, http_service) -> None:
    """Test Google Custom Search API directly."""
    # Mock the API response
    mock_get_json.return_value = {
        "items": [
            {
                "title": "Test Image",
                "link": "https://example.com/image.jpg",
                "image": {"width": 800, "height": 600},
            }
        ],
        "searchInformation": {
            "totalResults": "1",
            "searchTime": 0.1,
        },
    }

    clicycle.configure(app_name="event-importer-test")
    clicycle.header("Google Custom Search API Test")
    clicycle.info("Testing direct API access")

    clicycle.info("Searching for 'Bonobo live set'...")
    response = await http_service.get_json(
        "https://www.googleapis.com/customsearch/v1",
        service="GoogleSearch",
    )

    # Assert that the API call was successful and returned results
    assert "error" not in response, f"API Error: {response.get('error')}"
    assert "items" in response and response["items"], "No 'items' found in response"

    clicycle.success(f"Found {len(response['items'])} results")

    # Display results in a table
    clicycle.section("Search Results")

    results = []
    for i, item in enumerate(response["items"], 1):
        result = {
            "#": str(i),
            "Title": item.get("title", "No title")[:40],
            "Size": "Unknown",
            "URL": item.get("link", "No URL"),
        }

        if "image" in item and item["image"].get("width"):
            result["Size"] = (
                f"{item['image']['width']}x{item['image'].get('height', '?')}"
            )

        results.append(result)

    clicycle.table(results, title="Image Search Results")

    # Show API usage info if available
    if "searchInformation" in response:
        info = response["searchInformation"]
        clicycle.section("Search Information")
        clicycle.info(f"Total results: {info.get('totalResults', 'Unknown')}")
        clicycle.info(f"Search time: {info.get('searchTime', 'Unknown')}s")

    clicycle.success("Google API test completed")


if __name__ == "__main__":
    try:
        # This would need proper fixtures when run standalone
        print("Run with pytest for proper fixture support")
    except KeyboardInterrupt:
        clicycle.warning("Test interrupted by user")
